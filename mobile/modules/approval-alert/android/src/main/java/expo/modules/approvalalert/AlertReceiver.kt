package expo.modules.approvalalert

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Shows a scheduled alert (the Settings test; push brings real ones later), and handles the Later button. */
class AlertReceiver : BroadcastReceiver() {
  override fun onReceive(context: Context, intent: Intent) {
    when (intent.action) {
      Alerts.ACTION_SHOW -> intent.extras?.let { Alerts.post(context, it) }
      Alerts.ACTION_LATER -> Alerts.stopRing(context, intent.getStringExtra(Alerts.AREA) ?: "other")
    }
  }
}
