"""Install / migrate setup for erpnext_drive_integrations.onboarding. Safe to run again (every migrate re-applies it)."""
import frappe

COORDINATOR = "Project Coordinator"


def ensure_roles():
    """Before migrate: pages refer to this role, so it must exist first."""
    if not frappe.db.exists("Role", COORDINATOR):
        frappe.get_doc({"doctype": "Role", "role_name": COORDINATOR, "desk_access": 1}).insert(ignore_permissions=True)


def coordinator_permissions():
    """MD decision: Projects Manager and Project Coordinator may change task dates.

    ERPNext's defaults give Projects Manager no Task access at all, so both roles get Task read + write;
    Project Coordinator also gets Project read (Projects Manager already has it).
    """
    from frappe.permissions import add_permission, update_permission_property

    grants = ((COORDINATOR, "Project", ("read",)), (COORDINATOR, "Task", ("read", "write")),
              ("Projects Manager", "Task", ("read", "write")))
    for role, doctype, rights in grants:
        if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
            add_permission(doctype, role, 0)  # copies the standard rules first, then adds this role
        for right in rights:
            update_permission_property(doctype, role, 0, right, 1)


def baseline_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({"Task": [
        dict(fieldname="hov_baseline_section", label="Baseline (original plan)", fieldtype="Section Break",
             insert_after="exp_end_date", collapsible=1),
        dict(fieldname="hov_baseline_start", label="Baseline Start", fieldtype="Datetime", read_only=1, no_copy=1,
             insert_after="hov_baseline_section"),
        dict(fieldname="hov_baseline_end", label="Baseline End", fieldtype="Datetime", read_only=1, no_copy=1,
             insert_after="hov_baseline_start"),
    ]}, update=True)


def projects_navigation():
    from frappe.desk.doctype.custom_sidebar.custom_sidebar import add_site_sidebar_item

    add_site_sidebar_item("Projects", {"type": "Link", "label": "Construction Schedule", "link_type": "Page",
                                       "link_to": "construction-schedule", "icon": "calendar", "child": 0})


def buying_navigation():
    """Vendor Onboarding + KYC Amendment in the Buying menu (audit follow-up, 2026-11-11). The role rule
    (access.py) still hides each link from people whose roles can't open it."""
    from frappe.desk.doctype.custom_sidebar.custom_sidebar import add_site_sidebar_item

    for label, doctype, icon in (("Vendor Onboarding", "Vendor Onboarding", "users"),
                                 ("KYC Amendment", "KYC Amendment", "edit")):
        add_site_sidebar_item("Buying", {"type": "Link", "label": label, "link_type": "DocType",
                                         "link_to": doctype, "icon": icon, "child": 0})


def vendor_kyc_fields():
    """ADR-039: KYC facts kept on ERPNext's own Supplier / Contact (filled only by onboarding / amendment)."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    ro = dict(read_only=1, no_copy=1)
    create_custom_fields({
        "Supplier": [
            dict(fieldname="hov_kyc_section", label="Vendor KYC", fieldtype="Section Break", insert_after="pan", collapsible=1),
            dict(fieldname="hov_constitution", label="Constitution", fieldtype="Data", insert_after="hov_kyc_section", **ro),
            dict(fieldname="hov_cin", label="CIN", fieldtype="Data", insert_after="hov_constitution", **ro),
            dict(fieldname="hov_udyam", label="Udyam (MSME) number", fieldtype="Data", insert_after="hov_cin", **ro),
            dict(fieldname="hov_kyc_col", fieldtype="Column Break", insert_after="hov_udyam"),
            dict(fieldname="hov_gst_status", label="GST status at onboarding", fieldtype="Data", insert_after="hov_kyc_col", **ro),
            dict(fieldname="hov_vendor_onboarding", label="Vendor onboarding", fieldtype="Link", options="Vendor Onboarding",
                 insert_after="hov_gst_status", **ro),
        ],
        "Contact": [
            dict(fieldname="hov_kyc_section", label="Verification", fieldtype="Section Break", insert_after="designation", collapsible=1),
            dict(fieldname="hov_email_verified_on", label="Email verified on", fieldtype="Datetime", insert_after="hov_kyc_section", **ro),
            dict(fieldname="hov_whatsapp_verified_on", label="WhatsApp verified on", fieldtype="Datetime",
                 insert_after="hov_email_verified_on", **ro),
            dict(fieldname="hov_kyc_col", fieldtype="Column Break", insert_after="hov_whatsapp_verified_on"),
            dict(fieldname="hov_whatsapp_opt_in", label="WhatsApp consent", fieldtype="Check", insert_after="hov_kyc_col", **ro),
            dict(fieldname="hov_opt_in_on", label="Consent given on", fieldtype="Datetime", insert_after="hov_whatsapp_opt_in", **ro),
            dict(fieldname="hov_is_director", label="Director check (MCA)", fieldtype="Data", insert_after="hov_opt_in_on", **ro),
        ],
    }, update=True)


def after_migrate():
    ensure_roles()
    coordinator_permissions()
    baseline_fields()
    projects_navigation()
    vendor_kyc_fields()
    buying_navigation()
    frappe.clear_cache()
