# First administrator at setup (P77)

Choose the first administrator of a fresh authentik instance at setup time and
switch off the built-in `akadmin` account.

## What it does

`first-admin.sh <server container> [administrator folder]` asks the person setting
up the instance for the administrator's email and name (no password), asks for
confirmation, and then:

- creates or refreshes that administrator in the given folder (default
  `administrators`), in the administrator group, **without a password**;
- prints a one-time link, valid for 24 hours, that registers the administrator's
  passkey and signs them in. The passkey must come from an approved provider in
  [`passkey-providers.json`](../passkey-providers.json) (shared by every passkey check, P79) (Apple Passwords, Bitwarden
  or Vaultwarden, Google Password Manager, Chrome on Mac), with user verification;
- switches off `akadmin`: inactive, a random password nobody knows, no groups,
  roles or tokens.

Rerun the same command to issue a new link, for example after a lost passkey;
the previous link stops working. Remove the lost passkey under the user's MFA
devices in the admin interface.

## Why `akadmin` is switched off, not deleted

Upstream's first-time setup page (`initial-setup`) opens whenever `akadmin` is
missing or has no usable password, and upstream's bootstrap blueprint creates
`akadmin` if it is absent. A present but inactive `akadmin` with an unknown
password keeps that page closed; the bootstrap blueprint only creates the
account and never reactivates it.

## Use

On a fresh install, keep upstream's `AUTHENTIK_BOOTSTRAP_PASSWORD` set until this
command has run, so the setup page is closed from the first start. Then remove
the bootstrap password from the environment.

    ./first-admin.sh <authentik server container> [administrator folder]

`FIRST_ADMIN_EMAIL`, `FIRST_ADMIN_NAME` and `FIRST_ADMIN_YES=1` skip the questions
for automation. `FIRST_ADMIN_BASE_URL` overrides `AUTHENTIK_WEB__BASE_URL` for the
link. `DOCKER` selects the container command (default `docker`).

Send the link over a private channel; never put it into logs, tickets or Git.
The sign-in flow of the deployment must accept the administrator's passkey
(for example production's passkey sign-in, or a login policy that admits the
administrator folder after an approved passkey).

## Tests

`tests/test_first_admin.py` checks the provider list, the link and passkey rules
and that `akadmin` is switched off rather than deleted. The behaviour was
verified on a throwaway authentik 2026.8 instance: the setup page stays closed
before and after, a rerun invalidates the previous link, the link reaches passkey
registration once, `akadmin` stays off after the bootstrap blueprint is applied
again, and sign-in is admitted only after an approved passkey from the link.

Development was assisted by Claude Code.
