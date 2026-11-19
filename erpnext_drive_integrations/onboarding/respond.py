"""Outside responses (ADR-039): send a form or document to someone outside the company and record the answer.

Outsiders never log in. They get a private link (email, or shared by hand by staff).

Security model (MD 2026-11-09, method A "first device wins"):
- A link key is 32 random bytes. Only its SHA-256 is stored, so a database copy can't open any link.
- The first device that opens the link (after tapping "Open") gets an HttpOnly cookie. After that the link
  works only on that device. Other devices are refused and logged, and staff are alerted.
- The first answer closes the request; all its other links (other channels) go stale.
- Every guest method is key-bound, rate-limited and touches only that one request's own document.
  Staff methods check roles from the Response Rule plus ERPNext's own permissions.
"""
import hashlib
import re
import secrets

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, escape_html, format_datetime, get_datetime, now_datetime

DOCTYPE = "Response Request"
DEFAULT_VALID_DAYS = 7  # used only when the admin has not set link_valid_days on the Response Rule
REFUSED = "This link is not valid or has expired. Please contact Example Organization Constructions."
OTHER_DEVICE = ("This link was already opened on another phone or computer, so it is locked to that device. "
                "If that was not you, please call Example Organization Constructions.")
# purpose -> module that knows the form: form_spec(req) and on_answer(req, channel, decision, reason)
HANDLERS = {"Vendor Onboarding": "erpnext_drive_integrations.onboarding.vendor", "Email verification": "erpnext_drive_integrations.onboarding.vendor",
            "KYC Amendment": "erpnext_drive_integrations.onboarding.amendment", "Document response": "erpnext_drive_integrations.onboarding.respond"}


# ---------- the public host gate (before_request hook) ----------
# The public respond host (site_config hov_respond_host) may reach ONLY these. Second layer behind the
# narrow Traefik route. It is needed because Frappe runs any guest method given as `cmd=` on ANY path, even
# in a POST body the proxy can't see. (Password login is off: System Settings disable_user_pass_login = 1.)
RESPOND_PAGE = re.compile(r"^/(o|r|v)/[A-Za-z0-9_-]{20,100}$")
GUEST_METHODS = frozenset({
    "erpnext_drive_integrations.onboarding.respond.open_link", "erpnext_drive_integrations.onboarding.respond.answer", "erpnext_drive_integrations.onboarding.respond.document_pdf",
    "erpnext_drive_integrations.onboarding.vendor.save", "erpnext_drive_integrations.onboarding.vendor.lookup_gstin", "erpnext_drive_integrations.onboarding.vendor.lookup_ifsc",
    "erpnext_drive_integrations.onboarding.vendor.upload", "erpnext_drive_integrations.onboarding.vendor.submit", "erpnext_drive_integrations.onboarding.amendment.submit_form",
})
STATIC_PATHS = frozenset({"/website_script.js", "/favicon.ico", "/link-help",
                          "/apple-touch-icon.png", "/apple-touch-icon-precomposed.png"})


def allowed_on_respond_host(method, path, form_keys, header_names):
    """Pure rule (unit-tested): may this request pass on the public respond host?"""
    # (X-Frappe-Site-Name is added by our own frontend nginx, so it is not refused.)
    if "cmd" in form_keys or any(h.lower().startswith(("x-authentik", "authorization")) for h in header_names):
        return False
    if path.startswith("/api/method/"):
        return path[len("/api/method/"):] in GUEST_METHODS and method in ("GET", "POST")
    if method not in ("GET", "HEAD"):
        return False
    return bool(RESPOND_PAGE.match(path)) or path.startswith("/assets/") or path in STATIC_PATHS


def gate():
    host = (frappe.conf.get("hov_respond_host") or "").lower()
    request = getattr(frappe.local, "request", None)
    if not host or request is None or (request.host or "").split(":")[0].lower() != host:
        return
    path = request.path
    prefix = "/api/method/"
    if path.startswith(prefix):
        aliases = frappe.conf.get("cloud_legacy_rpc_aliases") or {}
        path = prefix + aliases.get(path[len(prefix):], path[len(prefix):])
    if not allowed_on_respond_host(request.method, path, set(frappe.form_dict or {}), list(request.headers.keys())):
        frappe.throw(_("Not found"), frappe.PageDoesNotExistError)


# ---------- pure helpers (unit-tested) ----------

def new_key():
    return secrets.token_urlsafe(32)


def key_hash(key):
    return hashlib.sha256(str(key or "").encode()).hexdigest()


def device_state(stored_hash, cookie_value):
    """'first' = nobody opened it yet, 'same' = this device holds the lock, 'other' = another device does."""
    if not stored_hash:
        return "first"
    if cookie_value and secrets.compare_digest(stored_hash, key_hash(cookie_value)):
        return "same"
    return "other"


def is_expired(expires_on, now):
    return bool(expires_on) and get_datetime(expires_on) < now


# ---------- internal writes (Response Requests are never edited by people) ----------

def system_save(doc, insert=False):
    """Save a record that people may not change directly (Response Request, locked onboarding fields)."""
    frappe.flags.hov_system_write = True
    try:
        doc.flags.ignore_permissions = True
        doc.insert() if insert else doc.save()
    finally:
        frappe.flags.hov_system_write = False
    return doc


def event_row(event, channel="", detail=""):
    return {"at": now_datetime(), "event": event, "channel": channel or "",
            "ip": getattr(frappe.local, "request_ip", None) or "",
            "device": (frappe.get_request_header("User-Agent") or "")[:140] if getattr(frappe.local, "request", None) else "",
            "detail": str(detail or "")[:500]}


def log(req, event, channel="", detail=""):
    req.append("events", event_row(event, channel, detail))
    system_save(req)


def base_url():
    return (frappe.conf.get("hov_respond_url") or frappe.utils.get_url()).rstrip("/")


# ---------- rules (admin) ----------

def get_rule(doctype):
    name = frappe.db.get_value("Response Rule", {"document_type": doctype, "enabled": 1})
    return frappe.get_cached_doc("Response Rule", name) if name else None


def check_role(doctype, field, fallback=("System Manager",)):
    """Allow if the user has one of the rule's roles. No roles set -> fallback roles (None = no extra check)."""
    rule = get_rule(doctype)
    allowed = {r.role for r in (rule.get(field) or [])} if rule else set()
    if not allowed:
        if fallback is None:
            return rule
        allowed = set(fallback)
    if not allowed & set(frappe.get_roles()):
        frappe.throw(_("Your role may not do this (allowed: {0}).").format(", ".join(sorted(allowed))), frappe.PermissionError)
    return rule


def check_different_approver(doctype, doc):
    rule = get_rule(doctype)
    if (rule.different_approver if rule else 1) and doc.owner == frappe.session.user:
        frappe.throw(_("This must be approved by a different person than the one who created it."), frappe.PermissionError)


# ---------- creating and sending requests ----------

def create_request(reference_doctype, reference_name, purpose, *, recipient_name, email=None, mobile=None,
                   channels=("Email", "Manual"), path="o", target=None, rule_doctype=None):
    rule = get_rule(rule_doctype or reference_doctype)
    days = (rule.link_valid_days if rule else 0) or DEFAULT_VALID_DAYS
    keys = {ch: new_key() for ch in channels}
    req = frappe.get_doc({
        "doctype": DOCTYPE, "reference_doctype": reference_doctype, "reference_name": reference_name,
        "purpose": purpose, "status": "Sent", "recipient_name": recipient_name, "recipient_email": email,
        "recipient_mobile": mobile, "target": target, "expires_on": add_days(now_datetime(), days),
        "keys": [{"channel": ch, "key_hash": key_hash(k)} for ch, k in keys.items()],
        "events": [event_row("Created", ", ".join(channels), f"by {frappe.session.user}")],
    })
    system_save(req, insert=True)
    return req, {ch: f"{base_url()}/{path}/{k}" for ch, k in keys.items()}


def is_test_copy():
    """True on a test copy. The test runtime sets `cloud_test_copy`; the older
    `onboarding_test_copy` key is still honoured."""
    return bool(frappe.conf.get("cloud_test_copy") or frappe.conf.get("onboarding_test_copy"))


def send_email(req, url, subject, intro):
    expires = format_datetime(req.expires_on, "dd MMM yyyy")
    message = (f"<p>Dear {escape_html(req.recipient_name or 'Sir / Madam')},</p><p>{intro}</p>"
               f'<p><a href="{url}" style="font-size:18px;font-weight:bold">Open</a></p>'
               f"<p>This link works on <b>one device only</b> (the first one you open it on) until {expires}. "
               "Please do not forward it.</p><p>Example Organization Constructions</p>")
    if is_test_copy():
        smtp = frappe.conf.get("cloud_test_form_smtp")
        if not smtp:
            # Test copies mute email; give the link to the sender's bell instead.
            notify(req.owner, f"TEST COPY: email to {req.recipient_email[:1]}*** not sent. Link: {url}", DOCTYPE, req.name)
            log(req, "Email skipped (test copy): link given to the sender", "Email")
            return
        # Owner-approved test sending (P38): forms only, through a dedicated
        # account, never Frappe's muted queue or the production accounts.
        send_test_form_email(smtp, req.recipient_email, "[TEST] " + subject,
                             '<p style="color:#b00020"><b>TEST SYSTEM</b>: this message comes from a test copy. '
                             "Answers are not kept and do not reach the live system.</p>" + message)
        log(req, "Email sent from the test copy ([TEST])", "Email", req.recipient_email)
        return
    frappe.sendmail(sender='noreply@example.com', recipients=[req.recipient_email], subject=subject, message=message,
                    reference_doctype=req.reference_doctype, reference_name=req.reference_name)
    log(req, "Email sent", "Email", req.recipient_email)


def send_test_form_email(smtp, recipient, subject, html):
    """Send one form email over implicit TLS with a dedicated test account."""
    import smtplib
    import socket
    import ssl
    from email.message import EmailMessage
    for key in ("host", "user", "password", "sender"):
        if not smtp.get(key):
            frappe.throw(_("Test form email is not configured ({0} missing)").format(key))
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = smtp["sender"], recipient, subject
    msg.set_content("TEST SYSTEM message. Open it in an email app that shows HTML to see the form link.")
    msg.add_alternative(html, subtype="html")
    context = ssl.create_default_context()
    hostname, address = smtp["host"], smtp.get("address") or smtp["host"]

    class VerifiedSMTP(smtplib.SMTP_SSL):
        # Connect to `address` (e.g. a tailnet IP) but verify the certificate
        # for the SMTP hostname; certificate checks are never disabled.
        def _get_socket(self, host, port, timeout):
            raw = socket.create_connection((address, port), timeout)
            return context.wrap_socket(raw, server_hostname=hostname)

    with VerifiedSMTP(hostname, int(smtp.get("port") or 465), context=context, timeout=20) as server:
        server.login(smtp["user"], smtp["password"])
        server.send_message(msg)


def notify(user, subject, doctype, name):
    """Bell (and phone push) for staff. Rule 6: the subject carries no names, amounts or personal data."""
    if not user or user in ("Administrator", "Guest"):
        return
    frappe.get_doc({"doctype": "Notification Log", "for_user": user, "type": "Alert", "subject": subject,
                    "document_type": doctype, "document_name": name}).insert(ignore_permissions=True)


# ---------- guarding every guest call ----------

def _key_row(key):
    if not key or len(str(key)) > 100:
        return None
    return frappe.db.get_value("Response Request Key", {"key_hash": key_hash(key), "parenttype": DOCTYPE},
                               ["parent", "channel", "stale"], as_dict=True)


def guard(key, opening=False):
    """Return (request, channel) for a valid, open link on the device that holds the lock, else refuse."""
    row = _key_row(key)
    if not row:
        frappe.throw(REFUSED, frappe.PermissionError)
    req = frappe.get_doc(DOCTYPE, row.parent)
    if row.stale or req.status != "Sent":
        frappe.throw(REFUSED if req.status != "Answered" else "This was already answered. Thank you.", frappe.PermissionError)
    if is_expired(req.expires_on, now_datetime()):
        req.status = "Expired"
        log(req, "Expired (link used after expiry)", row.channel)
        frappe.db.commit()
        frappe.throw(REFUSED, frappe.PermissionError)
    cookie = f"hov_{req.name}"
    state = device_state(req.device_hash, frappe.request.cookies.get(cookie) if frappe.request else None)
    if state == "other":
        log(req, "Refused: opened on another device", row.channel)
        if not frappe.cache.get_value(f"hov:other-device:{req.name}"):
            frappe.cache.set_value(f"hov:other-device:{req.name}", 1, expires_in_sec=3600)
            notify(req.owner, f"A link for {req.name} was opened on a second device (refused)", DOCTYPE, req.name)
        frappe.db.commit()
        frappe.throw(OTHER_DEVICE, frappe.PermissionError)
    if state == "first":
        if not opening:
            frappe.throw(_("Please open the link first."), frappe.PermissionError)
        token = secrets.token_urlsafe(24)
        req.device_hash = key_hash(token)
        log(req, "Opened (locked to this device)", row.channel)
        frappe.local.cookie_manager.set_cookie(cookie, token, expires=get_datetime(req.expires_on),
                                               secure=True, httponly=True, samesite="Lax")
    return req, row.channel


def finish(req, answer, channel, detail=""):
    """First answer wins: lock the row, refuse if someone answered meanwhile, stale every key."""
    if frappe.db.get_value(DOCTYPE, req.name, "status", for_update=True) != "Sent":
        frappe.throw("This was already answered. Thank you.", frappe.PermissionError)
    req.reload()
    req.status, req.answer, req.answered_on, req.answered_via = "Answered", answer, now_datetime(), channel
    for k in req.keys:
        k.stale = 1
    log(req, f"Answered: {answer}", channel, detail)


def handler(req):
    return frappe.get_module(HANDLERS[req.purpose])


# ---------- guest API (respond.example.com pages) ----------

@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=60)
def open_link(key):
    row = _key_row(key)
    if row:
        status, answered_on = frappe.db.get_value(DOCTYPE, row.parent, ["status", "answered_on"])
        if status == "Answered":
            return {"state": "answered", "answered_on": format_datetime(answered_on, "dd MMM yyyy, HH:mm")}
    req, channel = guard(key, opening=True)
    return {"state": "open", "purpose": req.purpose, "for": req.recipient_name,
            "expires_on": format_datetime(req.expires_on, "dd MMM yyyy"), **handler(req).form_spec(req)}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=60)
def answer(key, decision, reason=None):
    req, channel = guard(key)
    return handler(req).on_answer(req, channel, decision, (reason or "").strip()[:500])


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=20, seconds=60)
def document_pdf(key):
    req, channel = guard(key)
    if not req.document_file:
        frappe.throw(REFUSED, frappe.PermissionError)
    file = frappe.get_doc("File", {"file_url": req.document_file, "attached_to_doctype": DOCTYPE, "attached_to_name": req.name})
    log(req, "PDF downloaded", channel)
    frappe.local.response.update({"type": "download", "filename": f"{req.reference_name}.pdf",
                                  "filecontent": file.get_content(), "content_type": "application/pdf"})


# ---------- "Document response" purpose: accept / reject a PDF (PO, Job Offer, ...) ----------

def form_spec(req):
    return {"kind": "document", "title": f"{_(req.reference_doctype)} {req.reference_name}",
            "has_pdf": bool(req.document_file), "choices": ["Accepted", "Rejected"]}


def answer_document(req, channel, decision, reason):
    if decision not in ("Accepted", "Rejected"):
        frappe.throw(_("Choose Accept or Reject."))
    if decision == "Rejected" and not reason:
        frappe.throw(_("Please give a reason for rejecting."))
    finish(req, decision, channel, reason)
    frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": req.reference_doctype,
                    "reference_name": req.reference_name,
                    "content": f"{decision} by the recipient via a response link ({channel}), see {req.name}."
                               + (f" Reason: {escape_html(reason)}" if reason else "")}).insert(ignore_permissions=True)
    notify(req.owner, f"{req.reference_doctype} {req.reference_name}: {decision.lower()} by the recipient", req.reference_doctype, req.reference_name)
    return {"ok": True, "message": f"Thank you. Your answer ({decision}) is recorded."}


on_answer = answer_document  # handler API (see HANDLERS)


# ---------- staff API ----------

@frappe.whitelist(methods=["GET"])
def rule_status(doctype):
    rule = get_rule(doctype)
    if not rule:
        return {"enabled": False}
    roles = {r.role for r in rule.requester_roles}
    return {"enabled": True, "can_request": not roles or bool(roles & set(frappe.get_roles()))}


@frappe.whitelist(methods=["POST"])
def request_document_response(doctype, name, email, recipient_name):
    """Staff: email a PDF of this document for accept / reject. Returns the hand-share link (shown once)."""
    from erpnext_drive_integrations.onboarding.kyc import EMAIL_RE

    if not get_rule(doctype):
        frappe.throw(_("Responses are not switched on for {0} (Response Rule).").format(doctype))
    check_role(doctype, "requester_roles", fallback=None)
    frappe.get_doc(doctype, name).check_permission("read")
    if not EMAIL_RE.match((email or "").strip()):
        frappe.throw(_("Enter a valid email address."))
    pdf = frappe.get_print(doctype, name, as_pdf=True)
    req, urls = create_request(doctype, name, "Document response", recipient_name=recipient_name,
                               email=email.strip(), path="r")
    file = frappe.get_doc({"doctype": "File", "file_name": f"{name}.pdf", "content": pdf, "is_private": 1,
                           "attached_to_doctype": DOCTYPE, "attached_to_name": req.name}).insert(ignore_permissions=True)
    req.document_file, req.document_sha256 = file.file_url, hashlib.sha256(pdf).hexdigest()
    system_save(req)
    send_email(req, urls["Email"], f"{_(doctype)} {name} from Example Organization Constructions",
               f"Please review {_(doctype)} {name} and accept or reject it.")
    return {"request": req.name, "manual_link": urls["Manual"]}


@frappe.whitelist(methods=["POST"])
def reset_device(request):
    """Staff: release the device lock (e.g. the vendor opened it in WhatsApp's browser, then in Chrome)."""
    req = frappe.get_doc(DOCTYPE, request)
    req.check_permission("read")
    if req.owner != frappe.session.user and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only the person who sent it, or a System Manager, can do this."), frappe.PermissionError)
    req.device_hash = None
    log(req, "Device lock released", "", f"by {frappe.session.user}")
    return True
