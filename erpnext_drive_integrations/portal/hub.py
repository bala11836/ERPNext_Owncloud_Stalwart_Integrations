"""Small authenticated context for the notification enrollment client."""
import frappe

@frappe.whitelist()
def context():
    if frappe.session.user == "Guest":
        raise frappe.PermissionError("Sign in required")
    from frappe.sessions import get_csrf_token
    return {"user": frappe.session.user,
            "name": frappe.get_cached_value("User", frappe.session.user, "full_name"),
            "company": frappe.defaults.get_user_default("Company") or "",
            "csrf": get_csrf_token()}
