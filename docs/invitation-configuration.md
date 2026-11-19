# Invitations and passkey configuration

Use the shared approved-user group consistently in the invitation selector,
enrollment/recovery guards and normal passkey-login policy. The portable default
is `Workspace Users`; map it to the deployment group with `public_replacements`.
Do not recreate a retired ERP-only group to work around an empty selector.
Active status, unique email and native administrator permissions remain required.

Keep both Directory entries: **Invite users** opens the simple selection form;
**Invitations** opens native management. The simple form also has a **Manage
invitations** link. Never hide or replace native management. The historical
`hide-native-invitations.py` entry point now removes only its old marked CSS.

Render `.mjs` modules as well as HTML with the tested Git `asset_version`.
Versioned page, imported client and admin-navigation URLs prevent stale filters.

Both authentik server and worker must use the current SMTP-only sender. After
Docker network changes, verify the source IP observed by Mail and update only
the exact-IP restriction for the dedicated credential through private settings.
Keep secrets outside Git. Verify TLS, AUTH and permitted sender from both
services without sending mail; invitation receipt is a separate acceptance test.

Enrollment/recovery links are single-use. After successful enrollment, begin
normal login from the portal instead of reusing the consumed link. A retired
group reference does not require deleting or registering passkeys again.

## Test and release

Test shares the existing identity service. It does not duplicate its database
or send invitations through copied test mailboxes. Stage the rendered companion
and blueprint from Git in the test checkout, run offline regression tests, and
verify shared live rules read-only. Never apply a fresh-install blueprint over
live identity. Native policy tests must roll back and mock email. Real device
acceptance requires an approved identity and an interactive passkey ceremony.

The imported side-chat reported successful invitation receipt and repaired
shared-group checks. These historical observations are not a new delivery or
device test; the pending acceptance work remains recorded in the maintainers' task list (private operations repository).
