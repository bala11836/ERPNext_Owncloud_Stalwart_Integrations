"""Run: python test_respond.py  (no Frappe needed; a tiny in-memory fake `frappe`).

Covers the security rules of erpnext_drive_integrations.onboarding.respond (ADR-039): only key fingerprints are stored, the first
device wins and others are refused and logged, expiry, the first answer wins, and every key goes stale.
"""
import datetime as dt
import pathlib
import sys
import types
import unittest

NOW = dt.datetime(2026, 11, 9, 12, 0)


class Throw(Exception):
    pass


class Doc(types.SimpleNamespace):
    def __init__(self, **kw):
        super().__init__(flags=types.SimpleNamespace(), **kw)

    def get(self, k, default=None):
        return getattr(self, k, default)

    def append(self, table, row):
        getattr(self, table).append(types.SimpleNamespace(**row))

    def save(self):
        STORE[self.name] = self
        SAVES.append(self.name)

    def insert(self, ignore_permissions=False):
        if getattr(self, "doctype", None) == "Notification Log":
            NOTES.append(self.subject)
            return self
        self.name = f"RSP-{len(STORE) + 1}"
        self.keys = [types.SimpleNamespace(**k) for k in self.keys]
        self.events = [types.SimpleNamespace(**e) for e in self.events]
        self.owner = "buyer@example.com"
        self.device_hash = None
        self.answer = None
        self.document_file = None
        STORE[self.name] = self
        return self

    def reload(self):
        pass


STORE, SAVES, NOTES, COOKIES_SET, CACHE = {}, [], [], {}, {}

frappe = types.ModuleType("frappe")
frappe.whitelist = lambda **kw: (lambda f: f)
frappe._ = lambda s: s
frappe.PermissionError = Throw


def throw(msg, exc=Throw):
    raise Throw(msg)


def get_doc(doctype, name=None):
    if isinstance(doctype, dict):
        return Doc(**doctype)
    return STORE[name]


def get_value(doctype, filters, fields=None, as_dict=False, for_update=False):
    if doctype == "Response Request Key":
        for req in STORE.values():
            for k in req.keys:
                if k.key_hash == filters["key_hash"]:
                    return types.SimpleNamespace(parent=req.name, channel=k.channel, stale=getattr(k, "stale", 0))
        return None
    if doctype == "Response Request":
        req = STORE[filters]
        return req.status if isinstance(fields, str) else [getattr(req, f) for f in fields]
    if doctype == "Response Rule":
        return None


frappe.throw = throw
frappe.get_doc = get_doc
frappe.get_cached_doc = get_doc
frappe.db = types.SimpleNamespace(get_value=get_value, commit=lambda: None)
frappe.flags = types.SimpleNamespace(hov_system_write=False)
frappe.session = types.SimpleNamespace(user="buyer@example.com")
frappe.conf = {"hov_respond_url": "https://respond.example"}
frappe.cache = types.SimpleNamespace(get_value=lambda k: CACHE.get(k), set_value=lambda k, v, expires_in_sec=None: CACHE.__setitem__(k, v))
frappe.get_request_header = lambda h: "TestBrowser/1.0"
frappe.request = types.SimpleNamespace(cookies={})
frappe.local = types.SimpleNamespace(request=frappe.request, request_ip="1.2.3.4",
                                     cookie_manager=types.SimpleNamespace(set_cookie=lambda k, v, **kw: COOKIES_SET.__setitem__(k, (v, kw))))
frappe.get_roles = lambda user=None: ["Purchase User"]
utils = types.ModuleType("frappe.utils")
utils.add_days = lambda d, n: d + dt.timedelta(days=n)
utils.escape_html = lambda s: s
utils.format_datetime = lambda d, fmt=None: str(d)
utils.get_datetime = lambda d: d
utils.now_datetime = lambda: NOW
utils.get_url = lambda: "https://erp.example"
frappe.utils = utils
rate = types.ModuleType("frappe.rate_limiter")
rate.rate_limit = lambda **kw: (lambda f: f)
sys.modules.update({"frappe": frappe, "frappe.utils": utils, "frappe.rate_limiter": rate})
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from erpnext_drive_integrations.onboarding import respond  # noqa: E402


def key_of(url):
    return url.rsplit("/", 1)[1]


class Respond(unittest.TestCase):
    def setUp(self):
        for d in (STORE, NOTES, COOKIES_SET, CACHE):
            d.clear()
        frappe.request.cookies = {}
        self.req, self.urls = respond.create_request("Vendor Onboarding", "VOB-1", "Vendor Onboarding",
                                                     recipient_name="Ravi", email="ravi@example.com")

    def test_only_fingerprints_stored_and_urls_use_respond_host(self):
        raw = key_of(self.urls["Email"])
        self.assertTrue(self.urls["Manual"].startswith("https://respond.example/o/"))
        self.assertNotIn(raw, str(vars(self.req)))
        self.assertEqual(self.req.keys[0].key_hash, respond.key_hash(raw))
        self.assertGreaterEqual(len(raw), 40)

    def test_first_device_wins_other_device_refused_and_logged(self):
        key = key_of(self.urls["Email"])
        with self.assertRaises(Throw):  # must tap Open first; nothing is locked by a plain call
            respond.guard(key)
        req, channel = respond.guard(key, opening=True)
        self.assertEqual(channel, "Email")
        cookie_name = f"hov_{req.name}"
        token, opts = COOKIES_SET[cookie_name]
        self.assertTrue(opts["httponly"] and opts["secure"] and opts["samesite"] == "Lax")
        frappe.request.cookies = {cookie_name: token}
        respond.guard(key)  # same device: fine
        frappe.request.cookies = {}  # another phone
        with self.assertRaises(Throw) as e:
            respond.guard(key, opening=True)
        self.assertIn("another phone", str(e.exception))
        self.assertIn("Refused: opened on another device", [ev.event for ev in req.events])
        self.assertTrue(NOTES)  # staff alerted
        manual = key_of(self.urls["Manual"])  # the other channel's link is bound to the same device
        with self.assertRaises(Throw):
            respond.guard(manual, opening=True)

    def test_unknown_and_expired_links(self):
        with self.assertRaises(Throw):
            respond.guard("not-a-real-key", opening=True)
        self.req.expires_on = NOW - dt.timedelta(minutes=1)
        with self.assertRaises(Throw):
            respond.guard(key_of(self.urls["Email"]), opening=True)
        self.assertEqual(self.req.status, "Expired")

    def test_first_answer_wins_and_all_keys_go_stale(self):
        key = key_of(self.urls["Email"])
        req, channel = respond.guard(key, opening=True)
        respond.finish(req, "Submitted", channel)
        self.assertEqual((req.status, req.answer, req.answered_via), ("Answered", "Submitted", "Email"))
        self.assertTrue(all(k.stale for k in req.keys))
        with self.assertRaises(Throw):
            respond.finish(req, "Submitted", "Manual")
        frappe.request.cookies = {f"hov_{req.name}": COOKIES_SET[f"hov_{req.name}"][0]}
        with self.assertRaises(Throw):  # even the winning device can't answer again
            respond.guard(key)
        self.assertEqual(respond.open_link(key)["state"], "answered")

    def test_people_cannot_edit_requests(self):
        respond.system_save(self.req)
        self.assertFalse(frappe.flags.hov_system_write)  # flag always reset

    def test_public_host_gate(self):
        ok = respond.allowed_on_respond_host
        key = "A" * 43
        self.assertTrue(ok("GET", f"/o/{key}", set(), ["Host", "Cookie", "X-Frappe-Site-Name", "X-Forwarded-For"]))
        self.assertTrue(ok("POST", "/api/method/erpnext_drive_integrations.onboarding.vendor.submit", {"key", "values"}, ["Host"]))
        self.assertTrue(ok("GET", "/assets/frappe/dist/css/website.bundle.css", set(), []))
        self.assertTrue(ok("GET", "/link-help", set(), []))  # friendly page for the bare address
        self.assertFalse(ok("POST", "/link-help", set(), []))
        self.assertFalse(ok("GET", "/", set(), []))  # the bare address itself is redirected by Traefik
        # everything else is refused
        self.assertFalse(ok("POST", f"/o/{key}", {"cmd"}, []))  # legacy cmd= RPC on a page path
        self.assertFalse(ok("POST", "/api/method/erpnext_drive_integrations.onboarding.vendor.submit", {"key", "cmd"}, []))
        self.assertFalse(ok("POST", "/api/method/login", {"usr", "pwd"}, []))
        self.assertFalse(ok("GET", "/api/method/frappe.auth.get_logged_user", set(), []))
        self.assertFalse(ok("GET", "/api/resource/Supplier", set(), []))
        self.assertFalse(ok("GET", "/app", set(), []))
        self.assertFalse(ok("GET", "/private/files/x.pdf", set(), []))
        self.assertFalse(ok("GET", "/o/short", set(), []))
        self.assertFalse(ok("POST", "/api/method/erpnext_drive_integrations.onboarding.respond.open_link", {"key"}, ["X-Authentik-Email"]))
        self.assertFalse(ok("POST", "/api/method/erpnext_drive_integrations.onboarding.respond.open_link", {"key"}, ["Authorization"]))
        self.assertFalse(ok("POST", "/api/method/erpnext_drive_integrations.onboarding.vendor.approve", {"name"}, []))  # staff method

    def _send(self, conf):
        sent, calls = [], []
        frappe.conf = dict({"hov_respond_url": "https://respond.example"}, **conf)
        frappe.sendmail = lambda **kw: calls.append(kw)
        orig = respond.send_test_form_email
        respond.send_test_form_email = lambda smtp, to, subject, html: sent.append((smtp, to, subject, html))
        try:
            respond.send_email(self.req, self.urls["Email"], "Supplier form", "Please fill in.")
        finally:
            respond.send_test_form_email = orig
            frappe.conf = {"hov_respond_url": "https://respond.example"}
        return sent, calls

    def test_test_copy_without_account_gives_link_to_sender(self):
        for conf in ({"cloud_test_copy": True}, {"onboarding_test_copy": 1}):
            NOTES.clear()
            sent, calls = self._send(conf)
            self.assertEqual((sent, calls), ([], []))
            self.assertTrue(NOTES and NOTES[-1].startswith("TEST COPY"))

    def test_test_copy_with_account_sends_marked_form_only_via_test_account(self):
        smtp = {"host": "mail.test", "user": "u", "password": "p", "sender": "test@example.com"}
        sent, calls = self._send({"cloud_test_copy": True, "cloud_test_form_smtp": smtp})
        self.assertEqual(calls, [], "never through Frappe's queue")
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0][1], "ravi@example.com")
        self.assertTrue(sent[0][2].startswith("[TEST] "))
        self.assertIn("TEST SYSTEM", sent[0][3])

    def test_test_smtp_connects_to_address_but_verifies_hostname(self):
        import smtplib, socket, ssl
        seen = {}

        class FakeBase:
            def __init__(self, host, port, context=None, timeout=None):
                seen["sock"] = self._get_socket(host, port, timeout)
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def login(self, user, password): seen["login"] = user
            def send_message(self, msg): seen["to"] = msg["To"]

        class FakeContext:
            def wrap_socket(self, raw, server_hostname=None):
                seen["server_hostname"] = server_hostname
                return raw
        orig = (smtplib.SMTP_SSL, socket.create_connection, ssl.create_default_context)
        smtplib.SMTP_SSL = FakeBase
        socket.create_connection = lambda addr, timeout=None: seen.setdefault("connect", addr)
        ssl.create_default_context = lambda: FakeContext()
        try:
            respond.send_test_form_email({"host": "mx.example.com", "address": "100.64.0.9", "port": 465,
                                          "user": "u", "password": "p", "sender": "s@example.com"},
                                         "ravi@example.com", "[TEST] x", "<p>x</p>")
        finally:
            smtplib.SMTP_SSL, socket.create_connection, ssl.create_default_context = orig
        self.assertEqual(seen["connect"], ("100.64.0.9", 465))
        self.assertEqual(seen["server_hostname"], "mx.example.com")
        self.assertEqual(seen["to"], "ravi@example.com")

    def test_live_site_sends_normally(self):
        sent, calls = self._send({})
        self.assertEqual(sent, [])
        self.assertEqual(len(calls), 1)
        self.assertFalse(calls[0]["subject"].startswith("[TEST]"))

    def test_device_state_helper(self):
        self.assertEqual(respond.device_state(None, None), "first")
        self.assertEqual(respond.device_state(respond.key_hash("t"), "t"), "same")
        self.assertEqual(respond.device_state(respond.key_hash("t"), "x"), "other")
        self.assertEqual(respond.device_state(respond.key_hash("t"), None), "other")


if __name__ == "__main__":
    unittest.main()
