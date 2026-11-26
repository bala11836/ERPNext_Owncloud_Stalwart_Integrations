package com.example.erp.app

import android.content.Context
import android.graphics.Color as AndroidColor
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.core.content.edit
import com.example.erp.core.OutdoorSwitch
import com.example.erp.core.Palettes
import com.example.erp.core.Point
import com.example.erp.core.Trace
import com.example.erp.core.Tracer
import java.util.UUID

class MainActivity : ComponentActivity() {
    private val tracer = Tracer()
    private val outdoorSwitch = OutdoorSwitch()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        // No screenshots, and a blank card in the app switcher: the app will show personal data.
        window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)
        val testBuild = BuildConfig.DEBUG
        val settings = getSharedPreferences("display", Context.MODE_PRIVATE)
        val sensors = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val lightSensor: Sensor? = sensors.getDefaultSensor(Sensor.TYPE_LIGHT)
        val phone = checkPhone(this)

        setContent {
            var automatic by remember { mutableStateOf(settings.getBoolean("outdoor-automatic", true)) }
            var forced by remember { mutableStateOf(settings.getBoolean("outdoor-forced", false)) }
            var bright by remember { mutableStateOf(false) }
            var lux by remember { mutableStateOf<Float?>(null) }
            var traces by remember { mutableStateOf(tracer.all()) }

            // The light sensor is listened to only while the automatic switch is on and the app is on screen.
            DisposableEffect(automatic, lightSensor) {
                val listener = object : SensorEventListener {
                    override fun onSensorChanged(event: SensorEvent) {
                        lux = event.values[0]
                        bright = outdoorSwitch.reading(event.values[0])
                    }

                    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
                }
                if (automatic && lightSensor != null) sensors.registerListener(listener, lightSensor, SensorManager.SENSOR_DELAY_NORMAL)
                onDispose { sensors.unregisterListener(listener) }
            }

            val outdoor = forced || (automatic && bright)
            val palette = Palettes.pick(phoneIsDark = isSystemInDarkTheme(), outdoor = outdoor)
            // Status and navigation bar icons must stay readable on the look in use, also when Outdoor overrides night mode.
            SideEffect {
                val style = if (palette == Palettes.DARK) SystemBarStyle.dark(AndroidColor.TRANSPARENT)
                else SystemBarStyle.light(AndroidColor.TRANSPARENT, AndroidColor.TRANSPARENT)
                enableEdgeToEdge(statusBarStyle = style, navigationBarStyle = style)
            }

            ErpTheme(palette) {
                AppFrame(
                    FrameState(
                        palette, testBuild, traces, phone, "${Build.MANUFACTURER} ${Build.MODEL}", BuildConfig.VERSION_NAME,
                        hasLightSensor = lightSensor != null, automaticOutdoor = automatic, forcedOutdoor = forced, lux = lux,
                    ),
                    onAddSample = { addSample(); traces = tracer.all() },
                    onAutomaticOutdoor = { automatic = it; settings.edit { putBoolean("outdoor-automatic", it) } },
                    onForcedOutdoor = { forced = it; settings.edit { putBoolean("outdoor-forced", it) } },
                )
            }
        }
    }

    /** Test builds only: one failed and one complete trace, so the screen can be checked before real calls exist (Phase 1). */
    private fun addSample(): Trace? = sampleTraces(tracer)
}

/** One failed and one complete made-up trace. Used by the test-build button and by the screen tests. */
fun sampleTraces(tracer: Tracer): Trace? {
    val bad = UUID.randomUUID().toString()
    tracer.start(bad, "Sample: check-out refused")
    listOf(Point.SCREEN, Point.PHONE_STORE, Point.GATEWAY).forEach { tracer.mark(bad, it, true) }
    tracer.mark(bad, Point.NETWORK, true, tookMs = 420)
    tracer.mark(bad, Point.SERVER, false, "refused by a server rule (417)", detail = "sample values: distance_m=180, radius_m=100")
    val good = UUID.randomUUID().toString()
    tracer.start(good, "Sample: check-in saved")
    listOf(Point.SCREEN, Point.PHONE_STORE, Point.NETWORK, Point.GATEWAY, Point.SERVER).forEach { tracer.mark(good, it, true) }
    return tracer.mark(good, Point.READ_BACK, true, "matches")
}
