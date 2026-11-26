package com.example.erp.app

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/** What the app needs from this phone, checked for real. The same check opens onboarding later (screen A2). */
class PhoneCheck(val lines: List<Pair<StatusKind, String>>, val usable: Boolean)

fun checkPhone(context: Context): PhoneCheck {
    val lines = mutableListOf<Pair<StatusKind, String>>()
    val strong = BiometricManager.from(context).canAuthenticate(BIOMETRIC_STRONG)
    lines += when (strong) {
        BiometricManager.BIOMETRIC_SUCCESS -> StatusKind.OK to "Fingerprint sensor: ready"
        BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> StatusKind.WARN to "Fingerprint sensor: no fingerprint saved yet. Add yours in the phone's Settings."
        BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> StatusKind.BAD to "Fingerprint sensor: this phone has none. The app cannot keep a key here."
        else -> StatusKind.BAD to "Fingerprint sensor: not usable right now (code $strong)"
    }
    val strongBox = context.packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)
    lines += StatusKind.OK to if (strongBox) "Secure chip: separate chip (StrongBox)" else "Secure chip: built into the processor"
    // The app cannot be installed below Android 9, so a running app is always on a supported version.
    lines += StatusKind.OK to "Android ${Build.VERSION.RELEASE}: supported"
    return PhoneCheck(lines, usable = strong == BiometricManager.BIOMETRIC_SUCCESS)
}

@Composable
fun PhoneScreen(check: PhoneCheck, model: String, version: String) {
    // One centred column, so text lines stay readable on a tablet.
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(Look.Gap), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(Modifier.widthIn(max = 640.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("This phone", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
            Text(model, style = MaterialTheme.typography.bodyLarge, color = Look.Ink)
            Panel { check.lines.forEach { (kind, text) -> Status(kind, text) } }
            Status(
                if (check.usable) StatusKind.OK else StatusKind.WARN,
                if (check.usable) "This phone can keep a fingerprint-locked key." else "This phone cannot keep a fingerprint-locked key yet.",
            )
            Text("App version $version", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
        }
    }
}
