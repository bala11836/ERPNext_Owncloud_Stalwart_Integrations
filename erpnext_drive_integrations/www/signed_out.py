import frappe
from erpnext_drive_integrations.portal.sso import FINISH, redirect
no_cache = 1
def get_context(context):
    if frappe.session.user != 'Guest':
        redirect(FINISH)
    context.signin_url = '/api/method/erpnext_drive_integrations.portal.sso.start_signin'
    return context
