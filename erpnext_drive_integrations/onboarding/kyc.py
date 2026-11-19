"""Vendor KYC rules (ADR-039). Pure functions (no Frappe import), so they are unit-tested without a bench.

Free checks only (MD 2026-11-09): PAN format, PAN type letter vs constitution, PAN must equal the PAN inside
the GSTIN, GSTIN format + check digit, IFSC format, bank account typed twice. Paid checks (PAN-verify API,
MCA directors, bank Rs 1 check) plug in later.
"""
import re

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
ACCOUNT_RE = re.compile(r"^[0-9]{9,18}$")
GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# 4th letter of a PAN tells the holder type (Income Tax PAN structure).
CONSTITUTION_PAN_LETTERS = {
    "Proprietorship": ("P",),  # the proprietor's own PAN
    "Partnership": ("F",),
    "LLP": ("F",),
    "Company": ("C",),
    "HUF": ("H",),
    "Trust / Society": ("T", "A"),  # trust / association of persons (societies, clubs)
}
CONSTITUTIONS = tuple(CONSTITUTION_PAN_LETTERS)
# ERPNext Supplier.supplier_type has only Company / Individual / Partnership; the exact constitution is kept
# in the custom field hov_constitution.
SUPPLIER_TYPE = {"Proprietorship": "Individual", "Partnership": "Partnership", "LLP": "Partnership",
                 "Company": "Company", "HUF": "Individual", "Trust / Society": "Company"}
DOCUMENT_TYPES = ("GST certificate", "PAN card", "Cancelled cheque", "Udyam certificate", "Director check screenshot")

ERROR, WARN, INFO = "error", "warning", "info"


def norm(value):
    """Upper-case and drop spaces: 'abcde 1234f' -> 'ABCDE1234F'."""
    return re.sub(r"\s+", "", str(value or "")).upper()


def changed(old, new):
    """True when an email / mobile really changed (case and spaces ignored), so its verification must go."""
    clean = lambda v: re.sub(r"\s+", "", str(v or "")).lower()  # noqa: E731
    return clean(old) != clean(new)


def norm_mobile(value):
    """Indian mobile -> '+91XXXXXXXXXX', or '' when it is not a valid 10-digit mobile (starts 6-9)."""
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return f"+91{digits}" if re.fullmatch(r"[6-9][0-9]{9}", digits) else ""


def mask_email(email):
    user, _, domain = str(email or "").partition("@")
    return f"{user[:1]}***@{domain}" if domain else ""


def mask_mobile(mobile):
    digits = re.sub(r"\D", "", str(mobile or ""))
    return "••••••" + digits[-4:] if len(digits) >= 4 else ""


def gstin_check_digit(first14):
    """GSTIN 15th character (GSTN mod-36 checksum)."""
    total = 0
    for i, ch in enumerate(first14):
        product = GSTIN_CHARS.index(ch) * (2 if i % 2 else 1)
        total += product // 36 + product % 36
    return GSTIN_CHARS[(36 - total % 36) % 36]


def gstin_problem(gstin):
    gstin = norm(gstin)
    if not GSTIN_RE.match(gstin):
        return "GSTIN format is wrong (15 characters, like 36ABCDE1234F1Z5)."
    if gstin_check_digit(gstin[:14]) != gstin[14]:
        return "GSTIN check digit is wrong; please re-check the number."
    return None


def pan_from_gstin(gstin):
    """Characters 3-12 of a GSTIN are the holder's PAN."""
    return norm(gstin)[2:12]


def pan_problems(pan, constitution, gstin=None):
    pan = norm(pan)
    if not PAN_RE.match(pan):
        return ["PAN format is wrong (10 characters, like ABCDE1234F)."]
    problems = []
    letters = CONSTITUTION_PAN_LETTERS.get(constitution)
    if letters and pan[3] not in letters:
        problems.append(f"PAN type letter '{pan[3]}' does not match {constitution} (expected {' or '.join(letters)}).")
    if gstin and not gstin_problem(gstin) and pan_from_gstin(gstin) != pan:
        problems.append("PAN does not match the PAN inside the GSTIN.")
    return problems


def ifsc_problem(ifsc):
    return None if IFSC_RE.match(norm(ifsc)) else "IFSC format is wrong (11 characters, like SBIN0001234)."


def parse_ifsc(payload):
    """Razorpay IFSC directory reply -> the fields we keep."""
    payload = payload or {}
    return {"bank_name": (payload.get("BANK") or "").strip(), "bank_branch": (payload.get("BRANCH") or "").strip(),
            "bank_city": (payload.get("CITY") or "").strip(), "micr": (payload.get("MICR") or "").strip()}


def name_matches(a, b):
    """Loose business-name match: ignores case, punctuation and common suffixes (M/s, Pvt Ltd ...)."""
    def core(s):
        s = re.sub(r"[^a-z0-9 ]", " ", str(s or "").lower())
        drop = {"m", "s", "ms", "pvt", "private", "ltd", "limited", "llp", "the", "and", "co", "company"}
        return " ".join(w for w in s.split() if w not in drop)
    return bool(core(a)) and core(a) == core(b)


def principal(persons):
    found = [p for p in persons or [] if p.get("is_principal")]
    return found[0] if len(found) == 1 else None


def vendor_problems(data, persons, account_confirm=None):
    """All checks for a vendor form. Returns [(level, message)]; any ERROR blocks the vendor's submit.

    data: the Vendor Onboarding fields (dict-like). persons: list of person dicts.
    account_confirm: what the vendor re-typed for the bank account (None = not checked here).
    """
    out = []
    add = lambda level, msg: out.append((level, msg))  # noqa: E731
    if not (data.get("business_name") or "").strip():
        add(ERROR, "Business name is required.")
    constitution = data.get("constitution")
    if constitution not in CONSTITUTIONS:
        add(ERROR, "Choose the constitution (Proprietorship, Partnership, LLP, Company, HUF, Trust / Society).")
    gstin = norm(data.get("gstin"))
    if data.get("no_gst"):
        if gstin:
            add(ERROR, "You ticked 'no GST registration' but also gave a GSTIN.")
    elif not gstin:
        add(ERROR, "GSTIN is required (or tick 'no GST registration').")
    elif problem := gstin_problem(gstin):
        add(ERROR, problem)
    for problem in pan_problems(data.get("pan"), constitution, gstin or None):
        add(ERROR, problem)
    if constitution == "Company" and not norm(data.get("cin")):
        add(WARN, "CIN not given (needed for the director check).")
    for field, label in (("address_line1", "Address line 1"), ("city", "City"), ("state", "State"), ("pincode", "PIN code")):
        if not (str(data.get(field) or "")).strip():
            add(ERROR, f"{label} is required.")
    if data.get("pincode") and not re.fullmatch(r"[1-9][0-9]{5}", str(data.get("pincode")).strip()):
        add(ERROR, "PIN code must be 6 digits.")
    if problem := ifsc_problem(data.get("ifsc")):
        add(ERROR, problem)
    account = norm(data.get("bank_account_no"))
    if not account:
        add(ERROR, "Bank account number is required.")
    elif not ACCOUNT_RE.match(account):
        add(WARN, "Bank account number is not 9-18 digits; please double-check.")
    if account_confirm is not None and norm(account_confirm) != account:
        add(ERROR, "The re-typed bank account number does not match.")
    if not (data.get("account_holder_name") or "").strip():
        add(ERROR, "Account holder name is required.")
    if not persons:
        add(ERROR, "Add at least one contact person.")
    main = principal(persons)
    if not main:
        add(ERROR, "Choose exactly one principal contact.")
    for p in persons or []:
        who = p.get("person_name") or "A contact person"
        if not (p.get("person_name") or "").strip():
            add(ERROR, "Every contact person needs a name.")
        if p.get("email") and not EMAIL_RE.match(p["email"].strip()):
            add(ERROR, f"{who}: email address looks wrong.")
        if p.get("mobile") and not norm_mobile(p["mobile"]):
            add(ERROR, f"{who}: mobile must be a 10-digit Indian mobile number.")
    if main and not (main.get("email") or "").strip():
        add(ERROR, "The principal contact needs an email address (it is verified by a link).")
    if main and not norm_mobile(main.get("mobile")):
        add(ERROR, "The principal contact needs a mobile number.")
    # Facts from the GST lookup (written by the server, never by the vendor).
    if gstin and not data.get("gst_checked_on"):
        add(WARN, "GST details not checked online yet.")
    if data.get("gst_status") and data.get("gst_status") != "Active":
        add(WARN, f"GST registration status is '{data.get('gst_status')}', not Active.")
    gst_names = [n for n in (data.get("gst_legal_name"), data.get("gst_trade_name")) if n]
    if gst_names and not any(name_matches(data.get("business_name"), n) for n in gst_names):
        add(WARN, "Business name differs from the GST legal / trade name.")
    return out


def changed_fields(before, after, labels):
    """Labels of fields whose value changed between two dicts (used to show staff what the vendor changed)."""
    return [label for field, label in labels.items() if str(before.get(field) or "").strip() != str(after.get(field) or "").strip()]


def split_name(full):
    parts = str(full or "").strip().split()
    return (" ".join(parts[:-1]), parts[-1]) if len(parts) > 1 else (parts[0] if parts else "", "")


# ---- Mapping into ERPNext's own records (Supplier, Address, Contact, Bank Account) ----

def supplier_doc(ob):
    return {"doctype": "Supplier", "supplier_name": ob["business_name"].strip(),
            "supplier_type": SUPPLIER_TYPE.get(ob["constitution"], "Company"),
            "gstin": norm(ob.get("gstin")) or None, "gst_category": ob.get("gst_category") or ("Unregistered" if ob.get("no_gst") else None),
            "pan": norm(ob.get("pan")), "country": "India", "hov_constitution": ob["constitution"],
            "hov_cin": norm(ob.get("cin")) or None, "hov_udyam": norm(ob.get("udyam_number")) or None,
            "hov_gst_status": ob.get("gst_status") or None, "hov_vendor_onboarding": ob.get("name")}


def address_doc(ob, supplier):
    return {"doctype": "Address", "address_title": ob["business_name"].strip(), "address_type": "Billing",
            "address_line1": ob["address_line1"].strip(), "address_line2": (ob.get("address_line2") or "").strip() or None,
            "city": ob["city"].strip(), "state": ob["state"].strip(), "pincode": str(ob["pincode"]).strip(),
            "country": "India", "gstin": norm(ob.get("gstin")) or None,
            "gst_category": ob.get("gst_category") or ("Unregistered" if ob.get("no_gst") else None),
            "is_primary_address": 1, "links": [{"link_doctype": "Supplier", "link_name": supplier}]}


def contact_doc(person, supplier):
    first, last = split_name(person["person_name"])
    doc = {"doctype": "Contact", "first_name": first, "last_name": last or None,
           "designation": (person.get("designation") or "").strip() or None,
           "is_primary_contact": 1 if person.get("is_principal") else 0,
           "email_ids": [], "phone_nos": [], "links": [{"link_doctype": "Supplier", "link_name": supplier}],
           "hov_email_verified_on": person.get("email_verified_on") or None,
           "hov_whatsapp_opt_in": 1 if person.get("whatsapp_opt_in") else 0, "hov_opt_in_on": person.get("opt_in_on") or None,
           "hov_is_director": person.get("director_check") or None}
    if person.get("email"):
        doc["email_ids"].append({"email_id": person["email"].strip(), "is_primary": 1})
    if mobile := norm_mobile(person.get("mobile")):
        doc["phone_nos"].append({"phone": mobile, "is_primary_mobile_no": 1})
    return doc


def bank_account_doc(ob, supplier, bank):
    return {"doctype": "Bank Account", "account_name": ob["account_holder_name"].strip(), "bank": bank,
            "bank_account_no": norm(ob["bank_account_no"]), "branch_code": norm(ob["ifsc"]),
            "party_type": "Supplier", "party": supplier, "is_default": 1, "is_company_account": 0}


# ---- KYC Amendment: what may be changed, and where it lives in ERPNext ----
# label -> (record, field). Bank changes always create a NEW Bank Account (old one disabled), never an edit.
AMENDABLE = {
    "Business name": ("Supplier", "supplier_name"),
    "Udyam number": ("Supplier", "hov_udyam"),
    "Address line 1": ("Address", "address_line1"),
    "Address line 2": ("Address", "address_line2"),
    "City": ("Address", "city"),
    "State": ("Address", "state"),
    "PIN code": ("Address", "pincode"),
    "Bank IFSC": ("Bank Account", "branch_code"),
    "Bank account no.": ("Bank Account", "bank_account_no"),
    "Account holder name": ("Bank Account", "account_name"),
    "Principal contact email": ("Contact", "email_id"),
    "Principal contact mobile": ("Contact", "mobile_no"),
}
BANK_LABELS = frozenset(k for k, (rec, _) in AMENDABLE.items() if rec == "Bank Account")


def amendment_problems(changes):
    """changes: [{field, new_value}] -> list of error strings."""
    errors, seen = [], set()
    for row in changes:
        label, value = row.get("field"), str(row.get("new_value") or "").strip()
        if label not in AMENDABLE:
            errors.append(f"'{label}' cannot be amended here.")
            continue
        if label in seen:
            errors.append(f"'{label}' is listed twice.")
        seen.add(label)
        if not value and label != "Address line 2":
            errors.append(f"New value for '{label}' is empty.")
        elif label == "Bank IFSC" and ifsc_problem(value):
            errors.append(ifsc_problem(value))
        elif label == "Principal contact email" and not EMAIL_RE.match(value):
            errors.append("New principal contact email looks wrong.")
        elif label == "Principal contact mobile" and not norm_mobile(value):
            errors.append("New principal contact mobile must be a 10-digit Indian mobile.")
        elif label == "PIN code" and not re.fullmatch(r"[1-9][0-9]{5}", value):
            errors.append("PIN code must be 6 digits.")
    return errors
