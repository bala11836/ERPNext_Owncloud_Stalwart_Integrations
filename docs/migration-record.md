# Consolidation receipt — 15 November 2026

Production runs one custom installed app, **ERPNext_drive_integrations 0.1.0**, alongside nine retained upstream/partner apps. The former three custom registrations are gone from the installed-app list. Their functions remain modular inside the single package.

Verified:

- Fresh local database/files backup plus private native Compose, site configuration and session-state rollback material retained.
- Full metadata/schema rehearsal against a disposable isolated database, with no public listener, scheduler or external-provider network access.
- Native Module Def/link migration, controller imports and installed-app membership; no destructive app uninstallation or business-table drop.
- 25 audited business-table counts unchanged after production migration.
- All custom controller imports, 48 retained whitelisted compatibility targets and ten permission-filtered portal entries resolve.
- Backend, frontend, websocket, both queues, scheduler and collaboration service use the same consolidated ERP image. Native Coolify definitions persist the release; the configurator uses an explicit curated app list on future redeployments.
- HTTPS serves the new menu asset, the new SSO status route and the retained old spelling through a private compatibility mapping. The public response help route remains available.
- Original maintenance/scheduler state restored after verification.
- Browser About confirms the single custom app; ERPNext, Onboarding, Mail and DMS open inside the portal. Saved Navbar branding asset references were migrated to the new package.
- GitHub Actions offline checks passed on the initial release.

Source checks include offline domain/mobile/hook suites, recovered passkey recovery tests, invitation-client checks, JavaScript syntax and a publication scan for deployment identities and actual runtime secret values. No credentials, customer records, native session databases or private branding were published.

The previous repository was reviewed for authentik/Raven features and remains untouched. Source provenance is in source-review.md. Existing device/provider acceptance gaps remain in the maintainers' task list (private operations repository); this consolidation does not claim to complete them.

Runtime URLs, protocol compatibility identifiers, branding and credentials remain in private configuration. They are rendered into a separate build tree rather than committed. Future updates must rebuild from Git and deploy a matched image across all ERP roles, with database/files/config rollback retained.
