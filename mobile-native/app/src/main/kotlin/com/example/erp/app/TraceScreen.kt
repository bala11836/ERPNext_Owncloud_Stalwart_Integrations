package com.example.erp.app

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import com.example.erp.core.Point
import com.example.erp.core.Trace

/**
 * Data trace (test builds): the last actions, and for each one the eight points its data passes, green or red,
 * with the reason at the point that failed. Phone: list, then detail. Tablet (wide): list and detail side by side.
 */
@Composable
fun TraceScreen(traces: List<Trace>, showValues: Boolean, onAddSample: (() -> Unit)?) {
    var openId by rememberSaveable { mutableStateOf<String?>(null) }
    val open = traces.firstOrNull { it.id == openId }
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val wide = maxWidth >= 840.dp
        if (wide) {
            Row(Modifier.fillMaxSize().padding(Look.Gap), horizontalArrangement = Arrangement.spacedBy(Look.Gap)) {
                TraceList(traces, open?.id, onAddSample, Modifier.weight(1f)) { openId = it }
                Column(Modifier.weight(1.4f)) {
                    if (open != null) TraceDetail(open, showValues, onBack = null)
                    else Text("Choose an action on the left.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                }
            }
        } else if (open != null) {
            Column(Modifier.fillMaxSize().padding(Look.Gap)) { TraceDetail(open, showValues, onBack = { openId = null }) }
        } else {
            TraceList(traces, null, onAddSample, Modifier.fillMaxSize().padding(Look.Gap)) { openId = it }
        }
    }
}

@Composable
private fun TraceList(traces: List<Trace>, selected: String?, onAddSample: (() -> Unit)?, modifier: Modifier, onOpen: (String) -> Unit) {
    Column(modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Data trace", style = MaterialTheme.typography.headlineMedium)
        if (traces.isEmpty()) {
            Text("No actions yet. Each save you make in the app appears here with the points its data passed.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
        }
        for (trace in traces) {
            val fault = trace.fault
            Surface(
                Modifier.fillMaxWidth().heightIn(min = Look.Touch).clickable { onOpen(trace.id) },
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(2.dp, if (trace.id == selected) Look.Accent else Look.Line),
                color = if (trace.id == selected) Look.Soft else Color.White,
            ) {
                Column(Modifier.padding(Look.Gap), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(trace.action, style = MaterialTheme.typography.titleMedium)
                    when {
                        fault != null -> Status(StatusKind.BAD, "Failed at ${fault.point.ordinal + 1}. ${fault.point.label}")
                        trace.complete -> Status(StatusKind.OK, "Saved and read back the same")
                        else -> Status(StatusKind.NONE, "In progress")
                    }
                }
            }
        }
        if (onAddSample != null) MainButton("Add a sample trace (test builds)", onAddSample)
    }
}

@Composable
private fun TraceDetail(trace: Trace, showValues: Boolean, onBack: (() -> Unit)?) {
    val clipboard = LocalClipboardManager.current
    Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(trace.action, style = MaterialTheme.typography.headlineMedium)
        Panel {
            for (point in Point.entries) {
                val mark = trace.marks.lastOrNull { it.point == point }
                val kind = when {
                    mark == null -> StatusKind.NONE
                    mark.ok -> StatusKind.OK
                    else -> StatusKind.BAD
                }
                val took = mark?.tookMs?.let { " · $it ms" }.orEmpty()
                Status(kind, "${point.ordinal + 1}. ${point.label}: ${kind.word}$took")
                if (mark != null && mark.note.isNotEmpty()) Text(mark.note, style = MaterialTheme.typography.bodyMedium)
                if (mark != null && !mark.ok) Text("Usually means: ${point.faultMeans}.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
                if (showValues && mark?.detail != null) Text(mark.detail!!, style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
            }
        }
        MainButton("Copy this trace", { clipboard.setText(AnnotatedString(trace.report(withValues = showValues))) })
        if (onBack != null) MainButton("Back to the list", onBack)
    }
}
