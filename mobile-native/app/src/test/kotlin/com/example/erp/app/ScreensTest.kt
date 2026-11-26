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
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
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

    private val phone = PhoneCheck(listOf(StatusKind.OK to "Fingerprint sensor: ready", StatusKind.OK to "Android 15: supported"), usable = true)

    private fun show(palette: Palette, testBuild: Boolean = true, withTraces: Boolean = true) {
        val tracer = Tracer()
        if (withTraces) sampleTraces(tracer)
        compose.setContent {
            var traces by androidx.compose.runtime.remember { mutableStateOf(tracer.all()) }
            var automatic by androidx.compose.runtime.remember { mutableStateOf(true) }
            var forced by androidx.compose.runtime.remember { mutableStateOf(false) }
            ErpTheme(if (forced) Palettes.OUTDOOR else palette) {
                AppFrame(
                    FrameState(if (forced) Palettes.OUTDOOR else palette, testBuild, traces, phone, "Test Phone", "0.1.0", hasLightSensor = true, automaticOutdoor = automatic, forcedOutdoor = forced, lux = 24f),
                    onAddSample = { sampleTraces(tracer); traces = tracer.all() },
                    onAutomaticOutdoor = { automatic = it },
                    onForcedOutdoor = { forced = it },
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
        compose.onNode(hasText("Sample: check-out refused", substring = true) and hasClickAction()).performClick()
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
        compose.onNode(hasText("Sample: check-out refused", substring = true) and hasClickAction()).performClick()
        assertEquals(0, compose.onAllNodesWithText("sample values", substring = true).fetchSemanticsNodes().size)
        place(Place.DISPLAY).performClick()
        assertEquals(0, compose.onAllNodesWithText("lux", substring = true).fetchSemanticsNodes().size)
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
