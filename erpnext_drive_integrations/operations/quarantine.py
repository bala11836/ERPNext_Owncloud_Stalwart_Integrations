"""Disable outbound side effects on a restored TEST database before web startup.

Bench-only operation; never whitelisted. Native worker containers must remain
stopped until this and the private test bootstrap have both succeeded.
"""
import os
import frappe


def apply():
    if os.environ.get('CLOUD_DEPLOYMENT_TIER')!='test' or frappe.conf.get('cloud_test_copy') is not True:
        raise RuntimeError('Quarantine is restricted to an explicitly marked test runtime')
    changed={}
    for doctype,settings in {
        'Email Account':{'enable_incoming':0,'enable_outgoing':0,'default_incoming':0,'default_outgoing':0},
        'Webhook':{'enabled':0},'Notification':{'enabled':0},
        'Auto Email Report':{'enabled':0},'Scheduled Job Type':{'stopped':1},
    }.items():
        if not frappe.db.exists('DocType',doctype):continue
        fields={field:value for field,value in settings.items() if frappe.get_meta(doctype).has_field(field)}
        if fields:
            names=frappe.get_all(doctype,pluck='name')
            for name in names:frappe.db.set_value(doctype,name,fields,update_modified=False)
            changed[doctype]=len(names)
    # API keys and browser/native session credentials must not become valid on
    # a different host just because its business database was restored.
    if frappe.get_meta('User').has_field('api_key'):
        frappe.db.sql('UPDATE `tabUser` SET api_key=NULL')
    for doctype in ['OAuth Bearer Token','OAuth Authorization Code']:
        if frappe.db.exists('DocType',doctype):frappe.db.delete(doctype)
    frappe.db.sql('DELETE FROM `tabSessions`')
    frappe.db.sql('DELETE FROM `__Auth`')
    if frappe.db.exists('DocType','Email Queue'):
        frappe.db.sql("UPDATE `tabEmail Queue` SET status='Error' WHERE status IN ('Not Sent','Sending','Partially Sent')")
    frappe.db.set_single_value('System Settings','enable_scheduler',0)
    frappe.db.commit()
    return {'quarantined':True,'outbound_definitions_disabled':changed}
