package com.example.erp.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AlertsTest {
    private fun signal(kind: String, vararg more: Pair<String, String>) = mapOf("kind" to kind, *more)

    private fun approval(name: String) = signal("approval", "needs" to "decide", "doctype" to "Purchase Order", "docname" to name)

    /** Feeds signals in order and gives the last state and every action. */
    private fun run(vararg signals: Map<String, String>): Pair<AlertState, List<AlertAction>> {
        var state = AlertState()
        val actions = signals.map { signal -> Alerts.handle(signal, state).also { state = it.first }.second }
        return state to actions
    }

    @Test
    fun approvalsRingAndAreCountedOncePerThing() {
        val (state, actions) = run(approval("PO-1"), approval("PO-2"), approval("PO-1"), signal("verify", "doctype" to "Field Attendance Entry", "docname" to "FAE-9"))
        assertEquals(
            listOf("Approval waiting", "2 approvals waiting", "2 approvals waiting", "3 approvals waiting"),
            actions.map { (it as AlertAction.Show).words },
        )
        assertTrue(actions.all { (it as AlertAction.Show).strength == Strength.RING && it.slot == Slot.DECIDE })
        assertEquals(3, state.deciding.size)
    }

    @Test
    fun removingTakesOneAwayQuietlyAndTheLastOneRemovesTheAlert() {
        val (state, actions) = run(
            approval("PO-1"), approval("PO-2"),
            signal("remove", "doctype" to "Purchase Order", "docname" to "PO-1"),
            signal("remove", "doctype" to "Purchase Order", "docname" to "PO-1"), // told twice: nothing happens the second time
            signal("remove", "doctype" to "Purchase Order", "docname" to "PO-2"),
        )
        assertEquals(AlertAction.Show(Slot.DECIDE, "Approval waiting", Strength.QUIET), actions[2])
        assertEquals(AlertAction.Ignore, actions[3])
        assertEquals(AlertAction.Remove(Slot.DECIDE), actions[4])
        assertEquals(AlertState(), state)
    }

    @Test
    fun whatCameBackToMeIsItsOwnQuieterAlert() {
        val back = signal("returned", "needs" to "decide", "doctype" to "Field Attendance Entry", "docname" to "FAE-1")
        val (state, actions) = run(back, approval("PO-1"), signal("remove", "doctype" to "Field Attendance Entry", "docname" to "FAE-1"))
        assertEquals(AlertAction.Show(Slot.REJECTED, "Rejected, to correct", Strength.ALERT), actions[0])
        assertEquals(AlertAction.Remove(Slot.REJECTED), actions[2])
        assertEquals(1, state.deciding.size) // the approval is untouched
        assertEquals("3 rejected, to correct", Alerts.rejectedWords(3))
    }

    @Test
    fun aReminderSaysThatItIsOneAndHowLong() {
        assertEquals("Reminder: an approval has been waiting for 4 hours", Alerts.reminderWords(1, 4))
        assertEquals("Reminder: an approval has been waiting for 1 hour", Alerts.reminderWords(1, 1))
        assertEquals("Reminder: 3 approvals are still waiting, the oldest for 8 hours", Alerts.reminderWords(3, 8))
        assertEquals("Reminder: an approval is still waiting", Alerts.reminderWords(1, null))
        val (state, actions) = run(signal("reminder", "count" to "3", "oldest_hours" to "8"))
        assertEquals(AlertAction.Show(Slot.DECIDE, "Reminder: 3 approvals are still waiting, the oldest for 8 hours", Strength.RING), actions.single())
        assertEquals(AlertState(), state) // a reminder counts nothing itself: the server counted
        // A reminder that says nothing waits, or says nonsense, shows nothing.
        for (bad in listOf(signal("reminder"), signal("reminder", "count" to "0"), signal("reminder", "count" to "-2"), signal("reminder", "count" to "many"), signal("reminder", "count" to "99999999999"))) {
            assertEquals(bad.toString(), AlertAction.Ignore, run(bad).second.single())
        }
        assertEquals("Reminder: 999 approvals are still waiting", (run(signal("reminder", "count" to "5000")).second.single() as AlertAction.Show).words)
    }

    @Test
    fun nothingShownIsEverTakenFromTheSignal() {
        val secret = "Payment of 1,50,000.00 to A. Example"
        val loaded = mapOf(
            "kind" to "approval", "doctype" to secret, "docname" to secret, "site" to secret, "site_label" to secret,
            "title" to secret, "body" to secret, "message" to secret, "amount" to "150000",
        )
        val (state, action) = Alerts.handle(loaded, AlertState())
        assertEquals(AlertAction.Show(Slot.DECIDE, "Approval waiting", Strength.RING), action)
        // What is remembered is a short fingerprint, not the reference.
        assertFalse(state.deciding.single().contains("Example"))
        assertEquals(16, state.deciding.single().length)
        for (kind in listOf("approval", "verify", "returned", "reminder", "message", "mail", "notice", "test")) {
            val words = (Alerts.handle(loaded + ("kind" to kind) + ("count" to "2"), AlertState()).second as AlertAction.Show).words
            assertFalse("$kind: $words", words.contains("Example") || words.contains("150000") || words.contains("1,50,000"))
        }
    }

    @Test
    fun anUnknownOrBrokenSignalShowsNothingButARealApprovalIsNeverDropped() {
        for (bad in listOf(emptyMap(), signal(""), signal("APPROVAL"), signal("pay-now"), signal("remove"), signal("remove", "doctype" to "X"))) {
            val (state, action) = Alerts.handle(bad, AlertState())
            assertEquals(bad.toString(), AlertAction.Ignore, action)
            assertEquals(AlertState(), state)
        }
        // An approval without a usable reference still rings; it is just not counted or removable by name.
        val (state, action) = Alerts.handle(signal("approval"), AlertState())
        assertEquals(AlertAction.Show(Slot.DECIDE, "Approval waiting", Strength.RING), action)
        assertEquals(AlertState(), state)
        assertEquals(AlertState(), Alerts.handle(signal("approval", "doctype" to "x".repeat(500), "docname" to "y"), AlertState()).first)
    }

    @Test
    fun chatMailAndNoticesHaveTheirOwnWordsAndStrengths() {
        assertEquals(AlertAction.Show(Slot.MESSAGE, "New message", Strength.ALERT), Alerts.handle(signal("message"), AlertState()).second)
        assertEquals(AlertAction.Show(Slot.MAIL, "New mail", Strength.QUIET), Alerts.handle(signal("mail"), AlertState()).second)
        assertEquals(AlertAction.Show(Slot.NOTICE, "Notice", Strength.QUIET), Alerts.handle(signal("notice"), AlertState()).second)
        assertEquals(AlertAction.Show(Slot.DECIDE, Alerts.TEST_WORDS, Strength.RING), Alerts.handle(signal("test"), AlertState()).second)
        assertEquals(listOf(Lead.INBOX, Lead.INBOX, Lead.CHAT, Lead.MAIL, Lead.CHAT), Slot.entries.map { it.lead })
        assertEquals(Slot.entries.size, Slot.entries.map { it.id }.toSet().size)
    }
}
