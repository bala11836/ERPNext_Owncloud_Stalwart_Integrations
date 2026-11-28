package com.example.erp.app

import android.app.KeyguardManager
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.example.erp.core.Alerts
import com.example.erp.core.Palettes
import com.example.erp.core.Slot
import java.lang.ref.WeakReference

/**
 * The full page over a locked screen when an approval rings, as in the earlier app (the look of an incoming
 * call): the app's mark, the alert's fixed words, and two large buttons.
 *
 * It shows nothing private and decides nothing. "Later" stops the ringing; the alert stays in the list. "Open"
 * asks the phone to unlock and then opens the app, whose own fingerprint lock comes before any detail.
 */
class RingActivity : ComponentActivity() {
    private var words by mutableStateOf("")
    private val slot get() = Slot.entries.find { it.name == intent.getStringExtra(AlertCenter.SLOT) } ?: Slot.DECIDE

    /** The words come from this app's own alert (the page cannot be started by another app). */
    private fun read() {
        words = intent.getStringExtra(AlertCenter.WORDS)?.takeIf { it.isNotEmpty() } ?: Alerts.waitingWords(1)
        // The page ends with the ringing, so a phone in a pocket does not stay lit. The quiet entry stays in the list.
        timer.removeCallbacks(end)
        timer.postDelayed(end, AlertCenter.RING_MS)
    }

    private val timer = Handler(Looper.getMainLooper())
    private val end = Runnable { finish() }

    override fun onDestroy() {
        timer.removeCallbacks(end)
        if (showing.get() === this) showing.clear()
        super.onDestroy()
    }

    companion object {
        private const val UNLOCK_MS = 120_000L
        private var showing = WeakReference<RingActivity>(null)

        /** The alert of [slot] is gone (decided elsewhere; null: every alert, as after a lost key): its page goes too. */
        fun close(slot: Slot?) {
            val page = showing.get() ?: return
            page.runOnUiThread { if (slot == null || page.slot == slot) page.finish() }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setShowWhenLocked(true)
        setTurnScreenOn(true)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) // for the 30 seconds of ringing only: see read()
        showing = WeakReference(this)
        read()
        setContent {
            ErpTheme(Palettes.pick(phoneIsDark = isSystemInDarkTheme(), outdoor = false)) {
                BackHandler(onBack = ::later) // Back is "Later": the ringing stops, the alert stays in the list
                Box(Modifier.fillMaxSize().background(Look.Ground).safeDrawingPadding()) { RingPage(words, onOpen = ::open, onLater = ::later) }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        read() // a newer alert replaces the page
    }

    private fun later() {
        AlertCenter.stopRing(this, slot)
        finish()
    }

    private fun open() {
        AlertCenter.stopRing(this, slot)
        val keyguard = getSystemService(KeyguardManager::class.java)
        val go = {
            startActivity(AlertCenter.openApp(this, slot))
            finish()
        }
        if (keyguard.isKeyguardLocked) {
            // Unlocking the phone may take longer than the ringing: the page waits for it, but not without end.
            timer.removeCallbacks(end)
            timer.postDelayed(end, UNLOCK_MS)
            keyguard.requestDismissKeyguard(this, object : KeyguardManager.KeyguardDismissCallback() {
                override fun onDismissSucceeded() = go()
                override fun onDismissCancelled() = finish()
                override fun onDismissError() = finish()
            })
        } else {
            go()
        }
    }
}

/** The page itself, apart from the phone, so it can be drawn and measured in a test. */
@Composable
fun RingPage(words: String, onOpen: () -> Unit, onLater: () -> Unit) {
    BoxWithConstraints(Modifier.fillMaxSize().padding(horizontal = 24.dp, vertical = 20.dp), contentAlignment = Alignment.TopCenter) {
        // The buttons sit at the bottom when there is room; with large text the whole page scrolls instead.
        Column(
            Modifier.widthIn(max = 480.dp).fillMaxWidth().verticalScroll(rememberScrollState()).heightIn(min = maxHeight),
            verticalArrangement = Arrangement.SpaceBetween,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Column(Modifier.padding(top = 32.dp), verticalArrangement = Arrangement.spacedBy(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Box(Modifier.size(96.dp).background(Look.Accent, RoundedCornerShape(24.dp)), contentAlignment = Alignment.Center) {
                    Icon(painterResource(R.drawable.ic_key), contentDescription = null, modifier = Modifier.size(52.dp), tint = Look.Ground)
                }
                Eyebrow("Approvals")
                Text(words, Modifier.fillMaxWidth(), style = MaterialTheme.typography.headlineMedium, color = Look.Ink, textAlign = TextAlign.Center)
                Text("Open the app to see it. Your fingerprint comes first.", Modifier.fillMaxWidth(), style = MaterialTheme.typography.bodyLarge, color = Look.Muted, textAlign = TextAlign.Center)
            }
            Column(Modifier.padding(top = 24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                MainButton("Open", onOpen, forward = true)
                OutlineButton("Later", onLater)
            }
        }
    }
}
