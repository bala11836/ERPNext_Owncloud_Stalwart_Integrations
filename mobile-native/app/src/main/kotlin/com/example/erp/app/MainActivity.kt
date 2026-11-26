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
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.adaptive.navigationsuite.NavigationSuiteScaffold
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.core.content.edit
import com.example.erp.core.OutdoorSwitch
import com.example.erp.core.Palettes
import com.example.erp.core.Point
import com.example.erp.core.Trace
import com.example.erp.core.Tracer
import java.util.UUID

/** Every destination the frame can show. A screen that is not finished is not in this list, so it cannot be reached. */
enum class Place(val label: String, val icon: Int) {
    TRACE("Data trace", R.drawable.ic_trace),
    PHONE("This phone", R.drawable.ic_phone),
    DISPLAY("Display", R.drawable.ic_display),
}

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

        setContent {
            var automatic by remember { mutableStateOf(settings.getBoolean("outdoor-automatic", true)) }
            var forced by remember { mutableStateOf(settings.getBoolean("outdoor-forced", false)) }
            var bright by remember { mutableStateOf(false) }
            var lux by remember { mutableStateOf<Float?>(null) }

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
                var place by rememberSaveable { mutableStateOf(Place.TRACE) }
                var traces by remember { mutableStateOf(tracer.all()) }
                // Bottom bar on a phone, side rail on a tablet or a phone turned sideways: chosen by the window's width.
                NavigationSuiteScaffold(
                    navigationSuiteItems = {
                        for (item in Place.entries) {
                            item(
                                selected = place == item,
                                onClick = { place = item },
                                icon = { Icon(painterResource(item.icon), contentDescription = null) },
                                label = { Text(item.label) },
                            )
                        }
                    },
                ) {
                    Box(Modifier.statusBarsPadding()) {
                        when (place) {
                            Place.TRACE -> TraceScreen(traces, showValues = testBuild, onAddSample = if (testBuild) ({ addSample(); traces = tracer.all() }) else null)
                            Place.PHONE -> PhoneScreen(checkPhone(this@MainActivity), "${Build.MANUFACTURER} ${Build.MODEL}", BuildConfig.VERSION_NAME)
                            Place.DISPLAY -> DisplayScreen(
                                palette,
                                hasLightSensor = lightSensor != null,
                                automatic = automatic,
                                forced = forced,
                                lux = if (testBuild) lux else null,
                                onAutomatic = { automatic = it; settings.edit { putBoolean("outdoor-automatic", it) } },
                                onForced = { forced = it; settings.edit { putBoolean("outdoor-forced", it) } },
                            )
                        }
                    }
                }
            }
        }
    }

    /** Test builds only: one failed and one complete trace, so the screen can be checked before real calls exist (Phase 1). */
    private fun addSample(): Trace? {
        val bad = UUID.randomUUID().toString()
        tracer.start(bad, "Sample: check-out refused")
        listOf(Point.SCREEN, Point.PHONE_STORE, Point.GATEWAY).forEach { tracer.mark(bad, it, true) }
        tracer.mark(bad, Point.NETWORK, true, tookMs = 420)
        tracer.mark(bad, Point.SERVER, false, "Refused: outside the site", detail = "sample values: distance_m=180, radius_m=100")
        val good = UUID.randomUUID().toString()
        tracer.start(good, "Sample: check-in saved")
        listOf(Point.SCREEN, Point.PHONE_STORE, Point.NETWORK, Point.GATEWAY, Point.SERVER).forEach { tracer.mark(good, it, true) }
        return tracer.mark(good, Point.READ_BACK, true, "matches")
    }
}
