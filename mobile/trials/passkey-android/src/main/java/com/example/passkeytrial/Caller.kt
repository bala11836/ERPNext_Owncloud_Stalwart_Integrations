package com.example.passkeytrial

import android.content.Context
import android.net.Uri
import androidx.annotation.RequiresApi
import androidx.credentials.provider.CallingAppInfo
import org.json.JSONObject

/**
 * Who asks, and for which website. A browser (or Google Play services, for a computer's QR sign-in) states the
 * website's address; Android lets us trust that only for callers on Google's public list. An ordinary app is
 * identified by its signing certificate.
 */
@RequiresApi(34)
class Caller(context: Context, private val info: CallingAppInfo, private val suppliedHash: ByteArray?) {
    val origin: String?
    val verified: Boolean
    val summary: String

    init {
        val list = Store.browsers(context)
        var seen: String? = null
        var note = if (list == null) "browser list missing" else "ok"
        if (list != null) {
            try {
                seen = info.getOrigin(list)
            } catch (e: IllegalStateException) {
                note = "caller states a website but is NOT on the browser list"
            }
        }
        origin = seen
        verified = seen != null || !info.isOriginPopulated()
        summary = "caller=${info.packageName} statesWebsite=${info.isOriginPopulated()} website=$seen hashSupplied=${suppliedHash != null} ($note)"
    }

    /** Refuses a website asking for another site's key. An unverified caller is logged and let through: TRIAL ONLY. */
    fun mayUse(rpId: String): Boolean {
        val host = origin?.let { Uri.parse(it).host } ?: return true
        return WebAuthn.siteMayUse(host, rpId)
    }

    /** Browsers send the hash of their own client data. For an ordinary app we write the client data ourselves. */
    fun clientData(type: String, challenge: String): Pair<String, ByteArray> {
        if (suppliedHash != null) return "{}" to suppliedHash
        val certificate = info.signingInfo.apkContentsSigners[0].toByteArray()
        val json = JSONObject()
            .put("type", type)
            .put("challenge", challenge)
            .put("origin", "android:apk-key-hash:" + WebAuthn.b64(WebAuthn.sha256(certificate)))
            .put("androidPackageName", info.packageName)
            .toString()
        return json to WebAuthn.sha256(json.toByteArray())
    }
}
