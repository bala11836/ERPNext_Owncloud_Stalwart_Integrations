package com.example.erp.core

import java.security.MessageDigest

/**
 * Alerts: what the phone shows for a signal (plans of 27 and 28 November 2026, finalised by the owner).
 *
 * A signal carries no content: a kind, sometimes a count, a number of hours and a reference. **Every word shown is
 * written here. Nothing shown is ever taken from the signal**, so a wrong or forged signal cannot put a name, an
 * amount or a text on a locked phone; a kind this app does not know is dropped. (This is true of every signal the
 * app handles. The server must send data-only signals: see `AlertService`.)
 */
enum class Strength {
    /** Rings: a decision waits for the person. */
    RING,

    /** The phone's normal alert sound. */
    ALERT,

    /** No sound: the alert appears or changes quietly. */
    QUIET,
}

/** One alert per slot on the phone, with its count. [id] is the phone's number for it; [lead] is where a tap goes. */
enum class Slot(val id: Int, val lead: Lead) {
    DECIDE(1, Lead.INBOX),
    REJECTED(2, Lead.INBOX),
    MESSAGE(3, Lead.CHAT),
    MAIL(4, Lead.MAIL),
    NOTICE(5, Lead.CHAT),
}

sealed interface AlertAction {
    data class Show(val slot: Slot, val words: String, val strength: Strength) : AlertAction
    data class Remove(val slot: Slot) : AlertAction

    /** An unknown or broken signal: nothing is shown. */
    data object Ignore : AlertAction
}

/**
 * What the phone remembers between signals so it can count and remove: for each thing that waits, a short
 * fingerprint of its reference, never the reference itself. Nothing readable about the business is kept.
 */
data class AlertState(val deciding: Set<String> = emptySet(), val rejected: Set<String> = emptySet())

object Alerts {
    private const val MAX_COUNT = 999
    private const val MAX_HOURS = 9999

    /**
     * The most fingerprints kept per list. A "decided elsewhere" signal can get lost on the way, so a list could
     * otherwise grow without end; the real Inbox sets the lists right when it loads (not built yet).
     */
    const val MAX_MARKS = 500

    /** The fingerprint kept for one waiting thing. The same thing always gives the same fingerprint. */
    fun mark(doctype: String, docname: String): String =
        MessageDigest.getInstance("SHA-256").digest("$doctype\n$docname".toByteArray()).take(8).joinToString("") { "%02x".format(it) }

    private fun mark(data: Map<String, String>): String? {
        val doctype = data["doctype"].orEmpty()
        val docname = data["docname"].orEmpty()
        return if (doctype.isEmpty() || docname.isEmpty() || doctype.length > 200 || docname.length > 200) null else mark(doctype, docname)
    }

    private fun number(text: String?, max: Int): Int? = text?.takeIf { it.length <= 6 && it.all { c -> c in '0'..'9' } && it.isNotEmpty() }?.toInt()?.coerceIn(0, max)

    fun waitingWords(count: Int): String = if (count <= 1) "Approval waiting" else "$count approvals waiting"

    fun rejectedWords(count: Int): String = if (count <= 1) "Rejected, to correct" else "$count rejected, to correct"

    fun reminderWords(count: Int, hours: Int?): String {
        val since = hours?.takeIf { it > 0 }?.let { if (it == 1) "1 hour" else "$it hours" }
        return when {
            count <= 1 -> "Reminder: an approval " + (since?.let { "has been waiting for $it" } ?: "is still waiting")
            else -> "Reminder: $count approvals are still waiting" + since?.let { ", the oldest for $it" }.orEmpty()
        }
    }

    /** What a test shows; it says that it is one. */
    const val TEST_WORDS = "Test alert. This is how an approval rings."

    /**
     * One signal in, the new state and what to do out. The server's kinds (owner's note of 28 November 2026):
     * `approval`, `verify` (something waits for a decision), `returned` (something came back to its sender, shown
     * as "rejected"), `reminder`, `remove`. `message`, `mail` and `notice` are for the chat and mail senders.
     * `test` is the phone's own.
     */
    fun handle(data: Map<String, String>, state: AlertState): Pair<AlertState, AlertAction> {
        when (data["kind"]) {
            "approval", "verify" -> {
                val mark = mark(data)
                val deciding = if (mark == null || state.deciding.size >= MAX_MARKS) state.deciding else state.deciding + mark
                // A signal without a usable reference still rings: a real approval is never dropped for a missing field.
                return state.copy(deciding = deciding) to AlertAction.Show(Slot.DECIDE, waitingWords(deciding.size), Strength.RING)
            }
            "returned" -> {
                val mark = mark(data)
                val rejected = if (mark == null || state.rejected.size >= MAX_MARKS) state.rejected else state.rejected + mark
                return state.copy(rejected = rejected) to AlertAction.Show(Slot.REJECTED, rejectedWords(rejected.size), Strength.ALERT)
            }
            "reminder" -> {
                val count = number(data["count"], MAX_COUNT) ?: return state to AlertAction.Ignore
                if (count == 0) return state to AlertAction.Ignore
                return state to AlertAction.Show(Slot.DECIDE, reminderWords(count, number(data["oldest_hours"], MAX_HOURS)), Strength.RING)
            }
            "remove" -> {
                val mark = mark(data) ?: return state to AlertAction.Ignore
                return when (mark) {
                    in state.deciding -> {
                        val left = state.deciding - mark
                        state.copy(deciding = left) to if (left.isEmpty()) AlertAction.Remove(Slot.DECIDE) else AlertAction.Show(Slot.DECIDE, waitingWords(left.size), Strength.QUIET)
                    }
                    in state.rejected -> {
                        val left = state.rejected - mark
                        state.copy(rejected = left) to if (left.isEmpty()) AlertAction.Remove(Slot.REJECTED) else AlertAction.Show(Slot.REJECTED, rejectedWords(left.size), Strength.QUIET)
                    }
                    else -> state to AlertAction.Ignore
                }
            }
            "message" -> return state to AlertAction.Show(Slot.MESSAGE, "New message", Strength.ALERT)
            "mail" -> return state to AlertAction.Show(Slot.MAIL, "New mail", Strength.QUIET)
            "notice" -> return state to AlertAction.Show(Slot.NOTICE, "Notice", Strength.QUIET)
            "test" -> return state to AlertAction.Show(Slot.DECIDE, TEST_WORDS, Strength.RING)
            else -> return state to AlertAction.Ignore
        }
    }
}
