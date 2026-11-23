import frappe
from frappe import _

MANAGER = 'Field Attendance Manager'
SUPERVISOR = 'Field Supervisor'
APPROVER = 'Field Attendance Approver'
VERIFIER = 'Field Attendance Verifier'


def is_manager(user=None):
    user = user or frappe.session.user
    return user == 'Administrator' or bool({MANAGER, 'System Manager'} & set(frappe.get_roles(user)))


def require_user():
    user = frappe.session.user
    if user == 'Guest' or not frappe.db.get_value('User', user, 'enabled'):
        frappe.throw(_('Please sign in again.'), frappe.AuthenticationError)
    return user


def site_ids(user=None, role=None):
    user = user or require_user()
    if is_manager(user):
        return frappe.get_all('Field Site', filters={'enabled': 1}, pluck='name')
    roles = set(frappe.get_roles(user))
    permitted = []
    if SUPERVISOR in roles and role in (None, 'Supervisor'):
        permitted.append('Supervisor')
    if APPROVER in roles and role in (None, 'Approver'):
        permitted.append('Approver')
    if VERIFIER in roles and role in (None, 'Verifier'):
        permitted.append('Verifier')
    if not permitted:
        return []
    return frappe.db.sql('''SELECT DISTINCT m.parent FROM `tabField Site Member` m
        JOIN `tabField Site` s ON s.name=m.parent
        WHERE m.user=%s AND m.enabled=1 AND m.team_role IN %s AND s.enabled=1''',
        (user, permitted), pluck=True)


def site_access(site, role=None, user=None):
    return site in site_ids(user, role)


def require_site(site, role=None):
    user = require_user()
    if not site_access(site, role, user):
        frappe.throw(_('You do not have access to this site.'), frappe.PermissionError)
    return frappe.get_doc('Field Site', site)


def eligible_supervisor(site, user):
    return bool(user and frappe.db.get_value('User', user, 'enabled') and
                SUPERVISOR in frappe.get_roles(user) and frappe.db.exists('Field Site Member', {
                    'parent': site, 'parenttype': 'Field Site', 'user': user,
                    'team_role': 'Supervisor', 'enabled': 1}))


def has_membership(site, user, member_role, user_role):
    return (bool(user) and user_role in frappe.get_roles(user)
            and bool(frappe.db.get_value('User', user, 'enabled'))
            and bool(frappe.db.get_value('Field Site', site, 'enabled'))
            and bool(frappe.db.exists('Field Site Member', {
                'parent': site, 'parenttype': 'Field Site', 'team_role': member_role,
                'enabled': 1, 'user': user,
            })))


def approval_access(doc, user):
    if doc.state == 'Verified' or doc.verification_required:
        return has_membership(doc.site, user, 'Approver', APPROVER)
    return site_access(doc.site, 'Approver', user)


def verifier_for(site, supervisor):
    return frappe.db.get_value('Field Site Member', {
        'parent': site, 'parenttype': 'Field Site', 'team_role': 'Supervisor',
        'enabled': 1, 'user': supervisor,
    }, 'verifier')


def supervised_users(site, verifier):
    if not has_membership(site, verifier, 'Verifier', VERIFIER):
        return []
    return frappe.get_all('Field Site Member', filters={
        'parent': site, 'parenttype': 'Field Site', 'team_role': 'Supervisor',
        'enabled': 1, 'verifier': verifier,
    }, pluck='user')


def can_verify(doc, user):
    return (doc.get('entry_type') != 'Self' and doc.captured_by != user
            and doc.responsible_supervisor in supervised_users(doc.site, user)
            and frappe.db.get_value('Employee', doc.employee, 'user_id') != user)


def require_manager():
    require_user()
    if not is_manager():
        frappe.throw(_('Only a Field Attendance Manager can configure this module.'), frappe.PermissionError)


def entry_access(doc, user=None):
    user = user or frappe.session.user
    if user == 'Guest':
        return False
    if is_manager(user):
        return True
    if doc.captured_by == user and site_access(doc.site, 'Supervisor', user):
        return True
    if doc.captured_by == user and site_access(doc.site, 'Verifier', user):
        return True
    if doc.state != 'Draft' and doc.responsible_supervisor in supervised_users(doc.site, user):
        return True
    if doc.get('entry_type') == 'Self' and doc.captured_by == user:
        return True
    return doc.state != 'Draft' and site_access(doc.site, 'Approver', user)


def self_sites(user=None):
    """Sites where the user may check in themselves: any enabled membership (Staff, Supervisor or Approver)."""
    user = user or require_user()
    return frappe.db.sql('''SELECT DISTINCT m.parent FROM `tabField Site Member` m
        JOIN `tabField Site` s ON s.name=m.parent
        WHERE m.user=%s AND m.enabled=1 AND s.enabled=1''', (user,), pluck=True)
