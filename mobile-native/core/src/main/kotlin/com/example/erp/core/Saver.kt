package com.example.erp.core

/**
 * The one place every save passes through. It sends, sorts the answer to the point where it failed, reads the
 * record back and compares it, and writes each step into the trace, so no feature can save "silently".
 * The network itself (addresses, sign-in token, reading the server's answer) is a [Transport], added in Phase 1;
 * here it is an interface, so every path is tested without a server.
 */
sealed interface Reply {
    /** The server (or the gateway in front of it) answered. [message] is the server's own sentence, when it sent one. */
    data class Answer(val status: Int, val message: String? = null, val fields: Map<String, String?> = emptyMap(), val tookMs: Long = 0) : Reply

    /** Nothing answered: no signal, a timeout, an address that does not resolve. */
    data class NoConnection(val reason: String, val tookMs: Long = 0) : Reply
}

fun interface Transport {
    fun call(method: String, args: Map<String, String?>, trackingId: String): Reply
}

enum class Outcome { SAVED, STORED_DIFFERENTLY, REFUSED, NOT_ALLOWED, NOT_SIGNED_IN, NO_CONNECTION, SERVER_FAILED }

/** [sentence] is what the person reads: what happened and, where there is one, what to do. Never a code. */
data class SaveResult(val outcome: Outcome, val sentence: String, val trace: Trace, val fields: Map<String, String?> = emptyMap())

class Saver(private val tracer: Tracer, private val transport: Transport) {
    /**
     * @param id the action's unique request ID; it is also the tracking number and goes to the server with the call.
     * @param kinds the fields to compare after the save, each with its kind. Empty: nothing is compared.
     * @param readBack fetches the saved record again, given the server's answer (which holds the record's name).
     *   Null when the action has nothing to read back.
     */
    fun save(
        id: String,
        action: String,
        method: String,
        args: Map<String, String?>,
        kinds: Map<String, ReadBack.Kind> = emptyMap(),
        readBack: ((Map<String, String?>) -> Reply)? = null,
    ): SaveResult {
        tracer.start(id, action)
        // Field names only: the trace's notes never hold a value.
        tracer.mark(id, Point.SCREEN, true, "fields: " + args.filterValues { it != null }.keys.sorted().joinToString())

        val reply = try {
            transport.call(method, args, id)
        } catch (e: RuntimeException) {
            Reply.NoConnection(e.javaClass.simpleName)
        }
        if (reply is Reply.NoConnection) {
            tracer.mark(id, Point.NETWORK, false, "no answer", reply.tookMs, detail = reply.reason)
            return done(id, Outcome.NO_CONNECTION, "No connection. Nothing was sent. Try again when you have signal.")
        }
        reply as Reply.Answer
        tracer.mark(id, Point.NETWORK, true, tookMs = reply.tookMs)

        if (reply.status == 401) {
            tracer.mark(id, Point.GATEWAY, false, "not signed in (401)")
            return done(id, Outcome.NOT_SIGNED_IN, "You are signed out. Sign in again; nothing was saved.")
        }
        tracer.mark(id, Point.GATEWAY, true)

        when {
            reply.status in 200..299 -> tracer.mark(id, Point.SERVER, true, "accepted (${reply.status})")
            reply.status == 403 -> {
                tracer.mark(id, Point.SERVER, false, "not allowed (403)", detail = reply.message)
                return done(id, Outcome.NOT_ALLOWED, reply.message ?: "You are not allowed to do this.")
            }
            reply.status in 400..499 -> {
                tracer.mark(id, Point.SERVER, false, "refused by a server rule (${reply.status})", detail = reply.message)
                return done(id, Outcome.REFUSED, reply.message ?: "The server did not accept this, and gave no reason.")
            }
            else -> {
                tracer.mark(id, Point.SERVER, false, "the server failed (${reply.status})", detail = reply.message)
                return done(id, Outcome.SERVER_FAILED, "The server has a problem right now. Nothing was saved. Try again in a few minutes.")
            }
        }

        if (readBack == null || kinds.isEmpty()) return done(id, Outcome.SAVED, "Saved.", reply.fields)

        val again = try {
            readBack(reply.fields)
        } catch (e: RuntimeException) {
            Reply.NoConnection(e.javaClass.simpleName)
        }
        if (again !is Reply.Answer || again.status !in 200..299) {
            val why = if (again is Reply.Answer) "status ${again.status}" else "no answer"
            tracer.mark(id, Point.READ_BACK, false, "could not read the record back ($why)")
            // The save itself was accepted; only the check could not be made.
            return done(id, Outcome.SAVED, "Saved. It could not be checked again just now.", reply.fields)
        }
        val differences = ReadBack.differences(args, again.fields, kinds)
        tracer.mark(
            id, Point.READ_BACK, differences.isEmpty(), ReadBack.note(differences), again.tookMs,
            detail = differences.joinToString("; ") { "${it.field}: sent ${it.sent}, stored ${it.stored}" }.ifEmpty { null },
        )
        return if (differences.isEmpty()) done(id, Outcome.SAVED, "Saved.", again.fields)
        else done(id, Outcome.STORED_DIFFERENTLY, "Saved, but the server stored something different from what you entered. Please check it.", again.fields)
    }

    private fun done(id: String, outcome: Outcome, sentence: String, fields: Map<String, String?> = emptyMap()) =
        SaveResult(outcome, sentence, tracer.find(id)!!, fields)
}
