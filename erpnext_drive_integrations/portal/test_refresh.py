"""Test-only refresh requests. The web process never receives Docker/SSH access."""
import json
import os
from pathlib import Path
import uuid
from datetime import datetime, timezone

import frappe
from urllib.parse import urlsplit

STATE_ROOT = Path('/var/lib/cloud-integration/test-refresh')
PUBLIC_FIELDS = ('phase', 'requested_at', 'started_at', 'finished_at',
                 'last_successful_at', 'request_id', 'kind', 'last_code_refresh_at',
                 'revision')
PHASES = {'idle', 'queued', 'snapshotting', 'transferring', 'restoring',
          'validating', 'updating-code', 'succeeded', 'failed'}
# "code" resets the test site to the tested release (main); "data" replaces
# test data with a scrambled 60-day production copy (use sparingly).
KINDS = {'code', 'data'}


def enabled():
    """A restored database alone can never turn production into a refresh target."""
    return bool(os.environ.get('CLOUD_DEPLOYMENT_TIER') == 'test'
                and frappe.conf.get('cloud_test_copy') is True
                and frappe.conf.get('cloud_test_refresh_enabled') is True)


def can_request():
    allowed = {str(user).casefold() for user in (frappe.conf.get('cloud_test_refresh_users') or [])}
    return enabled() and frappe.session.user.casefold() in allowed and (
        frappe.session.user == 'Administrator' or 'System Manager' in frappe.get_roles())


def require_test_host():
    expected = urlsplit(frappe.conf.get('host_name') or '').hostname
    actual = urlsplit(frappe.request.url).hostname
    if not enabled() or not expected or actual != expected:
        frappe.throw('Refresh is available only on the configured test site.', frappe.PermissionError)


def read_state():
    file = STATE_ROOT / 'status.json'
    saved={'phase':'idle','last_successful_at':None}
    if file.exists():
        if file.is_symlink() or file.stat().st_size > 16384:
            raise RuntimeError('Invalid refresh status file')
        saved=json.loads(file.read_text())
    queued=STATE_ROOT/'request.json'
    if queued.exists():
        if queued.is_symlink() or queued.stat().st_size>4096:
            raise RuntimeError('Invalid refresh request file')
        pending=json.loads(queued.read_text())
        if pending['request_id']!=saved.get('request_id') or saved.get('phase') in {'idle','succeeded','failed'}:
            saved.update(phase='queued',request_id=pending['request_id'],requested_at=pending['requested_at'],
                         kind=pending.get('kind','data'))
    out = {key: saved.get(key) for key in PUBLIC_FIELDS}
    out['phase'] = out.get('phase') if out.get('phase') in PHASES else 'failed'
    out['kind'] = out.get('kind') if out.get('kind') in KINDS else 'data'
    if out.get('revision') is not None and not str(out['revision']).isalnum():
        out['revision'] = None
    return out


@frappe.whitelist(allow_guest=True, methods=['GET'])
def status():
    # This contains only progress/timestamps, so the already SSO-protected test
    # portal can reconnect after restoration invalidates its ERP session.
    require_test_host()
    return read_state()


@frappe.whitelist(methods=['POST'])
def request_refresh(kind='data'):
    require_test_host()
    if frappe.request.method != 'POST' or not can_request():
        frappe.throw('Only a test System Manager may replace test data.', frappe.PermissionError)
    if kind not in KINDS:
        frappe.throw('Unknown refresh kind.', frappe.ValidationError)
    STATE_ROOT.mkdir(parents=True, exist_ok=True, mode=0o750)
    request = {'request_id': str(uuid.uuid4()), 'actor': frappe.session.user,
               'requested_at': datetime.now(timezone.utc).isoformat(), 'kind': kind}
    # The fixed worker configuration selects both servers and all data paths;
    # no caller-controlled command, destination, URL or filename is accepted.
    temporary = STATE_ROOT / ('.request-' + request['request_id'])
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(request, stream)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, STATE_ROOT / 'request.json', follow_symlinks=False)
        except FileExistsError:
            frappe.throw('A refresh is already queued or running.', frappe.ValidationError)
    finally:
        temporary.unlink(missing_ok=True)
    return {'phase': 'queued', 'request_id': request['request_id'], 'kind': kind}
