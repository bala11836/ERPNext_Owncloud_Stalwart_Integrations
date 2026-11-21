# Persistent isolated test workspace

The test application code is built from this repository and its pinned public
upstreams. Production supplies business data and native storage identity keys
only through the restricted snapshot exporter. Never use a production image,
copy a running app directory, or edit application source in the test containers.

## Inputs and prerequisites

Use a separate Linux Docker/Coolify host with sufficient disk for images, the
four live stores, one snapshot and a matching rollback copy. Coolify and SSH
administration remain on the private management network. Supply your own DNS,
trusted HTTPS, existing authentik, ordinary-user group and administrator.
Private keys, provider accounts, branding and business data are external inputs;
they cannot be recreated by cloning Git. Pin the controller/platform separately
and follow their official installation instructions before these app steps.

Turn off Coolify's **forced** Docker cleanup on the test host (Server >
Docker cleanup; threshold-based cleanup stays on). The forced nightly run
deletes every image no container is using, including the ERP core image the
add-on is built from and stacks not yet started, so a rebuild in progress
cannot be resumed the next day. On 18 November 2026 it removed the core and
document-processing images from the new TrueNAS test VM.

**Test host without a fixed public address** (e.g. a home connection): set
`auth_bridge_private` to the SSO proxy's private (tailnet-only) entry point and
the source it sees that traffic from (Tailscale translates forwarded tailnet
traffic to the Docker gateway, so the tailnet address itself is not visible),
and `proxy_hosts` to map the SSO hostname to the SSO host's tailnet address;
re-render the bridge on the SSO host. To publish the test hostnames without
a public address on the test host, set `relay_target` (the test host's tailnet
address) and render `tools/prepare_test_relay.py` into the relay host's
dynamic proxy directory; point the six test DNS names at the relay host; set
`proxy_protocol_trusted_ips` on the test host to the source its proxy sees for
relayed traffic. Then run
`tools/coolify_proxy_hosts.py --profile PROFILE` on the test host and restart
its proxy. During a host migration `test_server_ip` may list both hosts.

**Recreating a Coolify proxy drops the service networks Coolify attached at
deploy time.** Use `tools/coolify_proxy_http3.py --restart` (records and
reattaches them) or reconnect them by hand; never a bare `--force-recreate`
on production.

Run `tools/coolify_proxy_hosts.py --profile PROFILE` on every test host: it
saves the proxy's workspace network and test-hostname aliases (and any
`proxy_hosts` pins) in Coolify's proxy configuration, so restarting the proxy
from the dashboard keeps them.

**Optional real form emails from the test copy** (owner decision, P38): set
`test_form_smtp` in the private profile to a dedicated sending account and a
root-only password file. `address` may be the SMTP host's private (tailnet) address; TLS is still verified for `host`, and the egress firewall then allows only that address and port. Create the account with `integrations/mail/smtp_senders.py` (send-only, source-restricted). Only onboarding form emails use it, with a `[TEST]`
subject and a test-system banner; everything else stays muted. Without it,
form links go to the sender's notification bell.

Keep a root-private operator profile, generated secrets, receipts, runtime and
build directories **outside the checkout**. See
`deployment/test-runtime.example.json` and `deployment/stacks/inputs.json`.
Choose a distinct subnet and seven hostnames, including the existing SSO host.
Never point test application URLs, queues, workers or storage at production.

## Build and register from Git

1. Clone a selected commit. Run `tools/check_repository.py` and
   `tools/run_unit_tests.py` using the matching ERP Python environment.
2. Run `tools/prepare_erp_image.py --output /srv/cloud-build/core`. Build that
   generated Dockerfile using `tools/build_erp_core.py --context CONTEXT --tag TAG`.
   It mounts the generated `apps.json` as the official BuildKit `apps_json`
   input, rebuilds the builder stage and checks all nine app sources. A base64
   build argument is not consumed by this pinned official recipe. The app pins, official builder, base
   digest and Python constraints are committed under `deployment/`.
3. The office editor is ONLYOFFICE Docs (digest-pinned public image); no editor
   build step is needed. Collabora was retired in November 2026 (P42).
4. Prepare the approved test providers in existing authentik using
   `integrations/authentik/configure_test_clients.py` under native `ak shell`.
   The private input specifies source template slugs, exact test callbacks,
   shared group, application URLs and gateway. Mail defaults to the exact
   `/en/auth/callback` route; list any additional supported locales explicitly.
   Preserve existing client secrets on reruns. Transfer its root-private result
   to the test host over SSH; do not publish it. The service user must be able
   to read the temporary input; remove container-local copies after use.
5. Populate required private settings from the provider results, then run
   `tools/prepare_runtime.py --profile PROFILE --output RUNTIME`. `--source`
   defaults to the checkout. Required non-generated secrets fail closed.
   This creates six native stack specifications, marked runtime directories,
   rendered public URLs/assets and stable instance secrets. Drive's discovery
   URL uses its specific authentik application while keeping the global issuer.
6. Build the ERP addon using `deployment/erp/Dockerfile.addon`, the public core
   as `ERP_BASE_IMAGE`, and `RUNTIME/rendered` as Docker context. The Dockerfile
   is in the checkout, **not** the rendered context. Use immutable commit tags.
7. Run `tools/prepare_mail.py --source RUNTIME/rendered --output NEW_BUILD`.
   Build its pinned upstream Dockerfile with `NEXT_PUBLIC_PARENT_ORIGIN` set to
   the exact test portal origin, the selected commit and bounded build memory.
   Modified corresponding source is included in the output archive. Set the
   resulting ERP/Mail tags in the private runtime profile and rerender.
8. Register ERP, Drive, editor, Mail, DMS and processing with
   `tools/coolify_native.py`, selecting the existing controller team/server
   explicitly. Retain one receipt per service. The tool uses local native
   Coolify models, not a browser-exported API token. Re-registration must return
   the same service UUID. Compose files and receipts are private.
9. Provision the dedicated workspace network from the profile. Join the proxy
   with each test hostname as an alias. Render ingress with
   `tools/prepare_ingress.py`; publish only this instance's dynamic proxy file.
   When SSO is remote, apply `tools/prepare_auth_bridge.py` on its proxy: a fixed
   test Host context and exact test-source IP restriction, never a general
   caller-controlled authentication relay. Apply `tools/test_host_aliases.py`
   on the test host to use local trusted HTTPS without public-IP hairpinning.
   With a private bridge, also run `tools/sso_proxy_trust.py` on the SSO host with the
   entry point and sources printed by `prepare_auth_bridge.py --print-forwarded-trust`
   (exact addresses, normally the test VM only), then restart the SSO proxy at a quiet
   moment: otherwise the proxy drops `X-Forwarded-Uri` from the test proxy and the first
   sign-in returns to the landing page instead of the requested page (P65).
10. Start databases/cache/configurator, then run `tools/initialize_erp.py`
    with runtime, ERP receipt and site name. It refuses an existing site and
    installs the nine upstream apps plus the single consolidated addon.
    Start app roles with native Compose. Business scheduler and queues stay off
    during first bootstrap; activation starts report queues only after verified
    quarantine. The document worker starts after fresh owner-token enrollment.
11. Run `tools/prepare_test_profiles.py` with source, runtime, receipts, private
    profile and external secret output directory. Apply ERP bootstrap via
    native `bench execute` with its private JSON mounted read-only. Initialize
    Mail with `integrations/mail/stalwart_bootstrap.py`. Apply
    `tools/test_egress.py` before permitting test workloads to run business jobs.
    It permits the workspace subnet and the existing SSO server's IPv4 addresses
    on HTTPS. These are IP rules, not a hostname firewall: when other services
    share that server IP, test URLs, credential quarantine and disabled business
    jobs are additional isolation boundaries. No test SMTP/IMAP/submission ports
    are published.

## One-way refresh and rollback

For a fresh business installation without a source snapshot, complete native ERP
company setup, then sign the enrolled users into Drive and DMS once. Create the
shared Office Space in Drive, give the ordinary-user group editor access and the
chosen owner manager access, and record its ID privately. Supply the enrolled
user list, Space ID and processing owner to `tools/enroll_worker.py` through its
private profile. Personal files remain private; shared-space copies use the
native DMS group permissions. These company/users/Space records are business
configuration, not generic customer fixtures committed in Git.
After the **first** successful refresh on a new host, start the document
worker once with its compose profile (`--profile enrolled-worker up -d
document-worker`) and regenerate the private profiles, so later refreshes
stop, re-enroll and health-check it (found on the TrueNAS VM, 18 November).
After changing enrollment on an already running worker, restart that container:
the credentials file is updated atomically and a bind-mounted file must be
remounted. The refresh restorer holds the worker stopped until fresh enrollment
finishes, then starts it and requires its native health check to pass.

Install `tools/export_snapshot.py` from a reviewed immutable Git release on the
production host with a root-private fixed-container profile. Its restricted
SSH key is source-IP-limited with `restrict` and a forced command. The only
accepted original command is `export-test`: no shell, forwarding, filenames,
restore path or caller-selected destination. A separate read-only repository
deploy key on test is unrelated to this data-export credential.

The operator must explicitly approve brief production maintenance and native
Drive/Mail storage-key transfer. The exporter has a 100-second consistency
limit, a 120-second independent restart watchdog, a lock and minimum interval.
It pauses only selected app roles, leaving SSO/controller/databases online,
and resumes production **before compression or network transfer**. Failure
restarts previously running app roles and publishes no incomplete snapshot.
Backups are not implied by this refresh feature.

The test root worker validates the archive identity, manifest hashes, safe paths,
native confined Drive links/empty directories and byte/disk budget before test
replacement. It retains a private staged archive and a matched rollback copy.
Copied sessions, tokens, local mail credentials, delivery/scheduled actions and
external integrations are quarantined. Test SSO and site secrets stay separate;
fresh per-owner Drive/Paperless tokens are enrolled. Native Mail advertisements
must all resolve to test. Only known program-generated links/notes are retargeted;
deleted shortcuts stay deleted and user-modified shortcuts are preserved.

The initial run uses a root-created fixed request in the configured request
directory and `tools/test_refresh_worker.py --config PROFILE`. After native
record-count, application-health and enrollment validation succeeds, run
`tools/activate_test_refresh.py --config PROFILE`. It refuses activation without
a verified source receipt, enables the owner/System-Manager button, installs the
five-second request timer and persists egress policy. The successful date/time
appears below the button. Private-profile regeneration preserves this activation.
Activation also starts the short/default and long ERP queue workers so
user-triggered reports can run. The business scheduler and copied outbound
definitions remain disabled. Their container names are added to the next
refresh's stop/restart list.
Progress files contain only phase/times/request ID and are root-owned/readable by
the native ERP UID; SSH/Docker access stays out of the web process.

For a failed target restore, correct **Git source first**, publish/pull it, then
create another authorized local request and invoke the worker with
`--retry-staged`. This root-only option checks the staged source identity/hash
and retries test restoration without contacting or pausing production again.
The browser cannot select staged archives or bypass normal snapshot policy.
Success time changes only after all checks pass; failures keep the earlier
successful time and restore the matched test stores/configuration.

The in-page confirmation queues the request without a blocking browser popup.
During replacement, the test home keeps progress visible even though native ERP
sessions are deliberately cleared. Explicit logout signals still take precedence
and server permission checks remain active. On completion it navigates Home to
renew through ordinary SSO and replace stale frames/CSRF state.

After enrollment, start processing with its `enrolled-worker` profile, then
regenerate test profiles so future refreshes also pause the running worker.
Rehearse failure rollback and refresh from the UI. Never reverse-copy test data
or promote test secrets/volume contents to production.

## Acceptance and subsequent releases

Record the source commit, immutable images, native installed apps/source hashes,
asset manifest, business counts, test-only settings and browser results. Check
all portal routes, native module menus, Drive editor save, DMS/OCR ownership,
Mail/Calendar/Contacts/shared mailbox visibility and picker. Verify anonymous and
wrong-user refusal, native-client callbacks and logout separately. Provider and
physical-device acceptance in the maintainers' task list (private operations repository) remains distinct from a rebuild.

`tools/verify_test_processing.py --config PROFILE` creates one synthetic personal
PDF on marked test Drive and verifies extraction, native DMS ownership/object
permissions and its test-only generated link. It leaves the probe for inspection
until the next refresh. `tools/verify_test_collaboration.py --config PROFILE`
re-registers collaboration after Drive is healthy and checks DOCX/XLSX/PPTX
creation, hidden ODF creation and the test editor origin. The restore worker
includes this registration gate, preventing a running but unregistered editor
from being reported as a successful cold restore. Browser editing/save and
storage download verification are additional checks.

Only after these gates pass should an earlier repository be retired. Future
features follow commit → isolated test build → acceptance → production image
promotion with matched rollback data/configuration. Keep the public source
templates generic; exclude private rendered contexts, receipts and snapshots.
