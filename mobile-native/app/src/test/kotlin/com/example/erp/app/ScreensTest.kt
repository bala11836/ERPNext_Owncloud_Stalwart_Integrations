package com.example.erp.app

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.semantics.getOrNull
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.unit.dp
import com.example.erp.core.Palette
import com.example.erp.core.Palettes
import com.example.erp.core.Tracer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

/**
 * The robot that walks every link. In every look, at phone and tablet width, at normal and double font size, it
 * opens every place in the frame and every item on it, and fails when a destination is missing, when anything
 * that can be tapped is smaller than a finger, or when text runs off the side of the screen.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [35])
class ScreensTest {
    @get:Rule
    val compose = createComposeRule()

    private val phone = PhoneCheck(
        listOf(
            PhoneLine(StatusKind.OK, R.drawable.ic_fingerprint, "Fingerprint sensor", "Ready to use."),
            PhoneLine(StatusKind.WARN, R.drawable.ic_phone, "Android 15", "Supported."),
        ),
        usable = true,
    )

    private fun show(palette: Palette, testBuild: Boolean = true, withTraces: Boolean = true) {
        val tracer = Tracer()
        if (withTraces) sampleTraces(tracer)
        compose.setContent {
            var traces by androidx.compose.runtime.remember { mutableStateOf(tracer.all()) }
            var automatic by androidx.compose.runtime.remember { mutableStateOf(true) }
            var forced by androidx.compose.runtime.remember { mutableStateOf(false) }
            var note by androidx.compose.runtime.remember { mutableStateOf<String?>(null) }
            ErpTheme(if (forced) Palettes.OUTDOOR else palette) {
                AppFrame(
                    FrameState(if (forced) Palettes.OUTDOOR else palette, testBuild, traces, phone, "Test Phone", "0.1.0", hasLightSensor = true, automaticOutdoor = automatic, forcedOutdoor = forced, lux = 24f, safeNote = note),
                    onAddSample = { sampleTraces(tracer); traces = tracer.all() },
                    onAutomaticOutdoor = { automatic = it },
                    onForcedOutdoor = { forced = it },
                    onTryConnection = { tracer.start("req_0123456789abcdef", "Connection test"); tracer.mark("req_0123456789abcdef", com.example.erp.core.Point.NETWORK, false, "no answer"); traces = tracer.all() },
                    onSafeNote = { note = "A note saved Today, 10:42 was read back from the safe." },
                )
            }
        }
    }

    private fun place(place: Place) = compose.onNode(hasText(place.label) and hasClickAction())

    /** Everything that can be tapped is at least 48 dp tall, and no text reaches past the screen's side. */
    private fun checkLayout(where: String) {
        val root = compose.onRoot().fetchSemanticsNode()
        val density = root.layoutInfo.density
        val min = with(density) { 48.dp.toPx() }
        val tappable = SemanticsMatcher("can be tapped") { it.config.getOrNull(androidx.compose.ui.semantics.SemanticsActions.OnClick) != null }
        for (node in compose.onAllNodes(tappable).fetchSemanticsNodes()) {
            assertTrue("$where: a tap target is only ${node.size.height} px tall (needs $min)", node.size.height >= min - 1)
        }
        val text = SemanticsMatcher("has text") { it.config.getOrNull(SemanticsProperties.Text) != null }
        for (node in compose.onAllNodes(text).fetchSemanticsNodes()) {
            val words = node.config[SemanticsProperties.Text].joinToString()
            assertTrue("$where: \"$words\" has no size", node.size.width > 0 && node.size.height > 0)
            assertTrue("$where: \"$words\" runs off the side", node.boundsInRoot.left >= -1 && node.boundsInRoot.right <= root.size.width + 1)
        }
    }

    private fun walk(palette: Palette, wide: Boolean) {
        show(palette)
        val name = "${palette.name}${if (wide) " wide" else ""}"
        // Every place in the frame opens its own finished screen.
        for (place in Place.entries) {
            place(place).performClick()
            compose.onNode(hasText(place.title) and !hasClickAction()).assertIsDisplayed()
            checkLayout("$name / ${place.label}")
        }
        // Every item on Data trace opens its detail, and the way back works.
        place(Place.TRACE).performClick()
        for (action in listOf("Sample: check-out refused", "Sample: check-in saved")) {
            compose.onNode(hasText(action, substring = true) and hasClickAction()).performScrollTo().performClick()
            compose.onNodeWithText("1. Screen: OK").assertIsDisplayed()
            compose.onNodeWithText("Copy this trace").performScrollTo().assertIsDisplayed()
            checkLayout("$name / trace detail")
            if (!wide) compose.onNodeWithText("Back to the list").performScrollTo().performClick()
            compose.onNode(hasText("Data trace") and !hasClickAction()).assertIsDisplayed()
        }
        // Every situation of the Welcome screens, and the help screen behind each one and the way back.
        place(Place.WELCOME).performClick()
        for (situation in Situation.entries) {
            compose.onNodeWithText("Situation: ${situation.label}").assertIsDisplayed()
            checkLayout("$name / welcome, ${situation.label}")
            compose.onNodeWithContentDescription("Help").performClick()
            shown("How it works")
            checkLayout("$name / how it works")
            compose.onNodeWithText("Back").performScrollTo().performClick()
            compose.onNodeWithText("Situation: ${situation.label}").performClick()
        }
        compose.onNodeWithText("Situation: ${Situation.NEW.label}").assertIsDisplayed()
        // Every chat room opens and leads back, and so does the list of colleagues.
        place(Place.CHAT).performClick()
        for (room in listOf("Notices", "Site A", "Site A engineers", "Project manager")) {
            tap(room)
            reach(compose.onNode(hasText(room) and !hasClickAction())).assertIsDisplayed()
            checkLayout("$name / chat room $room")
            if (!wide) reach(compose.onNodeWithContentDescription("Back")).performClick()
        }
        tap("New chat with a colleague")
        compose.onNodeWithText("New chat").assertIsDisplayed()
        checkLayout("$name / new chat")
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        compose.onNode(hasText("Chat") and !hasClickAction()).assertIsDisplayed()
        // Every mail conversation opens and leads back; so do the folders, a new mail and an attachment.
        place(Place.MAIL).performClick()
        for (sender in listOf("Project manager", "Supplier accounts", "IT Support", "HR (2)")) {
            tap(sender)
            reach(compose.onNode(hasText("Reply") and hasClickAction())).assertIsDisplayed()
            checkLayout("$name / mail from $sender")
            if (!wide) reach(compose.onNodeWithContentDescription("Back")).performClick()
        }
        tap("Folder: Received")
        shown("Folders")
        checkLayout("$name / mail folders")
        tap("Sent")
        shown("Folder: Sent")
        tap("Write a mail")
        shown("New mail")
        checkLayout("$name / new mail")
        tap("Discard this mail")
        tap("Folder: Sent")
        tap("Received")
        tap("Project manager")
        tap("pour-checklist.pdf")
        shown("Attachments open here, inside the app.")
        checkLayout("$name / attachment")
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        reach(compose.onNode(hasText("Reply") and hasClickAction())).assertIsDisplayed()
    }

    private fun type(label: String, text: String) = reach(compose.onNode(androidx.compose.ui.test.hasSetTextAction() and hasText(label))).performTextInput(text)

    private fun absent(text: String) = assertEquals(text, 0, compose.onAllNodesWithText(text, substring = true).fetchSemanticsNodes().size)

    @Test
    fun mailFromOutsideSaysSoAndALinkShowsWhereItLeadsBeforeItOpens() {
        show(Palettes.LIGHT)
        place(Place.MAIL).performClick()
        // Unread is said in words; an outside sender too.
        reach(compose.onNode(hasText("Project manager") and hasText("New") and hasClickAction())).assertIsDisplayed()
        reach(compose.onNode(hasText("IT Support") and hasText("Outside") and hasClickAction())).assertIsDisplayed()
        tap("Supplier accounts")
        shown("This sender is not in the company.")
        // Pictures from the internet wait for a tap.
        shown("2 pictures from the internet are not loaded")
        tap("Show pictures")
        shown("2 pictures from the internet shown.")
        // The link says where it leads, asks, and "do not open" opens nothing.
        tap("Link to portal.supplier-example.net")
        shown("It leads to portal.supplier-example.net.")
        tap("Do not open")
        shown("Stand-in: nothing is sent.")
        tap("Link to portal.supplier-example.net")
        tap("Open portal.supplier-example.net")
        shown("the browser would open portal.supplier-example.net")
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        // Opening read it. The company's name in front of another domain is shown as what it is.
        tap("IT Support")
        shown("Link to example.com.account-check.net")
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        assertEquals(0, compose.onAllNodes(hasText("Supplier accounts") and hasText("New")).fetchSemanticsNodes().size)
        // A sender inside the company carries no warning.
        tap("Project manager")
        absent("This sender is not in the company.")
    }

    @Test
    fun aReplyIsFilledInWarnsBeforeLeavingTheCompanyAndLandsInSent() {
        show(Palettes.LIGHT)
        place(Place.MAIL).performClick()
        tap("Project manager")
        tap("Reply to all") // the sender and the engineer in copy, not me
        shown("pm@example.com, engineer@example.com")
        shown("Re: Pour checklist for Friday")
        shown("Project manager wrote:")
        absent("goes outside the company")
        tap("Send")
        shown("Stand-in: put in Sent, not sent.")
        tap("Folder: Received")
        tap("Sent")
        reach(compose.onNode(hasText("To: pm@example.com, engineer@example.com") and hasClickAction())).assertIsDisplayed()
        // A new mail: no Send until it can be sent, an unreadable address is named, an outside one is warned about.
        tap("Write a mail")
        assertEquals(0, compose.onAllNodes(hasText("Send") and hasClickAction()).fetchSemanticsNodes().size)
        type("To", "engineer")
        type("Subject", "Tomorrow")
        shown("Not a mail address: engineer.")
        assertEquals(0, compose.onAllNodes(hasText("Send") and hasClickAction()).fetchSemanticsNodes().size)
        type("To", "@supplier-example.net")
        shown("This mail goes outside the company: engineer@supplier-example.net")
        tap("Send")
        reach(compose.onNode(hasText("To: engineer@supplier-example.net") and hasClickAction())).assertIsDisplayed()
    }

    @Test
    fun aMessageIsSentWaitsWithoutSignalAndNoticesCannotBeWrittenTo() {
        show(Palettes.LIGHT)
        place(Place.CHAT).performClick()
        // Notices first, then my site; unread shown in words.
        compose.onNode(hasText("Site A") and hasText("2 new") and hasClickAction()).assertIsDisplayed()
        compose.onNode(hasText("Site A") and hasClickAction()).performClick()
        shown("Company room. Messages here are kept by the company.")
        assertEquals("nothing to send yet, so no Send button", 0, compose.onAllNodesWithText("Send").fetchSemanticsNodes().size)
        compose.onNode(androidx.compose.ui.test.hasSetTextAction()).performTextInput("On my way")
        tap("Send")
        shown("On my way")
        assertEquals(0, compose.onAllNodesWithText("Waiting to send").fetchSemanticsNodes().size)
        // A tap on a message answers it.
        reach(compose.onNode(hasText("Two more vibrators", substring = true) and hasClickAction())).performClick()
        shown("Replying to Store keeper")
        tap("Signal: on (stand-in)") // now without signal
        compose.onNode(androidx.compose.ui.test.hasSetTextAction()).performTextInput("I have it")
        tap("Send")
        shown("Reply to Store keeper")
        shown("Waiting to send")
        tap("Signal: off (stand-in)") // back online: it is sent
        assertEquals(0, compose.onAllNodesWithText("Waiting to send").fetchSemanticsNodes().size)
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        // Opening the room read its messages; the list shows my last line.
        assertEquals(0, compose.onAllNodesWithText("2 new").fetchSemanticsNodes().size)
        reach(compose.onNode(hasText("You: I have it", substring = true) and hasClickAction())).assertIsDisplayed()
        // Nobody writes in Notices.
        tap("Notices")
        shown("Nobody can write in this room.")
        assertEquals(0, compose.onAllNodes(androidx.compose.ui.test.hasSetTextAction()).fetchSemanticsNodes().size)
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        // A new one-to-one chat opens empty, is not a company room, and the same colleague opens the same chat again.
        tap("New chat with a colleague")
        tap("HR")
        shown("No messages yet.")
        assertEquals(0, compose.onAllNodesWithText("Company room", substring = true).fetchSemanticsNodes().size)
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        tap("New chat with a colleague")
        tap("HR")
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        assertEquals(1, compose.onAllNodes(hasText("HR") and hasClickAction()).fetchSemanticsNodes().size)
    }

    /** Scrolled to as a person would; something outside any scrolling area is simply where it is. */
    private fun reach(node: androidx.compose.ui.test.SemanticsNodeInteraction) = node.also { runCatching { it.performScrollTo() } }

    private fun tap(label: String) = reach(compose.onNode(hasText(label) and hasClickAction())).performClick()

    private fun shown(text: String) = reach(compose.onNodeWithText(text, substring = true)).assertIsDisplayed()

    /** Every button of the Welcome screens leads to the situation it names; none is a dead end. */
    @Test
    fun everyWelcomeButtonLeadsSomewhere() {
        show(Palettes.LIGHT)
        place(Place.WELCOME).performClick()
        shown("Your phone becomes your key.")
        tap("Request access")
        shown("Request sent")
        shown("Meet them with this phone and your ID.")
        shown("+91 90••• ••000")
        // Cancelling asks once more, and "keep" really keeps.
        tap("Cancel my request")
        shown("Cancel this request?")
        tap("Keep my request")
        shown("Request sent")
        tap("Check again") // the project manager confirmed
        shown("Checks your request next.")
        tap("Check again") // the admin approved
        shown("Approved. Make your key")
        shown("STEP 5 OF 5")
        tap("Make my key")
        shown("Welcome back")
        shown("This phone's key belongs to name@example.com.")
        tap("Open with fingerprint") // the stand-in answers with a miss
        shown("3 tries left")
        tap("Open with fingerprint") // and then with the last one
        shown("not recognised 5 times in a row")
        compose.onNodeWithText("Situation: ${Situation.GONE.label}").performClick() // round to "new here"
        repeat(Situation.UNLOCK.ordinal) { compose.onNodeWithText("Situation:", substring = true).performClick() }
        // From waiting, a confirmed cancel leads back to the start.
        compose.onNodeWithText("Situation: ${Situation.UNLOCK.label}").performClick() // after a miss
        shown("3 tries left")
        repeat(Situation.entries.size - Situation.MISS.ordinal + Situation.WAITING.ordinal) { compose.onNodeWithText("Situation:", substring = true).performClick() }
        tap("Cancel my request")
        tap("Yes, cancel my request")
        shown("Your phone becomes your key.")
    }

    @Test
    fun refusedRanOutAndKeyGoneSayWhyAndLeadToANewRequest() {
        show(Palettes.LIGHT)
        place(Place.WELCOME).performClick()
        fun go(to: Situation) {
            while (compose.onAllNodesWithText("Situation: ${to.label}").fetchSemanticsNodes().isEmpty()) compose.onNodeWithText("Situation:", substring = true).performClick()
        }
        go(Situation.OFFLINE)
        shown("Cannot check right now: no connection.")
        go(Situation.REFUSED)
        shown("The admin refused this request. Reason given: The mobile number does not match our records.")
        tap("Request again")
        shown("Your phone becomes your key.")
        go(Situation.EXPIRED)
        shown("not approved in the allowed time")
        tap("Request again")
        shown("Your phone becomes your key.")
        go(Situation.WEAK_PHONE)
        shown("No key was made.")
        assertEquals(0, compose.onAllNodesWithText("Make my key").fetchSemanticsNodes().size)
        go(Situation.GONE)
        shown("not recognised 5 times in a row")
        tap("Request a new key")
        shown("Your phone becomes your key.")
    }

    @Test fun everyLinkLight() = walk(Palettes.LIGHT, wide = false)

    @Test fun everyLinkDark() = walk(Palettes.DARK, wide = false)

    @Test fun everyLinkOutdoor() = walk(Palettes.OUTDOOR, wide = false)

    @Test @Config(qualifiers = "w1100dp-h800dp") fun everyLinkOnATablet() = walk(Palettes.LIGHT, wide = true)

    @Test @Config(qualifiers = "w1100dp-h800dp") fun everyLinkOnATabletInTheDark() = walk(Palettes.DARK, wide = true)

    @Test @Config(fontScale = 2.0f) fun everyLinkAtDoubleFontSize() = walk(Palettes.LIGHT, wide = false)

    @Test @Config(fontScale = 2.0f) fun everyLinkOutdoorAtDoubleFontSize() = walk(Palettes.OUTDOOR, wide = false)

    @Test
    fun aFailedTraceNamesItsPointAndKeepsValuesToTestBuilds() {
        show(Palettes.LIGHT, testBuild = true)
        // The row card says the state in words (a pill) and where it stopped, before anything is opened.
        compose.onNode(hasText("Sample: check-out refused", substring = true) and hasText("Failed") and hasText("Stopped at 5. Server function") and hasClickAction()).assertIsDisplayed()
        compose.onNode(hasText("Sample: check-in saved", substring = true) and hasText("Saved") and hasClickAction()).performScrollTo().assertIsDisplayed()
        compose.onNode(hasText("Sample: check-out refused", substring = true) and hasClickAction()).performScrollTo().performClick()
        compose.onNodeWithText("5. Server function: Failed").assertIsDisplayed()
        compose.onNodeWithText("Usually means: a server rule said no, or the server failed.").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("6. Read-back: Not reached").performScrollTo().assertIsDisplayed() // below the first screenful: scrolled to, as a person would
        assertEquals(1, compose.onAllNodesWithText("sample values", substring = true).fetchSemanticsNodes().size)
    }

    @Test
    fun theRealAppShowsNoValuesAndNoSampleButton() {
        val tracer = Tracer()
        sampleTraces(tracer)
        compose.setContent {
            ErpTheme(Palettes.LIGHT) {
                AppFrame(FrameState(Palettes.LIGHT, testBuild = false, tracer.all(), phone, "Test Phone", "0.1.0", true, true, false, lux = 24f), {}, {}, {})
            }
        }
        assertEquals(0, compose.onAllNodesWithText("Add a sample trace", substring = true).fetchSemanticsNodes().size)
        assertEquals(0, compose.onAllNodesWithText("Try the connection", substring = true).fetchSemanticsNodes().size)
        assertEquals("the Welcome stand-in is not in the real app", 0, compose.onAllNodesWithText(Place.WELCOME.label).fetchSemanticsNodes().size)
        assertEquals("the chat stand-in is not in the real app", 0, compose.onAllNodesWithText(Place.CHAT.label).fetchSemanticsNodes().size)
        assertEquals("the mail stand-in is not in the real app", 0, compose.onAllNodesWithText(Place.MAIL.label).fetchSemanticsNodes().size)
        compose.onNode(hasText("Sample: check-out refused", substring = true) and hasClickAction()).performClick()
        assertEquals(0, compose.onAllNodesWithText("sample values", substring = true).fetchSemanticsNodes().size)
        place(Place.PHONE).performClick()
        assertEquals(0, compose.onAllNodesWithText("Safe", substring = true).fetchSemanticsNodes().size)
        place(Place.DISPLAY).performClick()
        assertEquals(0, compose.onAllNodesWithText("lux", substring = true).fetchSemanticsNodes().size)
    }

    @Test
    fun theSafeTestCardSaysWhatIsInTheSafeAndOnlyInTestBuilds() {
        show(Palettes.LIGHT)
        place(Place.PHONE).performClick()
        shown("Empty.")
        tap("Save a test note in the safe")
        shown("was read back from the safe")
        checkLayout("safe test card")
    }

    @Test
    fun tryingTheConnectionAddsARowThatSaysWhereItStopped() {
        show(Palettes.LIGHT, withTraces = false)
        tap("Try the connection (test builds)")
        compose.onNode(hasText("Connection test") and hasText("Failed") and hasText("Stopped at 3. Network") and hasClickAction()).assertIsDisplayed()
        checkLayout("after a connection test")
    }

    @Test
    fun anEmptyTraceListSaysWhatWillAppear() {
        show(Palettes.LIGHT, withTraces = false)
        compose.onNodeWithText("No actions yet", substring = true).assertIsDisplayed()
        compose.onNodeWithText("Add a sample trace (test builds)").performClick()
        compose.onNode(hasText("Sample: check-in saved", substring = true) and hasClickAction()).assertIsDisplayed()
    }

    @Test
    fun theOutdoorSwitchChangesTheLookAndSaysSo() {
        show(Palettes.DARK)
        place(Place.DISPLAY).performClick()
        compose.onNodeWithText("Dark: follows your phone's night mode").assertIsDisplayed()
        compose.onNode(hasText("Outdoor mode now", substring = true) and hasClickAction()).performClick()
        compose.onNodeWithText("Outdoor: strongest contrast, larger text").assertIsDisplayed()
        compose.onNode(hasText("Outdoor mode now", substring = true) and hasClickAction()).performClick()
        compose.onNodeWithText("Dark: follows your phone's night mode").assertIsDisplayed()
    }
}
