package expo.modules.approvalalert

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.net.Uri
import android.os.Build
import android.os.Bundle

/**
 * One approval alert per area, like a visitor call (owner, 24 November 2026):
 * - a ringing notification (the phone's ringtone, repeated) that opens the full page over the locked screen and
 *   stops after 30 seconds, on Later or Review, or when the list is opened; silent and Do Not Disturb are respected
 *   (the system decides; the channel never bypasses them);
 * - a quiet entry in the list, so the alert is not lost when the ringing stops.
 * A newer alert of the same area replaces the older one: one ring, never one per document.
 * Texts carry only the kind, the count and the site; approving needs the app, behind its lock.
 */
object Alerts {
  const val AREA = "area"
  const val AREA_LABEL = "areaLabel"
  const val TITLE = "title"
  const val BODY = "body"
  const val URL = "url"
  const val CHANNEL = "channel"
  const val LIST_CHANNEL = "listChannel"
  const val NORMAL_CHANNEL = "normalChannel"
  const val LATER = "later"
  const val REVIEW = "review"
  const val ACTION_SHOW = "expo.modules.approvalalert.SHOW"
  const val ACTION_LATER = "expo.modules.approvalalert.LATER"
  const val RING_MS = 30_000L

  private fun ringChannel(area: String) = "$area-ring"
  private fun listChannel(area: String) = "$area-list"
  fun ringId(area: String) = "ring:$area".hashCode()
  fun listId(area: String) = "list:$area".hashCode()

  private fun manager(ctx: Context) = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

  private fun channels(ctx: Context, area: String, ring: String, list: String) {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
    val sound = AudioAttributes.Builder()
      .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
      .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
      .build()
    manager(ctx).createNotificationChannel(
      NotificationChannel(ringChannel(area), ring, NotificationManager.IMPORTANCE_HIGH).apply {
        setSound(RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE), sound)
        enableVibration(true)
        lockscreenVisibility = Notification.VISIBILITY_PUBLIC
      },
    )
    manager(ctx).createNotificationChannel(NotificationChannel(listChannel(area), list, NotificationManager.IMPORTANCE_LOW))
  }

  @Suppress("DEPRECATION")
  private fun builder(ctx: Context, channel: String) =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(ctx, channel) else Notification.Builder(ctx)

  private const val FLAGS = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE

  /** Opens the app at `url` (its own link scheme, this package only); the app lock shows first. */
  fun openIntent(ctx: Context, url: String?): Intent {
    val open = if (url.isNullOrEmpty()) ctx.packageManager.getLaunchIntentForPackage(ctx.packageName) ?: Intent()
    else Intent(Intent.ACTION_VIEW, Uri.parse(url)).setPackage(ctx.packageName)
    return open.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
  }

  /** Stop the ringing (Later, Review, or the page closed). The quiet list entry stays until it is opened. */
  fun stopRing(ctx: Context, area: String) = manager(ctx).cancel(ringId(area))

  fun clear(ctx: Context, area: String) {
    manager(ctx).cancel(ringId(area))
    manager(ctx).cancel(listId(area))
  }

  /**
   * A normal alert with the phone's notification sound, shown on top (a returned entry, or an area the person set
   * to not ring). One per area: a newer one replaces the older.
   */
  @Suppress("DEPRECATION")
  fun postNormal(ctx: Context, a: Bundle) {
    val area = a.getString(AREA) ?: "other"
    val title = a.getString(TITLE) ?: return
    val channel = "$area-normal"
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
      manager(ctx).createNotificationChannel(
        NotificationChannel(channel, a.getString(NORMAL_CHANNEL) ?: area, NotificationManager.IMPORTANCE_HIGH).apply {
          lockscreenVisibility = Notification.VISIBILITY_PUBLIC
        },
      )
    }
    val open = PendingIntent.getActivity(ctx, listId(area), openIntent(ctx, a.getString(URL)), FLAGS)
    val n = builder(ctx, channel)
      .setSmallIcon(ctx.applicationInfo.icon).setContentTitle(title).setContentText(a.getString(BODY) ?: "")
      .setContentIntent(open).setAutoCancel(true)
      .setVisibility(Notification.VISIBILITY_PUBLIC)
      .setCategory(Notification.CATEGORY_REMINDER)
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) n.setPriority(Notification.PRIORITY_HIGH).setDefaults(Notification.DEFAULT_ALL)
    manager(ctx).notify(listId(area), n.build())
  }

  @Suppress("DEPRECATION")
  fun post(ctx: Context, a: Bundle) {
    val area = a.getString(AREA) ?: "other"
    val title = a.getString(TITLE) ?: return
    val body = a.getString(BODY) ?: ""
    channels(ctx, area, a.getString(CHANNEL) ?: area, a.getString(LIST_CHANNEL) ?: area)
    val icon = ctx.applicationInfo.icon
    val page = PendingIntent.getActivity(
      ctx, ringId(area),
      Intent(ctx, AlertActivity::class.java).putExtras(a).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_USER_ACTION),
      FLAGS,
    )
    val review = PendingIntent.getActivity(ctx, listId(area), openIntent(ctx, a.getString(URL)), FLAGS)
    val later = PendingIntent.getBroadcast(
      ctx, ringId(area), Intent(ctx, AlertReceiver::class.java).setAction(ACTION_LATER).putExtra(AREA, area), FLAGS,
    )

    // The quiet entry first: it is what stays in the list after the ringing stops.
    manager(ctx).notify(
      listId(area),
      builder(ctx, listChannel(area))
        .setSmallIcon(icon).setContentTitle(title).setContentText(body)
        .setContentIntent(review).setAutoCancel(true)
        .setVisibility(Notification.VISIBILITY_PUBLIC)
        .setCategory(Notification.CATEGORY_REMINDER)
        .build(),
    )

    val ring = builder(ctx, ringChannel(area))
      .setSmallIcon(icon).setContentTitle(title).setContentText(body)
      .setCategory(Notification.CATEGORY_REMINDER)
      .setVisibility(Notification.VISIBILITY_PUBLIC)
      .setFullScreenIntent(page, true)
      .setContentIntent(page)
      .setAutoCancel(true)
      .addAction(Notification.Action.Builder(null, a.getString(LATER) ?: "Later", later).build())
      .addAction(Notification.Action.Builder(null, a.getString(REVIEW) ?: "Review", review).build())
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) ring.setTimeoutAfter(RING_MS)
    else ring.setPriority(Notification.PRIORITY_MAX).setSound(RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE))
    val n = ring.build()
    // The sound repeats until the ring is stopped or times out; without a timeout (Android 7) it rings once.
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) n.flags = n.flags or Notification.FLAG_INSISTENT
    manager(ctx).notify(ringId(area), n)
  }
}
