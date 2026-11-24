package expo.modules.approvalalert

import android.app.Activity
import android.app.KeyguardManager
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.util.TypedValue
import android.view.Gravity
import android.view.ViewGroup.LayoutParams.MATCH_PARENT
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.view.WindowManager
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView

/**
 * The full page over the locked screen (the visitor-call look): the app icon, the area, the kind, the count and
 * the site, and two big buttons. Later stops the ringing. Review asks the phone to unlock, then opens the app,
 * whose own lock (Face ID, fingerprint or passcode) comes before any detail. Nothing can be approved here.
 */
class AlertActivity : Activity() {
  private val area get() = intent.getStringExtra(Alerts.AREA) ?: "other"

  @Suppress("DEPRECATION")
  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
      setShowWhenLocked(true)
      setTurnScreenOn(true)
    } else {
      window.addFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON)
    }
    window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
    setContentView(page())
  }

  override fun onNewIntent(intent: android.content.Intent) {
    super.onNewIntent(intent)
    setIntent(intent)
    setContentView(page()) // a newer alert of the same kind replaces the page
  }

  private fun dp(v: Int) = TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v.toFloat(), resources.displayMetrics).toInt()

  private fun text(value: String?, size: Float, bold: Boolean, alpha: Int = 255) = TextView(this).apply {
    this.text = value ?: ""
    setTextColor(Color.argb(alpha, 255, 255, 255))
    setTextSize(TypedValue.COMPLEX_UNIT_SP, size)
    if (bold) typeface = Typeface.DEFAULT_BOLD
    gravity = Gravity.CENTER
    setPadding(0, dp(6), 0, dp(6))
  }

  private fun button(label: String, filled: Boolean, onTap: () -> Unit) = Button(this).apply {
    text = label
    isAllCaps = false
    setTextSize(TypedValue.COMPLEX_UNIT_SP, 20f)
    typeface = Typeface.DEFAULT_BOLD
    setTextColor(if (filled) NAVY else Color.WHITE)
    background = GradientDrawable().apply {
      cornerRadius = dp(14).toFloat()
      setColor(if (filled) Color.WHITE else Color.TRANSPARENT)
      setStroke(dp(2), Color.WHITE)
    }
    minHeight = dp(64)
    setOnClickListener { onTap() }
    layoutParams = LinearLayout.LayoutParams(0, dp(64), 1f).apply { setMargins(dp(8), 0, dp(8), 0) }
  }

  private fun page() = LinearLayout(this).apply {
    orientation = LinearLayout.VERTICAL
    gravity = Gravity.CENTER
    setBackgroundColor(NAVY)
    setPadding(dp(28), dp(48), dp(28), dp(48))
    layoutParams = LinearLayout.LayoutParams(MATCH_PARENT, MATCH_PARENT)
    addView(
      ImageView(context).apply {
        setImageDrawable(packageManager.getApplicationIcon(packageName))
        importantForAccessibility = ImageView.IMPORTANT_FOR_ACCESSIBILITY_NO
      },
      LinearLayout.LayoutParams(dp(96), dp(96)).apply { bottomMargin = dp(24) },
    )
    addView(text(intent.getStringExtra(Alerts.AREA_LABEL)?.uppercase(), 18f, true, 220))
    addView(text(intent.getStringExtra(Alerts.TITLE), 30f, true))
    addView(text(intent.getStringExtra(Alerts.BODY), 22f, false, 235))
    addView(LinearLayout(context), LinearLayout.LayoutParams(MATCH_PARENT, 0, 1f))
    addView(
      LinearLayout(context).apply {
        orientation = LinearLayout.HORIZONTAL
        addView(button(intent.getStringExtra(Alerts.LATER) ?: "Later", false) { later() })
        addView(button(intent.getStringExtra(Alerts.REVIEW) ?: "Review", true) { review() })
      },
      LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT),
    )
  }

  private fun later() {
    Alerts.stopRing(this, area)
    finish()
  }

  private fun review() {
    Alerts.stopRing(this, area)
    val keyguard = getSystemService(Context.KEYGUARD_SERVICE) as KeyguardManager
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && keyguard.isKeyguardLocked) {
      keyguard.requestDismissKeyguard(
        this,
        object : KeyguardManager.KeyguardDismissCallback() {
          override fun onDismissSucceeded() = open()
        },
      )
    } else {
      open()
    }
  }

  private fun open() {
    Alerts.clear(this, area)
    startActivity(Alerts.openIntent(this, intent.getStringExtra(Alerts.URL)))
    finish()
  }

  /** Back is Later: the ringing stops, the list entry stays. */
  @Deprecated("Back is Later")
  override fun onBackPressed() = later()

  companion object {
    private val NAVY = Color.rgb(0x0A, 0x3D, 0x91) // the app's primary; white on it is 10:1
  }
}
