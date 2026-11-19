# Moving a running service onto the repository build

How an app that was first set up by hand (a "legacy" Coolify service) is moved
onto the stack rendered from this repository, without losing data and with a
pause of seconds. Used for the ERP, the office editor, Drive, DMS, Mail and
private DNS in November 2026. The dated records, with real addresses and
service IDs, are kept in the maintainers' private operations repository.

## Why

Production must be reproducible from Git. A hand-made service drifts, and a
Coolify redeploy can silently restore old settings. After a move, every
setting comes from a tested release plus a private profile outside Git.

## Steps

1. **Release and gate.** The change is committed, pushed and validated on the
   test site first (see `AGENTS.md`).
2. **Private production profile.** Outside Git, next to the other secrets.
   The renderer (`tools/prepare_runtime.py`) supports the options a move
   needs:
   - `existing_volumes`: reuse the legacy service's named data volumes;
   - `existing_mounts`: reuse persistent bind-mounted directories;
   - `extra_networks`: keep old network aliases that other services still use;
   - `production_bindings`: production-only host ports and `extra_hosts`
     (validated: IPv4 host addresses only);
   - `production_mail_ports`: the mail ports, for the Mail stack only.
3. **Carry the settings.** Take every setting from the legacy service. Inside
   one compose file, a key in `environment` **overrides** the same key in an
   `env_file`, so merge as `{**env_file, **environment}`. Then compare the
   environment of the new containers with the **running** legacy containers
   (`docker inspect -f '{{json .Config.Env}}'`), not with reconstructed files.
   (A Mail move once lost the portal from webmail's allowed frame ancestors
   because the merge order was reversed and the comparison repeated it.)
4. **Route file.** Replace the legacy container labels with a Traefik file
   route rendered from `deployment/production/*.traefik.yaml` (written for
   `example.com`; the deployment substitutes the real domain). Check routes
   that point at the old router names elsewhere (for example an ACME challenge
   route for the mail server's own certificate).
5. **Rollback point.** Copy the legacy compose file, its `.env`, env files and
   affected route files to a dated folder with checksums.
6. **Register and switch.** Register the rendered stack with Coolify
   (`tools/coolify_native.py`), stop the legacy containers (restart policy
   off, nothing deleted), start the new stack and install the route file.
7. **Verify** what users rely on: pages, sign-in, framing inside the portal,
   protocols (SMTP, IMAP, DNS), and that the data is the existing data.
8. **Backups and test refresh.** Point the backup profile and the test-refresh
   exporter at the new container names, and check that every container they
   name exists.
9. **Owner check, then delete.** After the owner confirms, delete the legacy
   service with Coolify's own delete, keeping volumes the new stack uses.
10. **Record** the move (release record, decisions, module README).

## Office editor note

After any restart of Drive (oCIS), restart its collaboration service as well,
so the editor registers again.
