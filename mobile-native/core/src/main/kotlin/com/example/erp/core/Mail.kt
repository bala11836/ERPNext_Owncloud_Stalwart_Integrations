package com.example.erp.core

import java.net.IDN
import java.net.URI
import java.time.LocalDateTime

/**
 * The rules of mail that do not depend on a server or a screen (screen plan of 27 November 2026, points 14 to 17,
 * with the owner's changes: the list of received mail is "Received", because "Inbox" is the approvals place).
 */
enum class Folder(val label: String) { RECEIVED("Received"), SENT("Sent"), DRAFTS("Drafts"), ARCHIVE("Archive"), TRASH("Trash") }

data class Person(val name: String, val address: String)

data class Mail(
    val id: String,
    /** Mails that answer each other share one conversation. */
    val thread: String,
    val folder: Folder,
    val from: Person,
    val to: List<Person>,
    val cc: List<Person> = emptyList(),
    val subject: String,
    val body: String,
    val at: LocalDateTime,
    val unread: Boolean = false,
    /** File names. */
    val attachments: List<String> = emptyList(),
    /** Pictures the mail would fetch from the internet. They are not loaded until the person asks. */
    val remotePictures: Int = 0,
)

/** The mails of one conversation in one folder, oldest first. */
data class Conversation(val mails: List<Mail>) {
    val thread: String get() = mails.first().thread
    val newest: Mail get() = mails.last()
    val unread: Boolean get() = mails.any { it.unread }
}

object Mails {
    /** The folder as conversations, the one with the newest mail first. */
    fun conversations(mails: List<Mail>, folder: Folder): List<Conversation> =
        mails.filter { it.folder == folder }.groupBy { it.thread }.values
            .map { thread -> Conversation(thread.sortedBy { it.at }) }
            .sortedByDescending { it.newest.at }

    /**
     * True unless the address is at one of the company's own domains, compared exactly. An address that only
     * contains or resembles a company domain, and one that cannot be read, is outside.
     */
    fun outside(address: String, company: Set<String>): Boolean {
        val domain = address.trim().substringAfterLast('@', "").lowercase().trimEnd('.')
        return domain.isEmpty() || domain !in company
    }

    private val ADDRESS = Regex("[^@\\s<>\"(),;:]+@[A-Za-z0-9-]+(\\.[A-Za-z0-9-]+)+")
    private val BETWEEN = Regex("[,;\\s]+")

    /** What was typed in "To", as addresses: the ones that can be sent to, and the ones that cannot. */
    fun addresses(typed: String): Pair<List<String>, List<String>> =
        typed.split(BETWEEN).filter { it.isNotEmpty() }.distinct().partition { ADDRESS.matches(it) }

    private val PREFIX = Regex("^((re|fwd?|fw)\\s*:\\s*)+", RegexOption.IGNORE_CASE)

    fun replySubject(subject: String): String = "Re: " + subject.replace(PREFIX, "")

    fun forwardSubject(subject: String): String = "Fwd: " + subject.replace(PREFIX, "")

    /** Everyone a "reply all" goes to: the sender and all other recipients, never the person themselves, each once. */
    fun replyAll(mail: Mail, me: String): List<Person> =
        (listOf(mail.from) + mail.to + mail.cc).filter { !it.address.equals(me, ignoreCase = true) }.distinctBy { it.address.lowercase() }

    fun firstLine(body: String): String = Format.short(body.lineSequence().map { it.trim() }.firstOrNull { it.isNotEmpty() && !it.startsWith(">") }.orEmpty(), 80)

    /** The answered mail, quoted under a reply. */
    fun quoted(mail: Mail): String = "\n\n${mail.from.name} wrote:\n" + mail.body.lines().joinToString("\n") { "> $it" }

    private val HOST = Regex("[a-z0-9]([a-z0-9.-]*[a-z0-9])?")
    private val LINK = Regex("https?://[^\\s<>\"')\\]]+")

    /** The web links written in a mail's text, each once. */
    fun links(body: String): List<String> = LINK.findAll(body).map { it.value.trimEnd('.', ',', ';', ':', '!', '?') }.distinct().toList()

    /**
     * Where a link really leads: the host the browser would go to, in plain letters. A name written with
     * look-alike letters shows in its coded form ("xn--..."), and a name placed before an "@" is ignored, because
     * the browser ignores it too. Null when it is not a web address; such a link is never opened.
     */
    fun realHost(link: String): String? = try {
        val uri = URI(link)
        // A name with letters outside plain ASCII is not read as a host by the parser; it is taken from the raw
        // address part, without anything before an "@" and without a port.
        val named = uri.host ?: uri.rawAuthority?.substringAfterLast('@')?.substringBefore(':')
        val host = if (uri.scheme?.lowercase() in setOf("http", "https") && !named.isNullOrEmpty()) IDN.toASCII(named).lowercase() else null
        host?.takeIf { HOST.matches(it) }
    } catch (e: Exception) {
        null
    }
}
