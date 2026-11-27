package com.example.erp.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.adaptive.navigationsuite.NavigationSuiteScaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import com.example.erp.core.Palette
import com.example.erp.core.Trace

/** Every destination the frame can show. A screen that is not finished is not in this list, so it cannot be reached. */
enum class Place(val label: String, val title: String, val icon: Int, val testOnly: Boolean = false) {
    TRACE("Data trace", "Data trace", R.drawable.ic_trace),
    PHONE("This phone", "This phone", R.drawable.ic_phone),
    DISPLAY("Display", "Display", R.drawable.ic_display),

    /** The Welcome screens against a stand-in, until the server part for access requests exists. Test builds only. */
    WELCOME("Welcome", "Welcome preview", R.drawable.ic_key, testOnly = true),

    /** The chat screens against a stand-in, until the chat server and sign-in exist. Test builds only. */
    CHAT("Chat", "Chat", R.drawable.ic_chat, testOnly = true),

    /** The mail screens against a stand-in, until the mail sign-in exists. Test builds only. */
    MAIL("Mail", "Mail", R.drawable.ic_mail, testOnly = true),
}

/** What the frame shows, handed in from outside, so the whole frame can be drawn in a test without a phone's sensors. */
class FrameState(
    val palette: Palette,
    val testBuild: Boolean,
    val traces: List<Trace>,
    val phone: PhoneCheck,
    val model: String,
    val version: String,
    val hasLightSensor: Boolean,
    val automaticOutdoor: Boolean,
    val forcedOutdoor: Boolean,
    val lux: Float?,
    /** Test builds: what the test note in the safe says, or null when the safe is empty. */
    val safeNote: String? = null,
)

/**
 * The frame around every screen: a bottom bar on a phone, a side rail on a tablet or a phone turned sideways,
 * chosen by the window's width.
 */
@Composable
fun AppFrame(state: FrameState, onAddSample: () -> Unit, onAutomaticOutdoor: (Boolean) -> Unit, onForcedOutdoor: (Boolean) -> Unit, onSafeNote: (() -> Unit)? = null, onTryConnection: (() -> Unit)? = null) {
    var place by rememberSaveable { mutableStateOf(Place.TRACE) }
    NavigationSuiteScaffold(
        navigationSuiteItems = {
            for (item in Place.entries.filter { !it.testOnly || state.testBuild }) {
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
                Place.TRACE -> TraceScreen(state.traces, showValues = state.testBuild, onAddSample = if (state.testBuild) onAddSample else null, onTryConnection = if (state.testBuild) onTryConnection else null)
                Place.PHONE -> PhoneScreen(state.phone, state.model, state.version, state.safeNote, if (state.testBuild) onSafeNote else null)
                Place.WELCOME -> WelcomePreviewScreen()
                Place.CHAT -> ChatPreviewScreen()
                Place.MAIL -> MailPreviewScreen()
                Place.DISPLAY -> DisplayScreen(
                    state.palette,
                    hasLightSensor = state.hasLightSensor,
                    automatic = state.automaticOutdoor,
                    forced = state.forcedOutdoor,
                    lux = if (state.testBuild) state.lux else null,
                    onAutomatic = onAutomaticOutdoor,
                    onForced = onForcedOutdoor,
                )
            }
        }
    }
}
