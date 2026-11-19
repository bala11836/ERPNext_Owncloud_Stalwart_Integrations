# Disaster recovery and ransomware protection

Owner guideline (18 November 2026). Read together with the release policy in
`AGENTS.md` and the backup module `integrations/backup/README.md`.

## What the owner keeps outside the servers

Everything needed to rebuild is in GitHub (code, deployment definitions) or
in the encrypted backups (data, private profiles, configuration), **except**
the items below. Keep them in the password manager, with a printed or offline
copy of items 1 to 3, and review this list every three months.

1. **Backup encryption password** ("backup encryption"). Without it
   no backup can ever be restored, by anyone.
2. **TrueNAS admin password** and physical access to the TrueNAS server. The
   RustFS admin keys (to create new backup access keys) are shown in TrueNAS
   under Apps, rustfs, Edit.
3. **SSH keys** in `~/.ssh` on the owner's Mac (production, test VM, TrueNAS,
   old VPS). They exist only there: copy the folder to an encrypted USB stick
   or the password manager's secure files. If they are lost, server access
   needs the providers' rescue consoles.
4. **Account logins with recovery codes**: production VPS provider (rescue
   console), BigRock (domain and DNS), GitHub (2FA recovery codes), Tailscale
   (tailnet control), Meta business account (WhatsApp), and the authentik
   administrator account.

The individual RustFS access keys (`backup-production`, `backup-drill`) need
not be kept: they are on the servers, and new ones can be created from the
RustFS console with item 2.

## Backups and how far back we can go

- Nightly encrypted, deduplicated backups of production (all databases
  online; Drive and Mail stopped for seconds) to RustFS on TrueNAS (`tank`,
  RAID10), over the tailnet.
- Retention: **7 daily, 4 weekly, 6 monthly** (about six months).
- Weekly restore drill on the test VM with a read-only key; a full restore
  rehearsal on a separate machine (P39) proves the recovery time.

## Ransomware and compromised accounts

Threat: an attacker who controls a user account or the production server
encrypts or deletes data, including backups.

- **User accounts** cannot reach the servers; damage is limited to what the
  user can edit, and earlier versions are in the backups.
- **Production server compromise** is the serious case: production holds a
  backup key that can also delete. Protections, in order:
  1. **ZFS snapshots on TrueNAS** of the backup storage (daily, kept 60 days).
     Production has no TrueNAS login, so it cannot delete or encrypt them;
     TrueNAS can roll the store back to any snapshot.
  2. **Versioned bucket, no version deletes for production** (P40):
     production can still add backups and prune (which only hides objects),
     but cannot delete old versions or switch versioning off; hidden versions
     stay 30 days (`integrations/backup/harden_storage.py`).
  3. **Offline copy**: periodically to a USB disk kept away from the servers.
  4. TrueNAS administration stays with the owner only; the tailnet lets
     production reach only the backup storage port.
- **Measured (P39 part 1, 18 November 2026):** downloading the full
  production backup (9.3 GiB) from TrueNAS to a spare server took 10.5
  minutes and importing all databases 26 seconds, with record counts identical
  to production. A replacement server needs tailnet access first; on a host
  without a TUN device (LXC) run Tailscale with
  `--tun=userspace-networking --outbound-http-proxy-listen=127.0.0.1:1056` and
  give restic `HTTP_PROXY`/`HTTPS_PROXY` pointing at that port.
- **Measured full rebuild (P39 part 2, 18 November 2026):** six stacks built
  from the repository on a spare server and loaded from the backup through
  the tested loader (`tools/backup_to_snapshot.py`, then
  `tools/restore_test_data.py`) in about 24 minutes of machine time, plus
  image transfer or rebuild. Sign-in (authentik) is restored as a database
  only until P44.
- **Before loading data on a recovery or rehearsal host,** check its proxy
  for leftover forwards to other environments (`/data/coolify/proxy/dynamic`)
  and render its own routes with `tools/prepare_ingress.py`; confirm a local
  request reaches the local stack (for example Drive's `config.json` shows the
  host's own revision). In P39 a forward left from an earlier move sent the
  rehearsal's first requests to the live test site.
- **Sign-in service (P44):** rebuild it from the repository `identity` stack.
  First `tools/restore_identity.py secrets` reads production's authentik
  secret key and passwords from the backed-up Coolify compose (the key MUST be
  production's: users' sign-in identifiers derive from it); render the stack
  with those settings, register it, then `tools/restore_identity.py load`
  imports the database and media and reports users, applications and
  providers.
- **Next rehearsal host:** the old VPS used for P39/P44 is retired; rent a
  temporary server (or use a TrueNAS VM) for the next full rehearsal and wipe
  it afterwards the same way (no leftover forwards, keys or data).
- **If hit today:** restore yesterday's backup to a clean server (P39 is the
  rehearsal). If the backup store itself was tampered with, first roll it back
  to the last good ZFS snapshot on TrueNAS.
