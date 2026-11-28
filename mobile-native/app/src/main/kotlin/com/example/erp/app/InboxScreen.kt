package com.example.erp.app

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import com.example.erp.core.Decided
import com.example.erp.core.Decision
import com.example.erp.core.DecisionResult
import com.example.erp.core.Format
import com.example.erp.core.Inbox
import com.example.erp.core.Item
import com.example.erp.core.Sent
import com.example.erp.core.SentState
import com.example.erp.core.Tone
import java.time.LocalDateTime

/** Every tap in Inbox that changes something outside the screen. All are required. */
class InboxActions(
    /**
     * Asks for the fingerprint, showing [what] is being signed. [done] gets true only after a real match; otherwise
     * false, with a sentence when there is something to tell the person. A decision is never sent without it.
     */
    val sign: (what: String, done: (signed: Boolean, trouble: String?) -> Unit) -> Unit,
    /** [modified] is the version the person looked at; the server refuses a decision made on an older one. */
    val decide: (id: String, modified: String, decision: Decision, reason: String?) -> DecisionResult,
    val hold: (id: String, modified: String, until: LocalDateTime, reason: String?) -> Unit,
)

private enum class InboxView(val word: String, val title: String) { WAITING("Waiting", "Waiting for me"), DECIDED("Decided", "Decided by me"), SENT("Sent", "Sent by me") }

private enum class Screen { LIST, ITEM, REJECT, HOLD, RESULT, PAST }

private fun kind(tone: Tone) = when (tone) {
    Tone.GOOD -> StatusKind.OK
    Tone.CARE -> StatusKind.WARN
    Tone.WRONG -> StatusKind.BAD
    Tone.PLAIN -> StatusKind.NONE
    Tone.WAITING -> StatusKind.WAIT
}

/**
 * Inbox: what waits for the person's decision, what they decided, and where what they sent is now.
 *
 * Built in: two decisions only, Approve and Reject, each signed with the fingerprint, and the fingerprint question
 * says what is signed; Approve is offered only after the person said they have seen the evidence; a rejection
 * always goes back to the sender, its reason is optional; "Decide later" is a hold with any date and time, not a
 * decision; without a connection nothing can be decided; nothing is shown as decided before the answer came.
 */
@Composable
fun InboxScreen(waiting: List<Item>, decided: List<Decided>, sent: List<Sent>, now: LocalDateTime, online: Boolean, actions: InboxActions) {
    var view by rememberSaveable { mutableStateOf(InboxView.WAITING) }
    var step by rememberSaveable { mutableStateOf(Screen.LIST) }
    var openId by rememberSaveable { mutableStateOf<String?>(null) }
    var trouble by remember(openId) { mutableStateOf<String?>(null) }
    var result by remember { mutableStateOf<DecisionResult?>(null) }
    var decidedTitle by remember { mutableStateOf("") }

    val item = waiting.firstOrNull { it.id == openId }
    // "I have looked" belongs to one version of one item: a changed item must be looked at again.
    var seen by rememberSaveable(openId, item?.modified) { mutableStateOf(false) }
    val past = decided.firstOrNull { it.item.id == openId }
    val toList = { step = Screen.LIST; openId = null; result = null }
    val open = { id: String -> openId = id; step = Screen.ITEM }

    fun decide(target: Item, decision: Decision, reason: String?) {
        trouble = null
        actions.sign(Inbox.question(decision, target)) { signed, why ->
            if (signed) {
                decidedTitle = target.title
                result = actions.decide(target.id, target.modified, decision, reason)
                step = Screen.RESULT
            } else {
                trouble = why
            }
        }
    }

    when {
        step == Screen.RESULT && result != null -> {
            BackHandler(onBack = toList)
            Result(decidedTitle, result!!, now, next = Inbox.sections(waiting, now).flatMap { it.items }.firstOrNull { Inbox.canDecide(it) && it.id != openId }, waitingCount = waiting.count { Inbox.canDecide(it) && it.id != openId },
                onLookAgain = { seen = false; result = null; step = Screen.ITEM }, onNext = { result = null; open(it) }, onList = toList)
        }
        // Without a connection these two fall back to the item, which says that nothing can be decided now.
        step == Screen.REJECT && item != null && online && Inbox.canDecide(item) -> {
            BackHandler { step = Screen.ITEM }
            Reject(item, trouble, onBack = { step = Screen.ITEM }) { reason -> decide(item, Decision.REJECTED, reason) }
        }
        step == Screen.HOLD && item != null && online && Inbox.canDecide(item) -> {
            BackHandler { step = Screen.ITEM }
            HoldChooser(item, now, onBack = { step = Screen.ITEM }) { until, reason -> actions.hold(item.id, item.modified, until, reason); toList() }
        }
        (step == Screen.ITEM || step == Screen.REJECT || step == Screen.HOLD) && item != null -> {
            BackHandler(onBack = toList)
            ItemView(item, now, online, seen, trouble, onSeen = { seen = it }, onBack = toList, onApprove = { decide(item, Decision.APPROVED, null) }, onReject = { trouble = null; step = Screen.REJECT }, onHold = { step = Screen.HOLD })
        }
        step == Screen.PAST && past != null -> {
            BackHandler(onBack = toList)
            PastView(past, now, onBack = toList)
        }
        else -> Page {
            Text("Inbox", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
            ViewSwitch(view) { view = it }
            Text(view.title, style = MaterialTheme.typography.titleMedium, color = Look.Ink)
            if (!online) Notice(StatusKind.NONE, "No connection. This is the last copy. Deciding needs a connection.")
            when (view) {
                InboxView.WAITING -> {
                    val sections = Inbox.sections(waiting, now)
                    if (sections.isEmpty()) Notice(StatusKind.OK, "Nothing is waiting for you.")
                    for (section in sections) {
                        Eyebrow(section.heading)
                        for (row in section.items) WaitingRow(row, now) { open(row.id) }
                    }
                }
                InboxView.DECIDED -> {
                    if (decided.isEmpty()) Text("You have not decided anything yet.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                    for (row in decided) {
                        val since = row.since?.let { " $it" }.orEmpty()
                        RowCard(
                            R.drawable.ic_inbox, row.item.title, "${row.decision.done} by you, ${Format.dateTime(row.at, now)}.$since",
                            pill = (if (row.decision == Decision.APPROVED) StatusKind.OK else StatusKind.WARN) to row.decision.done,
                            onClick = { openId = row.item.id; step = Screen.PAST },
                        )
                    }
                }
                InboxView.SENT -> {
                    if (sent.isEmpty()) Text("You have not sent anything for a decision.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                    // What was rejected is mine to correct, so it comes first.
                    for (row in sent.sortedBy { it.state != SentState.REJECTED }) {
                        val (pillKind, word) = when (row.state) {
                            SentState.WAITING -> StatusKind.WAIT to "Waiting"
                            SentState.APPROVED -> StatusKind.OK to "Approved"
                            SentState.REJECTED -> StatusKind.BAD to "Rejected"
                            SentState.ON_HOLD -> StatusKind.WAIT to "On hold"
                        }
                        RowCard(R.drawable.ic_forward, row.title, Inbox.sentLine(row, now), pill = pillKind to word)
                    }
                }
            }
        }
    }
}

/** Every Inbox screen is one scrolling page in one readable column, so nothing is squeezed at any size. */
@Composable
private fun Page(content: @Composable ColumnScope.() -> Unit) {
    Column(Modifier.fillMaxSize().imePadding().verticalScroll(rememberScrollState()).padding(Look.Gap)) {
        Column(Modifier.widthIn(max = 640.dp), verticalArrangement = Arrangement.spacedBy(12.dp), content = content)
    }
}

/** The three views. Side by side when there is room; one under the other with large text. */
@Composable
private fun ViewSwitch(current: InboxView, onChoose: (InboxView) -> Unit) {
    @Composable
    fun button(view: InboxView, modifier: Modifier) {
        if (view == current) MainButton(view.word, { onChoose(view) }, modifier) else OutlineButton(view.word, { onChoose(view) }, modifier)
    }
    if (LocalDensity.current.fontScale > 1.3f) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) { for (view in InboxView.entries) button(view, Modifier) }
    } else {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { for (view in InboxView.entries) button(view, Modifier.weight(1f)) }
    }
}

@Composable
private fun WaitingRow(item: Item, now: LocalDateTime, onOpen: () -> Unit) {
    val deadline = Inbox.deadline(item, now)
    val extra = listOfNotNull(item.hold?.let { Inbox.holdLine(it, now) }, "You sent this.".takeIf { item.sentByMe }).joinToString(" ")
    RowCard(
        R.drawable.ic_inbox,
        item.title,
        Inbox.rowLine(item, now) + (if (extra.isEmpty()) "" else "\n$extra"),
        pill = when {
            item.rejection != null -> StatusKind.BAD to "Rejected"
            deadline != null && deadline.first != Tone.PLAIN -> kind(deadline.first) to deadline.second
            item.hold != null -> StatusKind.WAIT to "On hold"
            else -> null
        },
        onClick = onOpen,
    )
}

@Composable
private fun Trail(item: Item, now: LocalDateTime) {
    if (item.trail.isEmpty()) return
    Eyebrow("What happened so far")
    Panel {
        for (step in item.trail) {
            Text("${step.what} by ${step.who}, ${Format.dateTime(step.at, now)}", style = MaterialTheme.typography.bodyLarge)
            if (step.reason != null) Text(step.reason!!, style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
        }
        Text("Waiting for you since ${Format.dateTime(item.waitingSince, now)}", style = MaterialTheme.typography.bodyLarge)
    }
}

@Composable
private fun Evidence(item: Item) {
    if (item.lines.isEmpty()) return
    val unusual = item.lines.count { it.unusual != null }
    Eyebrow(if (unusual == 0) "What it is about" else "What it is about ($unusual to look at closely)")
    Panel {
        for (line in item.lines) {
            Text(line.title, style = MaterialTheme.typography.titleMedium)
            Text(line.text, style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
            if (line.unusual != null) Status(StatusKind.WARN, line.unusual!!)
        }
    }
}

@Composable
private fun ItemHead(item: Item, now: LocalDateTime, onBack: () -> Unit) {
    TopBar(onBack = onBack)
    Text(item.title, style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
    Inbox.amount(item)?.let { Text(it, style = MaterialTheme.typography.headlineMedium, color = Look.Ink) }
    Text("From ${item.from}", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
    Inbox.deadline(item, now)?.let { (tone, words) -> Status(kind(tone), words) }
}

@Composable
private fun ItemView(
    item: Item,
    now: LocalDateTime,
    online: Boolean,
    seen: Boolean,
    trouble: String?,
    onSeen: (Boolean) -> Unit,
    onBack: () -> Unit,
    onApprove: () -> Unit,
    onReject: () -> Unit,
    onHold: () -> Unit,
) = Page {
    ItemHead(item, now, onBack)
    item.hold?.let { Notice(StatusKind.WAIT, Inbox.holdLine(it, now)) }
    Trail(item, now)
    Evidence(item)
    val rejection = item.rejection
    when {
        rejection != null -> {
            Notice(StatusKind.BAD, Inbox.rejectionLine(rejection, now))
            Text("Correct it where you made it and present it again. It can be presented as often as needed.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
        }
        item.sentByMe -> Notice(StatusKind.INFO, "You sent this. Someone else must decide it.")
        Inbox.amountUnreadable(item) -> Notice(StatusKind.BAD, "The amount is missing or cannot be read on this phone, so nothing can be decided here. Open it on the web.")
        !online -> Notice(StatusKind.NONE, "Needs a connection. Nothing can be decided now.")
        else -> {
            if (trouble != null) Notice(StatusKind.WARN, trouble)
            // Approve is offered only after the person says they have seen what they sign.
            SwitchRow("I have looked at everything above", "Needed before you can approve.", seen, onSeen)
            if (seen) MainButton("Approve with your fingerprint", onApprove)
            OutlineButton("Reject", onReject, danger = true)
            OutlineButton("Decide later", onHold)
        }
    }
}

@Composable
private fun Field(value: String, onChange: (String) -> Unit, label: String) {
    OutlinedTextField(value, onChange, Modifier.fillMaxWidth(), label = { Text(label) }, textStyle = MaterialTheme.typography.bodyLarge, minLines = 2, maxLines = 5, shape = RoundedCornerShape(Look.Corner))
}

/** One of the quick reasons, or none. A second tap on the chosen one takes it away again. */
@Composable
private fun QuickReasons(choices: List<String>, chosen: String?, onChoose: (String?) -> Unit) {
    for (choice in choices) RowCard(R.drawable.ic_forward, choice, if (choice == chosen) "Chosen. Tap again to take it away." else "", selected = choice == chosen, onClick = { onChoose(if (choice == chosen) null else choice) })
}

@Composable
private fun Reject(item: Item, trouble: String?, onBack: () -> Unit, onReject: (reason: String?) -> Unit) {
    // In memory only, like everything a person types.
    var quick by remember(item.id) { mutableStateOf<String?>(null) }
    var typed by remember(item.id) { mutableStateOf("") }
    Page {
        TopBar(onBack = onBack)
        Text("Reject", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
        Text(item.title, style = MaterialTheme.typography.titleMedium, color = Look.Ink)
        Notice(StatusKind.INFO, "It goes back to ${item.from} to change and present again. A reason is not required, but it tells them what to change.")
        QuickReasons(Inbox.REJECT_REASONS, quick) { quick = it }
        Field(typed, { typed = it.take(Inbox.MAX_REASON) }, "In your own words (optional)")
        if (trouble != null) Notice(StatusKind.WARN, trouble)
        MainButton("Reject with your fingerprint", { onReject(Inbox.reason(quick, typed)) })
        OutlineButton("Do not reject", onBack)
    }
}

/** A day and a time, chosen with large plus and minus buttons that work with gloves. No limit on how far ahead. */
@Composable
private fun Stepper(label: String, value: String, less: String, more: String, onLess: () -> Unit, onMore: () -> Unit) {
    Text(label, style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlineButton(less, onLess, Modifier.weight(1f))
        OutlineButton(more, onMore, Modifier.weight(1f))
    }
    Text(value, style = MaterialTheme.typography.titleMedium, color = Look.Ink)
}

@Composable
private fun HoldChooser(item: Item, now: LocalDateTime, onBack: () -> Unit, onHold: (until: LocalDateTime, reason: String?) -> Unit) {
    var quick by remember(item.id) { mutableStateOf<String?>(null) }
    var typed by remember(item.id) { mutableStateOf("") }
    var until by remember(item.id) { mutableStateOf(Inbox.holdTime(now.plusHours(1).withMinute(0), now)) }
    val set = { wanted: LocalDateTime -> until = Inbox.holdTime(wanted, now) }
    Page {
        TopBar(onBack = onBack)
        Text("Decide later", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
        Text(item.title, style = MaterialTheme.typography.titleMedium, color = Look.Ink)
        Notice(StatusKind.INFO, "This puts it on hold; it is not a decision. ${item.from} will see until when, and why if you say so. You are reminded at that time.")
        Eyebrow("Until when")
        OutlineButton("In 1 hour", { set(now.plusHours(1)) })
        OutlineButton("In 2 hours", { set(now.plusHours(2)) })
        OutlineButton("Tomorrow, 09:00", { set(now.toLocalDate().plusDays(1).atTime(9, 0)) })
        Stepper("Day", Format.date(until.toLocalDate()), "1 day earlier", "1 day later", { set(until.minusDays(1)) }, { set(until.plusDays(1)) })
        Stepper("Time", until.toLocalTime().toString().take(5), "30 min earlier", "30 min later", { set(until.minusMinutes(30)) }, { set(until.plusMinutes(30)) })
        Notice(StatusKind.WAIT, "On hold until ${Format.dateTime(until, now)}")
        Eyebrow("Why (optional)")
        QuickReasons(Inbox.HOLD_REASONS, quick) { quick = it }
        Field(typed, { typed = it.take(Inbox.MAX_REASON) }, "In your own words (optional)")
        MainButton("Put on hold", { onHold(until, Inbox.reason(quick, typed)) })
        OutlineButton("Do not put on hold", onBack)
    }
}

@Composable
private fun Result(title: String, result: DecisionResult, now: LocalDateTime, next: Item?, waitingCount: Int, onLookAgain: () -> Unit, onNext: (String) -> Unit, onList: () -> Unit) = Page {
    Text(title, style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
    when (result) {
        is DecisionResult.Done -> Notice(StatusKind.OK, result.sentence)
        is DecisionResult.Taken -> Notice(StatusKind.INFO, "Already ${result.decision.done.lowercase()} by ${result.by}, ${Format.dateTime(result.at, now)}. Nothing was decided by you.")
        DecisionResult.Changed -> {
            Notice(StatusKind.WARN, "This was changed after you opened it. Nothing was decided. Look at it again.")
            MainButton("Look at it again", onLookAgain)
        }
        DecisionResult.NotAllowed -> Notice(StatusKind.BAD, "You are not allowed to decide this. Nothing was decided.")
        DecisionResult.NoConnection -> Notice(StatusKind.NONE, "No connection. Nothing was decided. Try again when you have signal.")
        is DecisionResult.Failed -> Notice(StatusKind.BAD, result.sentence)
    }
    if (result !is DecisionResult.Changed && next != null) {
        MainButton(if (waitingCount == 1) "Open the next one" else "Open the next one ($waitingCount more)", { onNext(next.id) }, forward = true)
    }
    OutlineButton("Back to the list", onList)
}

@Composable
private fun PastView(past: Decided, now: LocalDateTime, onBack: () -> Unit) = Page {
    ItemHead(past.item, now, onBack)
    Notice(if (past.decision == Decision.APPROVED) StatusKind.OK else StatusKind.WARN, "${past.decision.done} by you, ${Format.dateTime(past.at, now)}." + past.reason?.let { " Reason: $it" }.orEmpty())
    past.since?.let { Text(it, style = MaterialTheme.typography.bodyLarge, color = Look.Ink) }
    Evidence(past.item)
    Text("A decision cannot be undone here. If it was a mistake, the document is cancelled or amended on the web by the people allowed to.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
}
