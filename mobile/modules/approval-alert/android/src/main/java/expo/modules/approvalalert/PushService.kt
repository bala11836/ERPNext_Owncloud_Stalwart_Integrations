package expo.modules.approvalalert

import android.content.Context
import android.net.Uri
import android.os.Bundle
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import org.json.JSONObject

/**
 * Alerts while the app is closed (owner, 26 November 2026). ERPNext sends Google a data-only message (kind,
 * document type and ID, site); this service writes the visible text here, from the texts the app stored in its
 * language (lib/push.ts), so no name or amount ever travels. Every approval rings the full page unless the person
 * made that area a normal alert; a returned entry is a normal alert. The app lock still shows first on opening.
 */
class PushService : FirebaseMessagingService() {
  override fun onMessageReceived(message: RemoteMessage) {
    val data = message.data
    if (data["v"] != "1") return
    val alert = PushTexts.build(applicationContext, data) ?: return
    if (alert.getBoolean(PushTexts.RING)) Alerts.post(applicationContext, alert) else Alerts.postNormal(applicationContext, alert)
  }

  // A new address reaches ERPNext the next time the app opens (lib/push registers at every start).
  override fun onNewToken(token: String) = Unit
}

object PushTexts {
  const val RING = "ring"
  private const val PREFS = "approval-alert"
  private const val KEY = "push-texts"

  fun save(ctx: Context, json: String) = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY, json).apply()

  private fun saved(ctx: Context): JSONObject =
    ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY, null)?.let { runCatching { JSONObject(it) }.getOrNull() } ?: JSONObject()

  private fun JSONObject.text(key: String, fallback: String) = optString(key).ifEmpty { fallback }
  private fun enc(v: String) = Uri.encode(v)

  /** The alert's texts and place, or null for a kind this version does not know. */
  fun build(ctx: Context, data: Map<String, String>): Bundle? {
    val kind = data["kind"] ?: return null
    if (kind !in setOf("approval", "verify", "returned")) return null
    val doctype = data["doctype"] ?: ""
    val t = saved(ctx)
    val area = t.optJSONObject("areas")?.optString(doctype)?.ifEmpty { null } ?: "other"
    val label = t.optJSONObject("labels")?.optString(area)?.ifEmpty { null } ?: area.replaceFirstChar { it.uppercase() }
    val site = data["site"].orEmpty()
    val siteLabel = data["site_label"].orEmpty()
    val docname = data["docname"].orEmpty()
    val fill = { s: String -> s.replace("{area}", label).replace("{site}", siteLabel) }

    val title = fill(
      when (kind) {
        "verify" -> t.text("verifyTitle", "Attendance to verify")
        "returned" -> t.text("returnedTitle", "Returned for correction")
        else -> t.text("approvalTitle", "{area}: approval waiting")
      },
    )
    val body = fill(
      when {
        kind == "returned" -> t.text("returnedBody", "{area} · open the app to see why")
        siteLabel.isNotEmpty() -> t.text("bodySite", "{site}")
        else -> t.text("bodyNoSite", "Open the app to review it")
      },
    )
    // Only the app's own screens, through its own link; the app lock shows first.
    val path = when {
      kind == "approval" && area == "attendance" && site.isNotEmpty() -> "attendance/approve?site=${enc(site)}"
      kind == "verify" && site.isNotEmpty() -> "attendance/verify?site=${enc(site)}"
      kind == "approval" && docname.isNotEmpty() && area != "attendance" -> "approvals/${enc(doctype)}/${enc(docname)}"
      kind == "returned" && area == "attendance" -> ""
      else -> "inbox"
    }
    val base = t.optString("base")
    val ringOff = t.optJSONArray("ringOff")?.let { a -> (0 until a.length()).map { a.optString(it) } }.orEmpty()
    return Bundle().apply {
      putString(Alerts.AREA, area)
      putString(Alerts.AREA_LABEL, label)
      putString(Alerts.TITLE, title)
      putString(Alerts.BODY, body)
      putString(Alerts.URL, if (base.isEmpty()) null else base + path)
      putString(Alerts.CHANNEL, fill(t.text("ringChannel", "{area}: ringing alerts")))
      putString(Alerts.LIST_CHANNEL, fill(t.text("listChannel", "{area}: in the list")))
      putString(Alerts.NORMAL_CHANNEL, fill(t.text("normalChannel", "{area}: alerts")))
      putString(Alerts.LATER, t.text("later", "Later"))
      putString(Alerts.REVIEW, t.text("review", "Review"))
      putBoolean(RING, kind != "returned" && area !in ringOff)
    }
  }
}
