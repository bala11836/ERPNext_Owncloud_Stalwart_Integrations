# Native Mail and integration senders

Use the pinned native Stalwart server and the separately compiled Mail overlay.
Fresh native configuration comes from
`integrations/mail/stalwart_bootstrap.py --profile PRIVATE_JSON`; keep its recovery
credential, account mapping and identity provider inputs outside Git. The shared
`noreply` Group mailbox is distinct from each person's User mailbox. Application
group access in authentik does not by itself assign a mailbox or send-as rights.
Set each person's signed mailbox claim and native group membership deliberately.

## Production-only transport

The runtime profile may contain `production_mail_ports`, a list of explicit
IPv4 host bindings such as `192.0.2.10:25:25` and `100.64.0.10:465:465`. Supported
matching ports are 25, 465, 587 and 993; select only the protocols required by the
current policy. The renderer rejects this list on test. Private native recovery
HTTP remains on the separately configured loopback port. These Docker mappings
do not replace firewall/source restrictions, native listeners or trusted TLS.

Configure the native server's default SMTP hostname, service advertisements,
certificate/renewal, protocol listeners and source restrictions before enabling
production sending. SMTP service certificates must match the hostname used by
clients; do not turn off certificate validation. Add DNS MX/SPF/DKIM/DMARC and
provider PTR for the chosen domain/IP, and verify actual delivery separately.
Keep Mail administration private. The ingress recipe exposes only the native
read-only filtered GET `/api/admin/policy` needed by the public web UI; settings
writes and other admin routes retain the private administration restriction.

## Sole integration sender

`integrations/mail/smtp_senders.py --profile PRIVATE_JSON --output PRIVATE_JSON`
creates/reuses dedicated SMTP-only native User service accounts, with
authenticate/send permissions and membership of the shared `noreply` mailbox.
Each generated app password is limited to explicitly supplied source networks.
It grants no mailbox-reading or administrative permission. The tool refuses
test mode and writes secrets only to its private external output. Repeated runs
reuse the same credential IDs instead of silently rotating them.

The profile supplies `tier: production`, native `admin_url`, recovery credential,
mail domain, SMTP hostname and `senders`. Each sender has a dedicated name such
as `smtp-erp` or `identity-noreply`, `shared_sender: noreply`, and a nonempty
`allowed_networks` list. Use a separate service identity for ERP and authentik.
Account/password inventory and any rotation remain private administrative data.

Configure native ERP Email Account fields with the shared noreply From address,
the service identity as login ID, its native encrypted password, SMTP hostname,
port 465 and SSL. Do not enable incoming mail for this service account. Update
integration/notification From references to the shared noreply address; preserve
personal accounts. Configure authentik's native email environment with its
separate service identity, SSL/465 and noreply From address. Credentials belong
in native encrypted fields/private runtime inputs, never browser assets or Git.

Verify an authenticated TLS connection and the expected envelope/sender. A real
send/receipt test requires the intended recipient and message to be authorized;
source generation or a working web inbox does not establish delivery health.

## Test isolation

Four-app refresh preserves native Mail storage identity keys so copied messages
remain readable, but replaces the directory/audience with the test provider,
clears copied local User credentials, disables SMTP/IMAP/POP/submission listeners
and retargets all service advertisements to the test hostname. It restarts the
native server to activate cached advertisements, then verifies the session's
API/download/upload/event-source URLs before browser access is accepted.
The independent test egress policy also blocks external business delivery.
No production mail transport bindings or integration passwords are enrolled.
