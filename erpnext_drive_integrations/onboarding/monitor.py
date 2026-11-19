"""Email health alert (MD, 2026-11-08). Runs hourly on production.

Why: If ERPNext mail
stops working, every System Manager gets a bell notification (which also reaches their phone through the
existing push). At most one alert per 6 hours. Silent on the test copy, where mail is off on purpose.
"""
import frappe
from frappe.utils import add_to_date, now_datetime

WINDOW_MINUTES = 70
DEDUPE_KEY = "onboarding:mail-alert"
DEDUPE_SECONDS = 6 * 3600
MAIL_ERROR_PATTERNS = ["%[Mail]%", "%send_email%", "Unable to send%"]


def sender_problem():
    """Check noreply's saved TLS SMTP session without sending message DATA."""
    session = None
    try:
        name = frappe.db.get_value('Email Account', {'email_id': 'noreply@example.com', 'enable_outgoing': 1}, 'name')
        if not name:
            return 'The noreply SMTP sender is not enabled.'
        session = frappe.get_doc('Email Account', name).get_smtp_server().session
        if session.noop()[0] != 250:
            return 'The noreply SMTP service did not accept its health check.'
        return None
    except Exception as exc:
        return 'The noreply SMTP service does not answer: ' + type(exc).__name__
    finally:
        if session is not None:
            try:
                session.quit()
            except Exception:
                pass


def find_problems():
    since = add_to_date(now_datetime(), minutes=-WINDOW_MINUTES)
    problems = []
    cloud = sender_problem()
    if cloud:
        problems.append(cloud)
    errors = frappe.get_all("Error Log", filters={"creation": [">", since]},
                            or_filters=[["method", "like", p] for p in MAIL_ERROR_PATTERNS], pluck="method")
    if errors:
        problems.append(f"{len(errors)} email error(s) in the last hour, e.g. {errors[0][:90]}")
    failed = frappe.db.count("Email Queue", {"status": "Error", "modified": [">", since]})
    if failed:
        problems.append(f"{failed} email(s) failed to send in the last hour")
    return problems


def check_mail():
    if frappe.conf.get("onboarding_test_copy") or frappe.conf.get("cloud_test_copy"):
        return
    problems = find_problems()
    if not problems or frappe.cache.get_value(DEDUPE_KEY):
        return
    frappe.cache.set_value(DEDUPE_KEY, 1, expires_in_sec=DEDUPE_SECONDS)
    admins = frappe.get_all("Has Role", filters={"role": "System Manager", "parenttype": "User"}, pluck="parent", distinct=True)
    admins = [u for u in admins if u not in ("Administrator", "Guest") and frappe.db.get_value("User", u, "enabled")]
    body = "<br>".join(frappe.utils.escape_html(p) for p in problems)
    for user in admins:
        frappe.get_doc({"doctype": "Notification Log", "for_user": user, "type": "Alert",
                        "subject": "Email problem on erp.example.com: emails may not be going out",
                        "email_content": body + "<br><br>Checked by erpnext_drive_integrations.onboarding.monitor (hourly)."}).insert(ignore_permissions=True)
    frappe.db.commit()
