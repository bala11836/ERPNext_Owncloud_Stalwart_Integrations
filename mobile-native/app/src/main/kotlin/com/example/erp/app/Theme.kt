package com.example.erp.app

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * Sunlight-first look: white ground, near-black text (contrast above 7:1), one deep blue accent, large type.
 * Status is always an icon or a word plus colour, never colour alone (see [Status]).
 */
object Look {
    val Ink = Color(0xFF111827)
    val Muted = Color(0xFF374151)
    val Accent = Color(0xFF0B4F9E)
    val Ok = Color(0xFF116B35)
    val Warn = Color(0xFF8A4B00)
    val Bad = Color(0xFFA61B1B)
    val Line = Color(0xFF9CA3AF)
    val Soft = Color(0xFFE8F0FA)

    /** Touch targets are at least this tall (gloves, one hand). */
    val Touch = 56.dp
    val Gap = 16.dp
}

private val Colors = lightColorScheme(
    primary = Look.Accent,
    onPrimary = Color.White,
    secondaryContainer = Look.Soft,
    onSecondaryContainer = Look.Ink,
    background = Color.White,
    onBackground = Look.Ink,
    surface = Color.White,
    onSurface = Look.Ink,
    surfaceVariant = Color(0xFFF1F4F8),
    onSurfaceVariant = Look.Muted,
    outline = Look.Line,
    error = Look.Bad,
    onError = Color.White,
)

private val Type = Typography(
    headlineMedium = TextStyle(fontSize = 28.sp, lineHeight = 34.sp, fontWeight = FontWeight.Bold),
    titleMedium = TextStyle(fontSize = 19.sp, lineHeight = 26.sp, fontWeight = FontWeight.SemiBold),
    bodyLarge = TextStyle(fontSize = 17.sp, lineHeight = 25.sp),
    bodyMedium = TextStyle(fontSize = 15.sp, lineHeight = 22.sp),
    labelLarge = TextStyle(fontSize = 18.sp, lineHeight = 24.sp, fontWeight = FontWeight.SemiBold),
    labelMedium = TextStyle(fontSize = 15.sp, lineHeight = 20.sp, fontWeight = FontWeight.SemiBold),
)

@Composable
fun ErpTheme(content: @Composable () -> Unit) = MaterialTheme(colorScheme = Colors, typography = Type, content = content)
