# Workspace HTTPS monitoring

## Purpose

Run the probes on a host independent of the services it watches. They use
Python's standard library and require outbound HTTPS. Redirects are reported
at the target route, and each configured route has its own expected status.
The probes verify TLS, make no authenticated requests and discard response
bodies. A successful status shows that the monitored route answered.

## Contents

- `https_probe.py`
- `cloud-https-monitor.service` and `cloud-https-monitor.timer`

## Requirements

Python 3 with its standard library, trusted CA certificates, outbound HTTPS
and systemd for scheduled runs.

## Reuse

Install `https_probe.py` in `/opt/cloud-monitoring`, the unit files in the
systemd unit directory and a host-specific `targets.json` in
`/etc/cloud-monitoring`. The config must be readable by the dynamic service
user. Keep credentials out of the URLs and the target labels.

## Configuration

```json
[
  {"name": "Website", "url": "https://example.com/", "statuses": [200]},
  {"name": "Document manager", "url": "https://dms.example.com/", "statuses": [302]}
]
```

## Tests

Run `python3 tests/test_https_monitor.py` from the repository root.

Check locally with `python3 https_probe.py targets.json`. Exit status 1
means at least one probe failed, and status 2 means the configuration is
invalid. Enable the timer with `systemctl enable --now cloud-https-monitor.timer`.
Read the checks through `journalctl -u cloud-https-monitor.service`.
This module provides probe results for an operator or notification integration.

## Licenses

The module uses the repository license and ships no external dependencies.

AI-assisted development by Codex.
