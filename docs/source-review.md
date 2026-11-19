# Source review and retained modules

The previous private ERPNext/Suite monorepo was reviewed at revision 5f814b5 (7 November 2026). Its README, invitation/recovery inventory, passkey provider policy and Raven push/session documentation were compared with the deployed sources.

Retained:

- Authentik single-email enrollment and recovery, fixed identity/expiry checks, transactional old-key replacement, provider restrictions, administrator companion and native navigation adapter. Source is in integrations/authentik/invite-recovery. Deployment-specific native object IDs and group names must be configured deliberately.
- Raven native OAuth/PKCE S256 binding to an active approved browser/identity session, token revocation and cleanup: erpnext_drive_integrations/portal/mobile.py. Native token validation and resource permissions remain mandatory.
- ERP notification/workflow push delivery, opt-in devices and a dedicated non-caching worker: portal/push.py and public/push-*.js. Native HR push remains upstream functionality. Raven background delivery from another user still requires device acceptance.
- Field attendance, supervisor permissions, automatic checkout and HR integration. Onboarding and the final Desk/portal UI are taken from the newer deployed sources.
- Private realtime ingress/startup adapters in deployment/erp. They do not fix the separately deferred idle/realtime investigation.
- The declared Insights frontend build adapter in `integrations/insights` obtains
  identity from its native authenticated user-info API rather than trusting a
  presentation cookie shared with a parent domain. The addon Dockerfile applies
  it to the pinned source and compiles the frontend; no compiled production
  bundle is copied. Native roles and document permissions remain authoritative.

Excluded:

- Retired Suite embedding, its Mail/Calendar callback and service-worker adapters, old combined search/header, old test infrastructure and superseded UI layouts.
- Databases, passkeys, session registries, native object snapshots, credentials, private logos and customer records.

The eight selected earlier planning topics are preserved and reconciled for the current stack in [roadmap.md](roadmap.md), with deployment evidence, revised requirements and the corresponding tasks in the maintainers' task list (private operations repository). Planned work is not silently treated as implemented.

The old repository remains untouched, but it is no longer a dependency of the
repository-built test deployment. The [acceptance matrix](test-acceptance.md)
records the reconstruction checks and limits. This repository contains retained
source rather than the old Git history, preventing old identity/configuration
values from entering new history.
