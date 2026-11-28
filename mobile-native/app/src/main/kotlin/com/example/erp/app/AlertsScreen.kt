package com.example.erp.app

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
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp

/** Every tap on the Alerts screen. All are required. */
class AlertActions(
    /** Does the one thing that unblocks alerts: asks the phone's permission, or opens the right phone setting. */
    val fix: (Fix) -> Unit,
    /** Opens the phone's own switch for one kind of alert. */
    val openKind: (AlertKind) -> Unit,
    /** Makes a signal on the phone itself after a short wait, so the phone can be locked first. */
    val signal: (data: Map<String, String>) -> Unit,
    val removeAll: () -> Unit,
)

/** How long a test waits before it shows, so the person can lock the phone or close the app first. */
const val TEST_WAIT_SECONDS = 10

/**
 * Alerts (under More): whether alerts can reach this phone and why not, the kinds with the phone's own switch for
 * each, and a test every person can run on their own phone. Test builds add one button per kind of signal and the
 * phone's delivery address.
 */
@Composable
fun AlertsScreen(view: AlertsView, testBuild: Boolean, actions: AlertActions) {
    val clipboard = LocalClipboardManager.current
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(Look.Gap)) {
        Column(Modifier.widthIn(max = 640.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Alerts", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
            val fix = view.fix
            if (view.blocked != null && fix != null) ActionMessage(StatusKind.BAD, "Alerts are blocked: ${view.blocked}", fix.label, { actions.fix(fix) })
            else Notice(StatusKind.OK, "Alerts can show on this phone.")
            if (view.blocked == null && !view.fullPage) {
                ActionMessage(StatusKind.WARN, "The full page over a locked screen is not allowed on this phone yet. Approvals still ring, as a banner.", Fix.FULL_PAGE.label, { actions.fix(Fix.FULL_PAGE) })
            }
            if (!view.connected) Notice(StatusKind.NONE, "This build is not connected to the alert service, so nothing arrives by itself. The test below still works.")
            Text(
                "Approvals ring at any time, unless your phone is on silent or on Do not disturb. Reminders come every 4 hours between 07:00 and 21:00. An alert never shows a name or an amount; you see those after your fingerprint.",
                style = MaterialTheme.typography.bodyLarge, color = Look.Muted,
            )
            MainButton("Test my alerts", { actions.signal(mapOf("kind" to "test")) })
            Text("It rings in about $TEST_WAIT_SECONDS seconds; the phone may take up to a minute. Lock the phone now, or close the app, to see the full page a real approval shows.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)

            Eyebrow("The kinds")
            for (kind in AlertKind.entries) RowCard(R.drawable.ic_bell, kind.title, kind.text + " Tap for the phone's own switch.", onClick = { actions.openKind(kind) })

            if (testBuild) {
                Eyebrow("Test signals (test builds)")
                Text("Each arrives after about $TEST_WAIT_SECONDS seconds (the phone may take up to a minute), also when the app is closed.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
                fun approval(name: String) = mapOf("kind" to "approval", "needs" to "decide", "doctype" to "Test", "docname" to name)
                OutlineButton("Signal: an approval", { actions.signal(approval("one")) })
                OutlineButton("Signal: a second approval", { actions.signal(approval("two")) })
                OutlineButton("Signal: reminder, 3 waiting, 8 hours", { actions.signal(mapOf("kind" to "reminder", "count" to "3", "oldest_hours" to "8")) })
                OutlineButton("Signal: the first approval was decided", { actions.signal(mapOf("kind" to "remove", "doctype" to "Test", "docname" to "one")) })
                OutlineButton("Signal: rejected, to correct", { actions.signal(mapOf("kind" to "returned", "doctype" to "Test", "docname" to "back")) })
                OutlineButton("Signal: a chat message", { actions.signal(mapOf("kind" to "message")) })
                OutlineButton("Signal: mail", { actions.signal(mapOf("kind" to "mail")) })
                OutlineButton("Signal: a notice", { actions.signal(mapOf("kind" to "notice")) })
                OutlineButton("Signal: with a name and an amount in it", { actions.signal(mapOf("kind" to "approval", "doctype" to "Test", "docname" to "three", "title" to "Pay A. Example 1,50,000.00", "body" to "Pay A. Example 1,50,000.00")) })
                OutlineButton("Remove every alert now", actions.removeAll, danger = true)

                Eyebrow("Delivery address (test builds)")
                val address = view.address
                if (address == null) {
                    Text(if (view.connected) "Google has not given this phone an address yet. Come back to this screen in a moment." else "None: this build is not connected to the alert service.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                } else {
                    Text("With this address the owner can send this one phone a test signal. It lets nobody read anything or sign in. Send it privately.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
                    Panel { Text(address, style = MaterialTheme.typography.bodyMedium) }
                    OutlineButton("Copy the delivery address", { clipboard.setText(AnnotatedString(address)) })
                }
            }
        }
    }
}
