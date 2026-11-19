> Sanitized operating record before package consolidation. Deployment examples use reserved addresses and generic identities. See the migration record for the final installed-package state.

# Idle navigation investigation — 15 November 2026

Read-only production investigation; no timeout, proxy, permission or application code changes made.

Observed:
- Existing retained ERP tab: module chooser opened without reload. Page URL and displayed list title were inconsistent (Payment Entry URL with Sales Invoice content). Full long-idle freeze was not deterministically reproduced.
- Separate portal test retained the HR, Onboarding, India Compliance and Framework frames while switching apps. Menus and subsequent navigation worked: Response Request, Expense Claim, GSTR 3B Report, Framework DocType.
- Raven command menu opened; Raven displayed explicit “Realtime events aren't working. Please refresh the page.” warning.
- Insights Workbooks navigation succeeded.
- Browser console repeatedly reported Socket.IO “Invalid origin” in the shared Frappe desk runtime. This is a confirmed real-time connectivity defect, not proof that it causes every stalled menu.
- Current ERP System Settings session_expiry is 170:00 hours; deny_multiple_sessions=0. A short Frappe idle timeout is not supported by this configuration.
- ERP OIDC access tokens: five minutes, refresh tokens thirty days; ERP proxy provider access tokens five minutes, refresh tokens eight hours. Access-token expiry alone must not be equated to logout; proxy renewal still needs validation under a real failure.
- Snapshot server resource use showed low ERP CPU and modest memory use; no current evidence of VPS exhaustion. This snapshot cannot exclude historical spikes.
- Custom session.js catches all fetch/JSON errors silently, has no fetch timeout and does not distinguish redirect-to-SSO HTML from a normal API response. Custom module adapter refreshes on window focus and mutations but does not explicitly handle document resume or portal frame reactivation. These are recovery gaps, not established root causes of the report.

Recommended sequence:
1. Diagnose and correct the public websocket Host/Origin/namespace routing so authenticated Frappe and Raven reconnect successfully. Preserve origin and authentication protections.
2. Add bounded, single-flight session validation plus explicit visible/resume/online/portal-activation recovery. Distinguish offline, server errors and expired authentication; reconnect native realtime and rebind menus as needed.
3. Preserve unsaved forms and editor drafts. Offer explicit recovery/re-authentication; do not blindly auto-reload the whole portal on a timer.
4. Capture sanitized failure-time route, HTTP status, redirect/content type, JS exception and socket state, then test actual long background/PC sleep/network interruption. Current short retained-frame tests do not certify overnight idle reliability.

Primary references:
- https://developer.chrome.com/docs/web-platform/page-lifecycle-api
- https://github.com/frappe/frappe/issues/39831 (closed/fixed upstream; similar historical expiry behavior, not proof our deployed version still has that bug)
- https://docs.frappe.io/framework/user/en/api/realtime

## Follow-up — 16 November 2026: idle menu freeze cause and client fix

Owner report: ERP menus (not the whole page) stop responding after the tab has
been idle or the computer asleep; a reload fixes it.

Cause identified from the versioned configuration (not yet confirmed on a live
failure capture):
- ERP is behind the authentik proxy outpost (`forward_single`). Its session is
  renewed by a refresh token valid for **8 hours**; Frappe's own session lasts
  170 hours.
- After the proxy session lapses, Desk background requests are redirected to
  SSO. The browser blocks that cross-site redirect for XHR/fetch, so menu
  actions silently fail while the rendered page still scrolls.
- `session.js` could not see this: `sso.session_status` deliberately bypasses
  the outpost and keeps reporting "authenticated".
- A reload is a top-level navigation, which follows the redirect; authentik
  silently re-issues the proxy session.

Change (`public/session.js`, asset `?v=20261116-idle1`):
- Existing session/logout checks are single-flight with an 8-second timeout.
- On resume (visibility, pageshow, network online) and on first interaction
  after at least a minute, probe a proxy-protected endpoint
  (`frappe.auth.get_logged_user`) without following redirects.
- On a redirect or 401, renew in a hidden same-origin frame through the normal
  SSO flow, exactly as a reload would. No authentication rule, token lifetime,
  origin check or proxy route is changed.
- If renewal needs interaction (SSO session also expired), show a "Reload"
  notice instead of reloading automatically, so unsaved work is not discarded.
- After renewal, reconnect the Frappe realtime socket if it is disconnected.
- No timer probes: an unattended tab does not keep the proxy session alive.
- `module-header-20261115.js?v=4` also refreshes on pageshow, online and
  visibility return.

Pre-deployment check (local Chromium, simulated ERP and SSO hosts): with a
valid SSO session the expired proxy is renewed silently and no notice appears;
with an SSO login required, the notice appears; no hidden frames are left.

Still required on permanent test before production: let a signed-in tab idle
beyond 8 hours (or shorten the **test** proxy provider's refresh validity) and
with computer sleep, then confirm menus work without reload across ERPNext, HR,
Onboarding, India Compliance, Framework, Raven and Insights; confirm the notice
path after SSO sign-out; and capture console/network state if any freeze
remains. The Socket.IO "Invalid origin" defect is separate and not addressed by
this change.
