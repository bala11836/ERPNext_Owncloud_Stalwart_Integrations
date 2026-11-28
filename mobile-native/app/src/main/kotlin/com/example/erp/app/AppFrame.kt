package com.example.erp.app

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.adaptive.navigationsuite.NavigationSuiteScaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import com.example.erp.core.Lead
import com.example.erp.core.Palette
import com.example.erp.core.Trace

/**
 * The five places of the app, in the order agreed with the owner on 27 November 2026. "Inbox" is what waits for
 * the person's decision; received mail is inside Mail. A place whose real screen does not exist yet is shown in
 * test builds only, so the real app never offers a place that leads nowhere.
 */
enum class Place(val label: String, val title: String, val icon: Int, val testOnly: Boolean = false) {
    /** Today against a stand-in with made-up days, until sign-in exists. Test builds only. */
    TODAY("Today", "Today", R.drawable.ic_today, testOnly = true),

    /** Inbox against a stand-in with made-up items, until sign-in exists. Test builds only. */
    INBOX("Inbox", "Inbox", R.drawable.ic_inbox, testOnly = true),

    /** The chat screens against a stand-in, until the chat server and sign-in exist. Test builds only. */
    CHAT("Chat", "Chat", R.drawable.ic_chat, testOnly = true),

    /** The mail screens against a stand-in, until the mail sign-in exists. Test builds only. */
    MAIL("Mail", "Mail", R.drawable.ic_mail, testOnly = true),
    MORE("More", "More", R.drawable.ic_more),
}

/** What "More" leads to. Each opens a finished screen and leads back. */
enum class Tool(val title: String, val text: String, val icon: Int, val testOnly: Boolean = false) {
    ALERTS("Alerts", "Whether alerts reach this phone, and a test.", R.drawable.ic_bell),
    DISPLAY("Display", "The look in use and Outdoor mode.", R.drawable.ic_display),
    PHONE("This phone", "Fingerprint sensor, secure chip, app version.", R.drawable.ic_phone),
    TRACE("Data trace", "Where the data of each action went.", R.drawable.ic_trace),

    /** The Welcome screens against a stand-in, until the server part for access requests exists. Test builds only. */
    WELCOME("Welcome preview", "The first-start screens against a stand-in. Test builds.", R.drawable.ic_key, testOnly = true),
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
    val alerts: AlertsView = AlertsView(),
)

/**
 * The frame around every screen: a bottom bar on a phone, a side rail on a tablet or a phone turned sideways,
 * chosen by the window's width.
 *
 * @param sign asks for the fingerprint to sign one decision. Required: no screen may decide anything without it.
 * @param goTo the place an alert asked for; [onWent] is called once it was looked at.
 */
@Composable
fun AppFrame(
    state: FrameState,
    sign: (what: String, done: (Boolean, String?) -> Unit) -> Unit,
    alertActions: AlertActions,
    onAddSample: () -> Unit,
    onAutomaticOutdoor: (Boolean) -> Unit,
    onForcedOutdoor: (Boolean) -> Unit,
    onSafeNote: (() -> Unit)? = null,
    onTryConnection: (() -> Unit)? = null,
    goTo: Place? = null,
    onWent: () -> Unit = {},
) {
    val places = Place.entries.filter { !it.testOnly || state.testBuild }
    var place by rememberSaveable { mutableStateOf(places.first()) }
    var tool by rememberSaveable { mutableStateOf<Tool?>(null) }
    // A tap on an alert asks for a place. Only a place this build shows is opened; the wish is then forgotten.
    LaunchedEffect(goTo) {
        if (goTo != null) {
            if (goTo in places) {
                place = goTo
                tool = null
            }
            onWent()
        }
    }
    NavigationSuiteScaffold(
        navigationSuiteItems = {
            for (item in places) {
                item(
                    selected = place == item,
                    // A tap on More always shows More's own list, also when one of its screens is open.
                    onClick = { place = item; tool = null },
                    icon = { Icon(painterResource(item.icon), contentDescription = null) },
                    label = { Text(item.label) },
                )
            }
        },
    ) {
        Box(Modifier.statusBarsPadding()) {
            when (place) {
                Place.TODAY -> TodayPreviewScreen(onOpen = {
                    place = when (it) {
                        Lead.INBOX -> Place.INBOX
                        Lead.CHAT -> Place.CHAT
                        Lead.MAIL -> Place.MAIL
                    }
                })
                Place.INBOX -> InboxPreviewScreen(sign)
                Place.CHAT -> ChatPreviewScreen()
                Place.MAIL -> MailPreviewScreen()
                Place.MORE -> MoreScreen(state, tool, { tool = it }, alertActions, onAddSample, onAutomaticOutdoor, onForcedOutdoor, onSafeNote, onTryConnection)
            }
        }
    }
}

@Composable
private fun MoreScreen(
    state: FrameState,
    tool: Tool?,
    onTool: (Tool?) -> Unit,
    alertActions: AlertActions,
    onAddSample: () -> Unit,
    onAutomaticOutdoor: (Boolean) -> Unit,
    onForcedOutdoor: (Boolean) -> Unit,
    onSafeNote: (() -> Unit)?,
    onTryConnection: (() -> Unit)?,
) {
    if (tool == null) {
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(Look.Gap), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Column(Modifier.widthIn(max = 640.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("More", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
                for (item in Tool.entries.filter { !it.testOnly || state.testBuild }) RowCard(item.icon, item.title, item.text, onClick = { onTool(item) })
            }
        }
        return
    }
    BackHandler { onTool(null) }
    Column(Modifier.fillMaxSize()) {
        TopBar(Modifier.padding(horizontal = 8.dp), onBack = { onTool(null) })
        Box(Modifier.weight(1f)) {
            when (tool) {
                Tool.TRACE -> TraceScreen(state.traces, showValues = state.testBuild, onAddSample = if (state.testBuild) onAddSample else null, onTryConnection = if (state.testBuild) onTryConnection else null)
                Tool.PHONE -> PhoneScreen(state.phone, state.model, state.version, state.safeNote, if (state.testBuild) onSafeNote else null)
                Tool.WELCOME -> WelcomePreviewScreen()
                Tool.ALERTS -> AlertsScreen(state.alerts, state.testBuild, alertActions)
                Tool.DISPLAY -> DisplayScreen(
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
