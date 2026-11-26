package com.example.erp.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SaverTest {
    private val id = "req_0123456789abcdef"
    private val args = mapOf("site" to "SITE-0001", "check_in_time" to "2026-11-26 08:57:00", "remarks" to null)
    private val kinds = mapOf("site" to ReadBack.Kind.TEXT, "check_in_time" to ReadBack.Kind.DATETIME)

    private fun save(first: Reply, second: Reply? = null, seen: MutableList<String> = mutableListOf()): SaveResult {
        val saver = Saver(Tracer()) { method, _, tracking -> seen += "$method|$tracking"; first }
        return saver.save(id, "Check-in", "hr.self_check_in", args, kinds, readBack = second?.let { reply -> { reply } })
    }

    private fun marks(result: SaveResult) = result.trace.marks.associate { it.point to it.ok }

    @Test
    fun savedAndReadBackTheSameIsACompleteGreenTrace() {
        val seen = mutableListOf<String>()
        val stored = mapOf("name" to "FAE-1", "site" to "SITE-0001", "check_in_time" to "2026-11-26 08:57:00.000000", "state" to "Submitted")
        val result = save(Reply.Answer(200, fields = mapOf("name" to "FAE-1"), tookMs = 420), Reply.Answer(200, fields = stored), seen)
        assertEquals(Outcome.SAVED, result.outcome)
        assertEquals("Saved.", result.sentence)
        assertTrue(result.trace.complete)
        assertEquals("Submitted", result.fields["state"])
        assertEquals(listOf("hr.self_check_in|$id"), seen) // the tracking number travels with the call
        assertEquals("fields: check_in_time, site", result.trace.marks.first().note) // names only, and no empty field
    }

    @Test
    fun aTimeZoneFaultIsCaughtAtReadBack() {
        val stored = mapOf("site" to "SITE-0001", "check_in_time" to "2026-11-26 03:27:00")
        val result = save(Reply.Answer(200), Reply.Answer(200, fields = stored))
        assertEquals(Outcome.STORED_DIFFERENTLY, result.outcome)
        assertEquals(Point.READ_BACK, result.trace.fault?.point)
        assertTrue(result.trace.fault!!.note.contains("check_in_time (time shifted by -5.5 hours"))
        assertFalse(result.trace.report().contains("03:27")) // values stay out of the shared report
        assertTrue(result.trace.report(withValues = true).contains("stored 2026-11-26 03:27:00"))
    }

    @Test
    fun aServerRuleRefusalShowsTheServersSentenceAndStopsAtPoint5() {
        val result = save(Reply.Answer(417, message = "You are 180 m outside the site."))
        assertEquals(Outcome.REFUSED, result.outcome)
        assertEquals("You are 180 m outside the site.", result.sentence)
        assertEquals(mapOf(Point.SCREEN to true, Point.NETWORK to true, Point.GATEWAY to true, Point.SERVER to false), marks(result))
        assertFalse(result.trace.report().contains("180")) // the server's sentence may hold a value: test builds only
    }

    @Test
    fun everyOtherAnswerIsSortedToItsPoint() {
        val signedOut = save(Reply.Answer(401))
        assertEquals(Outcome.NOT_SIGNED_IN, signedOut.outcome)
        assertEquals(Point.GATEWAY, signedOut.trace.fault?.point)

        val notAllowed = save(Reply.Answer(403, message = "You cannot check in at this site."))
        assertEquals(Outcome.NOT_ALLOWED, notAllowed.outcome)
        assertEquals("You cannot check in at this site.", notAllowed.sentence)
        assertEquals(Point.SERVER, notAllowed.trace.fault?.point)

        val broken = save(Reply.Answer(500, message = "Traceback (most recent call last) ..."))
        assertEquals(Outcome.SERVER_FAILED, broken.outcome)
        assertFalse(broken.sentence.contains("Traceback")) // never a raw server error on screen

        val silent = save(Reply.Answer(417))
        assertEquals("The server did not accept this, and gave no reason.", silent.sentence)

        val offline = save(Reply.NoConnection("UnknownHostException", tookMs = 30))
        assertEquals(Outcome.NO_CONNECTION, offline.outcome)
        assertEquals(Point.NETWORK, offline.trace.fault?.point)
        assertNull(offline.trace.marks.firstOrNull { it.point == Point.GATEWAY })
    }

    @Test
    fun aCrashInTheNetworkLayerIsAFailedPointNotACrashedApp() {
        val saver = Saver(Tracer()) { _, _, _ -> throw IllegalStateException("socket closed") }
        val result = saver.save(id, "Check-in", "hr.self_check_in", args)
        assertEquals(Outcome.NO_CONNECTION, result.outcome)
        assertEquals(Point.NETWORK, result.trace.fault?.point)
    }

    @Test
    fun aSaveThatCannotBeCheckedAgainIsStillSavedButNotGreen() {
        val result = save(Reply.Answer(200), Reply.NoConnection("timeout"))
        assertEquals(Outcome.SAVED, result.outcome)
        assertEquals("Saved. It could not be checked again just now.", result.sentence)
        assertEquals(Point.READ_BACK, result.trace.fault?.point)
        assertFalse(result.trace.complete)
    }

    @Test
    fun withNothingToCompareTheSaveEndsAtTheServer() {
        val saver = Saver(Tracer()) { _, _, _ -> Reply.Answer(200) }
        val result = saver.save(id, "Sign out", "push.unregister_device", mapOf("token" to "abc"))
        assertEquals(Outcome.SAVED, result.outcome)
        assertNull(result.trace.fault)
        assertNull(result.trace.marks.firstOrNull { it.point == Point.READ_BACK })
    }
}
