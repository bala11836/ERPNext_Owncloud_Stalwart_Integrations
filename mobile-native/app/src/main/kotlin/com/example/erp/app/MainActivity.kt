package com.example.erp.app

import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.adaptive.navigationsuite.NavigationSuiteScaffold
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.res.painterResource
import com.example.erp.core.Point
import com.example.erp.core.Trace
import com.example.erp.core.Tracer
import java.util.UUID

/** Every destination the frame can show. A screen that is not finished is not in this list, so it cannot be reached. */
enum class Place(val label: String, val icon: Int) {
    TRACE("Data trace", R.drawable.ic_trace),
    PHONE("This phone", R.drawable.ic_phone),
}

class MainActivity : ComponentActivity() {
    private val tracer = Tracer()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // No screenshots, and a blank card in the app switcher: the app will show personal data.
        window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)
        val testBuild = BuildConfig.DEBUG
        setContent {
            ErpTheme {
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
                    when (place) {
                        Place.TRACE -> TraceScreen(traces, showValues = testBuild, onAddSample = if (testBuild) ({ addSample(); traces = tracer.all() }) else null)
                        Place.PHONE -> PhoneScreen(checkPhone(this), "${Build.MANUFACTURER} ${Build.MODEL}", BuildConfig.VERSION_NAME)
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
