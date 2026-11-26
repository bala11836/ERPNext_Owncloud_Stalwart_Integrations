package expo.modules.approvalalert

import android.app.AlarmManager
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

class ApprovalAlertModule : Module() {
  private val context: Context
    get() = requireNotNull(appContext.reactContext) { "The app is not ready" }

  override fun definition() = ModuleDefinition {
    Name("ApprovalAlert")

    /** Show the full-page alert after `seconds` (the Settings test), even when the app is closed. */
    Function("schedule") { seconds: Int, alert: Map<String, String> ->
      val ctx = context
      val show = Intent(ctx, AlertReceiver::class.java).setAction(Alerts.ACTION_SHOW)
      alert.forEach { (k, v) -> show.putExtra(k, v) }
      val pending = PendingIntent.getBroadcast(ctx, 7401, show, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
      val alarms = ctx.getSystemService(Context.ALARM_SERVICE) as AlarmManager
      // Not exact (no special alarm permission): Android may deliver it up to about a minute late.
      alarms.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, System.currentTimeMillis() + seconds.coerceAtLeast(1) * 1000L, pending)
    }

    /** Android 14+: whether the person allowed full-page alerts for this app (earlier versions: always). */
    Function("canUseFullScreen") {
      if (Build.VERSION.SDK_INT >= 34) {
        (context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager).canUseFullScreenIntent()
      } else {
        true
      }
    }

    /** Android 14+: the system page where the person allows full-page alerts for this app. */
    Function("openFullScreenSettings") {
      if (Build.VERSION.SDK_INT >= 34) {
        context.startActivity(
          Intent(Settings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT, Uri.parse("package:${context.packageName}"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
        )
      }
    }

    /** The texts and ring choices PushService writes alerts with while the app is closed (lib/push.ts). */
    Function("setPushTexts") { json: String ->
      PushTexts.save(context, json)
    }
  }
}
