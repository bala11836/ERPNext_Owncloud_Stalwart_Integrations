package com.example.erp.app

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

/** The shared building blocks. Screens are made only from these, so every screen keeps the same rules. */

enum class StatusKind(val mark: String, val word: String, val color: Color) {
    OK("✓", "OK", Look.Ok),
    WARN("!", "Check", Look.Warn),
    BAD("✕", "Failed", Look.Bad),
    NONE("–", "Not reached", Look.Muted),
}

/**
 * A plain status line: a mark, the text, and colour. It is never tappable, so its text must never name an
 * action ("open", "tap", "see"). A message that needs the person to act is an [ActionMessage].
 */
@Composable
fun Status(kind: StatusKind, text: String, modifier: Modifier = Modifier) {
    Row(modifier, horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.Top) {
        Text(kind.mark, color = kind.color, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyLarge)
        Text(text, color = kind.color, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.bodyLarge)
    }
}

/**
 * A message the person must act on. It cannot be built without the action: [onAct] is required, so a message
 * that says "open" always opens something (the "no dead ends" rule).
 */
@Composable
fun ActionMessage(kind: StatusKind, text: String, actionLabel: String, onAct: () -> Unit, modifier: Modifier = Modifier) {
    Panel(modifier) {
        Status(kind, text)
        MainButton(actionLabel, onAct)
    }
}

@Composable
fun Panel(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Surface(modifier.fillMaxWidth(), shape = RoundedCornerShape(14.dp), border = BorderStroke(2.dp, Look.Line), color = Color.White) {
        Column(Modifier.padding(Look.Gap), verticalArrangement = Arrangement.spacedBy(10.dp)) { content() }
    }
}

@Composable
fun MainButton(label: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Button(onClick, modifier.fillMaxWidth().heightIn(min = Look.Touch), shape = RoundedCornerShape(14.dp)) {
        Text(label, style = MaterialTheme.typography.labelLarge)
    }
}
