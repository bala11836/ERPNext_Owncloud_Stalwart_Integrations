package com.example.erp.app

import android.Manifest
import android.annotation.SuppressLint
import android.app.AlarmManager
import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.core.content.edit
import com.example.erp.core.AlertAction
import com.example.erp.core.AlertState
import com.example.erp.core.Alerts
import com.example.erp.core.Slot
import com.example.erp.core.Strength
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.messaging.FirebaseMessaging
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/** The kinds of alert the person can switch in the phone's own settings. The app keeps no second set of switches. */
enum class AlertKind(val id: String, val title: String, val text: String, val importance: Int, val rings: Boolean = false) {
    APPROVALS("approvals", "Approvals: ringing", "Something waits for your decision. Rings and shows a full page on a locked phone.", NotificationManager.IMPORTANCE_HIGH, rings = true),
    APPROVALS_LIST("approvals-list", "Approvals: in the list", "Stays in the list after the ringing stops. No sound.", NotificationManager.IMPORTANCE_LOW),
    REJECTED("rejected", "Rejected, to correct", "Something you sent came back. Normal sound.", NotificationManager.IMPORTANCE_DEFAULT),
    CHAT("chat", "Chat", "A message for you. Normal sound.", NotificationManager.IMPORTANCE_DEFAULT),
    MAIL("mail", "Mail", "New mail. No sound.", NotificationManager.IMPORTANCE_LOW),
    NOTICES("notices", "Notices", "Information. No sound.", NotificationManager.IMPORTANCE_LOW),
}

/** What can be done about blocked alerts. */
enum class Fix(val label: String) {
    ALLOW("Allow alerts"),
    APP_SETTING("Open the phone's setting"),
    KIND_SETTING("Open the phone's setting"),
    FULL_PAGE("Allow the full page"),
}

/** Whether alerts can show on this phone. [blocked] says why not in plain words, with the one thing that fixes it. */
data class AlertsView(
    val blocked: String? = null,
    val fix: Fix? = null,
    /** False on a phone (Android 14 and newer) where the person has not allowed the full page over the locked screen. */
    val fullPage: Boolean = true,
    /** False when this build was made without the values for Google's messaging: it can show alerts, but receives none. */
    val connected: Boolean = false,
    /** Test builds: the address Google delivers this phone's alerts to, for one test signal from the owner. */
    val address: String? = null,
)

/**
 * Everything the app does with an alert on the phone. A signal comes in ([receive]), the rule in
 * [Alerts.handle] says what to show, and this shows or removes it. It works while the app is locked or closed and
 * touches nothing that is locked away: what it shows are the rule's fixed words, and what it remembers are short
 * fingerprints, never a reference or any content.
 *
 * A ringing alert is two entries, as in the earlier app: one that rings and opens the full page over a locked
 * screen and stops after [RING_MS], and a quiet one that stays in the list so the alert is not lost.
 */
object AlertCenter {
    const val OPEN_PLACE = "open-place"
    const val WORDS = "words"
    const val SLOT = "slot"
    const val ACTION_SHOW = "com.example.erp.app.ALERT_SHOW"
    const val ACTION_LATER = "com.example.erp.app.ALERT_LATER"
    const val RING_MS = 30_000L
    private const val PREFS = "alerts"
    private const val FIELD = "signal:"
    private const val FLAGS = PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT

    private fun kind(slot: Slot) = when (slot) {
        Slot.DECIDE -> AlertKind.APPROVALS_LIST
        Slot.REJECTED -> AlertKind.REJECTED
        Slot.MESSAGE -> AlertKind.CHAT
        Slot.MAIL -> AlertKind.MAIL
        Slot.NOTICE -> AlertKind.NOTICES
    }

    /** The phone's number for the ringing entry of a slot; the quiet entry uses the slot's own number. */
    private fun ringId(slot: Slot) = 100 + slot.id

    /** Makes the kinds known to the phone. Safe to call every time the app starts. */
    fun prepare(context: Context) {
        val manager = context.getSystemService(NotificationManager::class.java)
        for (kind in AlertKind.entries) {
            val channel = NotificationChannel(kind.id, kind.title, kind.importance).apply { description = kind.text }
            if (kind.rings) {
                // Approvals sound like a call, not like a message. The phone's silent mode still wins: this kind
                // never asks to get past "Do not disturb".
                channel.setSound(
                    RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE),
                    AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE).setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build(),
                )
                channel.enableVibration(true)
            }
            manager.createNotificationChannel(channel)
        }
    }

    private fun allowed(context: Context) =
        Build.VERSION.SDK_INT < 33 || ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    /** Opens the app itself at a place; the fingerprint is asked there before anything is shown. */
    fun openApp(context: Context, slot: Slot): Intent = Intent(context, MainActivity::class.java)
        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        .putExtra(OPEN_PLACE, slot.lead.name)

    /** One signal: from Google while the app is closed, or a test made on the phone. */
    @SuppressLint("MissingPermission") // checked by allowed(), which the check tool does not follow
    @Synchronized
    fun receive(context: Context, data: Map<String, String>) {
        // A phone without its key (never made, or erased after five misses) shows nothing: there is nobody to show it to.
        if (!PhoneLock.hasKey(context)) return
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val before = AlertState(prefs.getStringSet("deciding", emptySet()).orEmpty().toSet(), prefs.getStringSet("rejected", emptySet()).orEmpty().toSet())
        val (after, action) = Alerts.handle(data, before)
        if (after != before) prefs.edit(commit = true) { putStringSet("deciding", after.deciding); putStringSet("rejected", after.rejected) }
        val manager = NotificationManagerCompat.from(context)
        when (action) {
            is AlertAction.Remove -> {
                manager.cancel(action.slot.id)
                manager.cancel(ringId(action.slot))
                RingActivity.close(action.slot)
            }
            is AlertAction.Show -> if (allowed(context)) {
                // The quiet entry first: it is what stays in the list after the ringing stops.
                manager.notify(action.slot.id, entry(context, action).build())
                if (action.strength == Strength.RING) manager.notify(ringId(action.slot), ring(context, action).build())
            }
            AlertAction.Ignore -> Unit
        }
    }

    /** The entry that stays in the list. Only the rule's fixed words: no second line, no name, no amount. */
    private fun entry(context: Context, alert: AlertAction.Show) = NotificationCompat.Builder(context, kind(alert.slot).id)
        .setSmallIcon(R.drawable.ic_bell)
        .setContentTitle(alert.words)
        .setContentIntent(PendingIntent.getActivity(context, alert.slot.id, openApp(context, alert.slot), FLAGS))
        .setAutoCancel(true)
        // A ringing alert makes its sound through its ringing entry; a count that only goes down makes none.
        .setOnlyAlertOnce(alert.strength != Strength.ALERT)
        .setCategory(NotificationCompat.CATEGORY_STATUS)
        // Safe to show in full on a locked phone, because it holds nothing private.
        .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)

    /**
     * The entry that rings: on a locked phone it opens the full page ([RingActivity]); on a phone in use it is a
     * banner with the same two choices. Neither choice decides anything: "Open" leads to the app and its
     * fingerprint, "Later" only stops the ringing.
     */
    private fun ring(context: Context, alert: AlertAction.Show): NotificationCompat.Builder {
        val id = ringId(alert.slot)
        val page = PendingIntent.getActivity(
            context, id,
            Intent(context, RingActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_USER_ACTION)
                .putExtra(WORDS, alert.words).putExtra(SLOT, alert.slot.name),
            FLAGS,
        )
        val later = PendingIntent.getBroadcast(context, id, Intent(context, AlertReceiver::class.java).setAction(ACTION_LATER).putExtra(SLOT, alert.slot.name), FLAGS)
        val open = PendingIntent.getActivity(context, alert.slot.id, openApp(context, alert.slot), FLAGS)
        return NotificationCompat.Builder(context, AlertKind.APPROVALS.id)
            .setSmallIcon(R.drawable.ic_bell)
            .setContentTitle(alert.words)
            .setCategory(NotificationCompat.CATEGORY_REMINDER)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setFullScreenIntent(page, true)
            .setContentIntent(page)
            .setAutoCancel(true)
            .setTimeoutAfter(RING_MS)
            .addAction(0, "Later", later)
            .addAction(0, "Open", open)
    }

    /** "Later", "Open", or the full page closed: the ringing stops. The quiet entry stays in the list. */
    fun stopRing(context: Context, slot: Slot) = NotificationManagerCompat.from(context).cancel(ringId(slot))

    /** Sign-out and a lost key: every alert goes, and what was remembered about them. */
    @Synchronized // with receive(), so a signal being handled cannot write back what is cleared here
    fun clear(context: Context) {
        RingActivity.close(null)
        NotificationManagerCompat.from(context).cancelAll()
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit(commit = true) { clear() }
    }

    /**
     * Makes a signal arrive after [seconds], also when the app is closed in between: the phone's alarm service
     * keeps it, not the app. Not exact (that would need a special permission): the phone may deliver it up to
     * about a minute late. Used for the tests on the Alerts screen.
     */
    fun schedule(context: Context, data: Map<String, String>, seconds: Int) {
        val show = Intent(context, AlertReceiver::class.java).setAction(ACTION_SHOW)
        for ((name, value) in data) show.putExtra(FIELD + name, value)
        val pending = PendingIntent.getBroadcast(context, data.hashCode(), show, FLAGS)
        context.getSystemService(AlarmManager::class.java).setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, System.currentTimeMillis() + seconds * 1000L, pending)
    }

    /** The signal a scheduled alarm carries. */
    fun scheduled(intent: Intent): Map<String, String> =
        intent.extras?.let { extras -> extras.keySet().filter { it.startsWith(FIELD) }.associate { it.removePrefix(FIELD) to extras.getString(it).orEmpty() } }.orEmpty()

    /** Why alerts cannot show right now, and what fixes it; null when they can. */
    fun blocked(context: Context): Pair<String, Fix>? {
        val manager = NotificationManagerCompat.from(context)
        return when {
            !allowed(context) -> "the phone has not been allowed to show this app's alerts." to Fix.ALLOW
            !manager.areNotificationsEnabled() -> "alerts for this app are switched off in the phone's settings." to Fix.APP_SETTING
            manager.getNotificationChannel(AlertKind.APPROVALS.id)?.importance == NotificationManager.IMPORTANCE_NONE ->
                "the kind \"Approvals: ringing\" is switched off in the phone's settings." to Fix.KIND_SETTING
            else -> null
        }
    }

    /** Android 14 and newer: whether the person allowed this app's full page over the locked screen. Earlier: always. */
    fun fullPageAllowed(context: Context): Boolean =
        Build.VERSION.SDK_INT < 34 || context.getSystemService(NotificationManager::class.java).canUseFullScreenIntent()

    /**
     * Tells Google's messaging which app this is, from the values set privately for the build. There is no
     * settings file in the project. False when the build has no values: it then receives nothing.
     */
    fun connect(context: Context): Boolean {
        val values = listOf(BuildConfig.ALERTS_APP, BuildConfig.ALERTS_KEY, BuildConfig.ALERTS_PROJECT, BuildConfig.ALERTS_SENDER)
        if (values.any { it.isEmpty() }) return false
        if (FirebaseApp.getApps(context).isEmpty()) {
            FirebaseApp.initializeApp(
                context,
                FirebaseOptions.Builder().setApplicationId(BuildConfig.ALERTS_APP).setApiKey(BuildConfig.ALERTS_KEY)
                    .setProjectId(BuildConfig.ALERTS_PROJECT).setGcmSenderId(BuildConfig.ALERTS_SENDER).build(),
            )
        }
        return true
    }

    /** Asks Google for this phone's delivery address. Only called where it is used (test builds today; sign-in later). */
    fun address(done: (String?) -> Unit) {
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task -> done(if (task.isSuccessful) task.result else null) }
    }
}

/** Starts with the app's process, also when Google wakes the closed app for a signal. */
class ErpApp : Application() {
    override fun onCreate() {
        super.onCreate()
        AlertCenter.prepare(this)
        AlertCenter.connect(this)
    }
}

/**
 * Receives signals from Google. Only the signal's own short fields are read. The server must send data-only signals:
 * one that carries a ready-made notification text is shown by Google's library itself while the app is in the
 * background, without coming here.
 */
class AlertService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) = AlertCenter.receive(this, message.data)

    // ponytail: the address is sent to our server after sign-in (Phase 1 part 4); until then a new one is only shown in test builds.
    override fun onNewToken(token: String) = Unit
}

/** A scheduled test signal arriving, and the "Later" button of a ringing alert. Not open to other apps. */
class AlertReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            AlertCenter.ACTION_SHOW -> AlertCenter.receive(context, AlertCenter.scheduled(intent))
            AlertCenter.ACTION_LATER -> Slot.entries.find { it.name == intent.getStringExtra(AlertCenter.SLOT) }?.let { AlertCenter.stopRing(context, it) }
        }
    }
}
