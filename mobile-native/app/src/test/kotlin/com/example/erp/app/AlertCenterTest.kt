package com.example.erp.app

import android.Manifest
import android.app.AlarmManager
import android.app.Application
import android.app.Notification
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import com.example.erp.core.AlertAction
import com.example.erp.core.Slot
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config

/** What the phone really shows, rings and schedules for a signal: the part between the rules and the person. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class AlertCenterTest {
    private val app: Application = RuntimeEnvironment.getApplication()
    private val payment = mapOf("kind" to "approval", "doctype" to "Payment Entry", "docname" to "payment")
    private val decided = mapOf("kind" to "remove", "doctype" to "Payment Entry", "docname" to "payment")

    /** The alerts in the phone's list, by the phone's number for each. */
    private fun shown(): Map<Int, String?> =
        shadowOf(app.getSystemService(NotificationManager::class.java)).activeNotifications.associate { it.id to it.notification.extras.getString(Notification.EXTRA_TITLE) }

    private fun reminders() = shadowOf(app.getSystemService(AlarmManager::class.java)).scheduledAlarms.size

    private fun key(present: Boolean) {
        app.getSharedPreferences("lock", Context.MODE_PRIVATE).edit().apply { if (present) putString("wrapped", "x") else clear() }.commit()
    }

    @Before
    fun setUp() {
        shadowOf(app).grantPermissions(Manifest.permission.POST_NOTIFICATIONS)
        AlertCenter.prepare(app)
        key(true)
        AlertCenter.clear(app)
    }

    @After
    fun tearDown() {
        AlertCenter.inApp = null
        Session.lock()
        AlertCenter.clear(app)
        key(false)
    }

    @Test
    fun anApprovalIsAQuietEntryAndARingingOneAndGoesWhenItIsDecided() {
        AlertCenter.receive(app, payment)
        assertEquals(mapOf(1 to "Payment waiting", 101 to "Payment waiting"), shown())
        AlertCenter.receive(app, decided)
        assertEquals(emptyMap<Int, String?>(), shown())
    }

    @Test
    fun aPhoneWithoutItsKeyShowsNothingAndRemindsOfNothing() {
        key(false)
        AlertCenter.receive(app, payment)
        assertEquals(emptyMap<Int, String?>(), shown())
        key(true)
        AlertCenter.receive(app, payment)
        AlertCenter.remindLater(app, Slot.DECIDE, asked = true)
        key(false)
        AlertCenter.remindDue(app)
        assertEquals(0, reminders())
        assertEquals(mapOf(1 to "Payment waiting"), shown()) // nothing new was rung
    }

    @Test
    fun remindMeStopsTheRingingComesBackAgainAndAgainAndEndsWhenItIsDecided() {
        AlertCenter.receive(app, payment)
        AlertCenter.remindLater(app, Slot.DECIDE, asked = true)
        assertEquals("the ringing stops, the quiet entry stays", mapOf(1 to "Payment waiting"), shown())
        assertEquals(1, reminders())
        AlertCenter.remindDue(app)
        assertEquals(mapOf(1 to "Reminder: an approval is still waiting", 101 to "Reminder: an approval is still waiting"), shown())
        assertEquals("the next one is set without another tap", 1, reminders())
        AlertCenter.receive(app, decided)
        assertEquals(0, reminders())
        AlertCenter.remindDue(app)
        assertEquals(emptyMap<Int, String?>(), shown())
    }

    @Test
    fun aReminderAskedForWithNothingKnownToThePhoneRingsOnceAndNotAgain() {
        AlertCenter.remindLater(app, Slot.DECIDE, asked = true)
        AlertCenter.remindDue(app)
        assertEquals("Reminder: an approval is still waiting", shown()[101])
        assertEquals(0, reminders())
        // Not asked for and nothing waiting: nothing rings.
        AlertCenter.clear(app)
        AlertCenter.remindLater(app, Slot.DECIDE)
        AlertCenter.remindDue(app)
        assertEquals(emptyMap<Int, String?>(), shown())
    }

    @Test
    fun aRestartSetsARunningReminderAgainAndClearingTakesEverything() {
        AlertCenter.afterRestart(app)
        assertEquals("no reminder was running", 0, reminders())
        AlertCenter.receive(app, payment)
        AlertCenter.remindLater(app, Slot.DECIDE, asked = true)
        shadowOf(app.getSystemService(AlarmManager::class.java)).scheduledAlarms.clear() // the phone forgot it
        AlertCenter.afterRestart(app)
        assertEquals(1, reminders())
        AlertCenter.clear(app)
        assertEquals(0, reminders())
        assertEquals(emptyMap<Int, String?>(), shown())
        AlertCenter.afterRestart(app)
        assertEquals(0, reminders())
    }

    @Test
    fun whileTheAppIsOpenAndUnlockedNothingIsPutOverItAndTheAppIsTold() {
        val told = mutableListOf<AlertAction.Show>()
        AlertCenter.inApp = { told += it }
        // Open on the screen but locked: the alert comes as always.
        AlertCenter.receive(app, payment)
        assertEquals(setOf(1, 101), shown().keys)
        assertEquals(0, told.size)
        AlertCenter.clear(app)
        Session.open(ByteArray(32))
        AlertCenter.receive(app, payment)
        assertEquals("only the quiet entry, no ringing one", setOf(1), shown().keys)
        assertEquals(listOf("Payment waiting"), told.map { it.words })
        // A chat message only changes its number: the app is not told, nothing rings.
        AlertCenter.receive(app, mapOf("kind" to "message", "room" to "r"))
        assertEquals(1, told.size)
        assertEquals(setOf(1, 3), shown().keys)
        // Without the phone's permission for alerts the line in the app still comes.
        shadowOf(app).denyPermissions(Manifest.permission.POST_NOTIFICATIONS)
        AlertCenter.receive(app, mapOf("kind" to "approval", "doctype" to "Leave Application", "docname" to "leave"))
        assertEquals(2, told.size)
    }

    @Test
    fun onlyThisAppsOwnAlertCanAskForOneThingAndAScreen() {
        val own = AlertCenter.openApp(app, Slot.DECIDE, "payment", InboxJump.Start.REJECT)
        assertEquals(InboxJump("payment", InboxJump.Start.REJECT), AlertCenter.asked(app, own))
        // The same wish from another app: it knows the names of the fields, not this app's word.
        val forged = Intent().putExtra(AlertCenter.OPEN_ITEM, "payment").putExtra(AlertCenter.OPEN_START, "REJECT")
        assertNull(AlertCenter.asked(app, forged))
        assertNull(AlertCenter.asked(app, Intent(forged).putExtra("open-token", "guess")))
        // Reopened from the list of recent apps, Android hands the old wish over again: it is not followed twice.
        assertNull(AlertCenter.asked(app, Intent(own).addFlags(Intent.FLAG_ACTIVITY_LAUNCHED_FROM_HISTORY)))
        // After the alerts were cleared an old alert's wish no longer counts.
        AlertCenter.clear(app)
        assertNull(AlertCenter.asked(app, own))
        assertNull(AlertCenter.asked(app, AlertCenter.openApp(app, Slot.DECIDE)))
    }
}
