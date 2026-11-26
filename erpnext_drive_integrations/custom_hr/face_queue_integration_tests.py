"""Rollback-only live checks of the face capture queue (P95) against the installed Frappe/HRMS version.

Run on a test site only: `bench --site <site> execute erpnext_drive_integrations.custom_hr.face_queue_integration_tests.run`.
Creates synthetic users and employees, uses a blank synthetic image and a stand-in face engine (no real face, no
real attendance), and rolls everything back.
"""
import base64
import io
import uuid
from pathlib import Path

import frappe
from frappe.utils import add_days, now_datetime, nowdate

from erpnext_drive_integrations.custom_hr import face_queue, face_service, service

ENGINE = 'erpnext_drive_integrations.custom_hr.face_queue_integration_tests.StandInEngine'


class StandInEngine:
    """Every photograph gives the same numbers: enough to drive the queue's paths without a face model."""
    model_id = 'stand-in-1'

    def embed(self, jpeg_bytes):
        if not frappe.flags.get('face_queue_integration_test'):  # never usable as a real engine
            raise ValueError('the stand-in engine works only inside its own test run')
        return [1.0, 0.0, 0.0, 0.0]


def run():
    original, previous = frappe.session.user, frappe.conf.get('custom_hr_face')
    token = 'fq' + uuid.uuid4().hex[:10]
    checks, test_users, files = [], [], []

    def check(label, condition):
        assert condition, label
        checks.append(label)

    def denied(label, fn):
        try:
            fn()
        except (frappe.ValidationError, frappe.PermissionError, frappe.AuthenticationError):
            checks.append(label)
            return
        raise AssertionError(label + ' was not rejected')

    def user(label, roles):
        name = f'{token}-{label}@example.invalid'
        doc = frappe.get_doc(dict(doctype='User', email=name, first_name='FACE QUEUE ' + label, enabled=1,
                                  user_type='System User', send_welcome_email=0, roles=[{'role': r} for r in roles]))
        doc.flags.no_welcome_mail = True
        doc.insert(ignore_permissions=True)
        test_users.append(name)
        return name

    frappe.set_user('Administrator')
    frappe.flags.face_queue_integration_test = True
    try:
        company = frappe.get_all('Company', pluck='name', limit=1)[0]
        gender = frappe.get_all('Gender', pluck='name', limit=1)[0]
        a = user('a', ['Field Supervisor', 'Field Attendance Approver'])
        b = user('b', ['Field Supervisor'])
        boss = user('boss', ['Field Attendance Approver'])
        day = frappe.get_doc(dict(doctype='Shift Type', name=token + ' Day', start_time='00:00:00', end_time='23:59:00',
                                  enable_auto_attendance=0)).insert(ignore_permissions=True)
        night = frappe.get_doc(dict(doctype='Shift Type', name=token + ' Night', start_time='23:59:00',
                                    end_time='00:00:00', enable_auto_attendance=0)).insert(ignore_permissions=True)
        project = frappe.get_doc(dict(doctype='Project', project_name=token, company=company, status='Open')).insert(
            ignore_permissions=True)
        site = frappe.get_doc(dict(
            doctype='Field Site', site_name=token, company=company, project=project.name, day_shift=day.name,
            night_shift=night.name, enabled=1, maximum_accuracy_m=200,
            members=[{'user': u, 'team_role': r, 'enabled': 1} for u, r in
                     [(a, 'Supervisor'), (b, 'Supervisor'), (boss, 'Approver'), (a, 'Approver')]])).insert(
            ignore_permissions=True)

        def worker(label, supervisor, machine=0):
            return frappe.get_doc(dict(
                doctype='Employee', first_name='FACE QUEUE ' + label, gender=gender, date_of_birth='1990-01-01',
                date_of_joining=add_days(nowdate(), -10), company=company, status='Active',
                custom_field_attendance_required=1, custom_field_initial_site=site.name,
                custom_field_initial_supervisor=supervisor, custom_field_machine_required=machine)).insert(
                ignore_permissions=True)

        plain, second, operator, of_a = worker('plain', b), worker('second', b), worker('operator', b, 1), worker('of-a', a)
        from PIL import Image
        buffer = io.BytesIO()
        Image.new('RGB', (160, 160), (230, 235, 230)).save(buffer, 'JPEG')
        photo = 'data:image/jpeg;base64,' + base64.b64encode(buffer.getvalue()).decode()

        def payload():
            return dict(site=site.name, shift=day.name, capture_id=uuid.uuid4().hex, photo=photo, latitude=17,
                        longitude=78, accuracy_m=10, gps_captured_at=str(now_datetime()))

        def item(name):
            return frappe.get_doc('Field Face Capture', name)

        # 1. Face recognition off: the capture waits for the project manager.
        frappe.conf['custom_hr_face'] = {}
        frappe.set_user(b)
        first = payload()
        queued = face_queue.add(first)
        doc = item(queued['name'])
        files.append(doc.photo)
        check('without a face engine the capture waits for review', doc.state == 'Needs review' and 'switched off' in doc.note)
        check('the queued photograph is private', doc.photo.startswith('/private/files/')
              and frappe.db.get_value('File', {'file_url': doc.photo}, 'is_private') == 1)
        check('a retried upload returns the same capture', face_queue.add(first)['name'] == doc.name)
        check('the supervisor sees their own capture', doc.name in [r.name for r in face_queue.mine(site.name)])
        denied('a supervisor cannot read the review queue', lambda: face_queue.pending(site.name))
        denied('a supervisor cannot decide a capture', lambda: face_queue.resolve(doc.name, plain.name))
        frappe.set_user(a)
        denied('another user cannot reuse a capture identifier', lambda: face_queue.add(first))
        frappe.set_user(boss)
        check('the project manager sees it', doc.name in [r.name for r in face_queue.pending(site.name)])
        denied('a worker outside the capturing supervisor\'s team is refused', lambda: face_queue.resolve(doc.name, of_a.name))
        check('the refused choice left the capture waiting', item(doc.name).state == 'Needs review')
        done = face_queue.resolve(doc.name, plain.name, remarks='Synthetic check')
        entry = frappe.get_doc('Field Attendance Entry', done['entry'])
        files.append(entry.photo)
        check('resolved: the entry is recorded in the supervisor\'s name and submitted',
              done['state'] == 'Resolved' and entry.captured_by == b and entry.state == 'Submitted'
              and entry.employee == plain.name and not entry.attendance)
        check('the entry keeps the photograph and the validated place',
              entry.photo.startswith('/private/files/') and float(entry.latitude) == 17)
        check('the queue gave up its own copy of the photograph',
              not item(doc.name).photo and not frappe.db.exists('File', {'attached_to_doctype': 'Field Face Capture',
                                                                          'attached_to_name': doc.name}))
        denied('a decided capture cannot be decided again', lambda: face_queue.reject(doc.name, 'again'))

        # 2. The project manager cannot decide their own capture; a rejection needs a reason.
        frappe.set_user(a)
        own = item(face_queue.add(payload())['name'])
        files.append(own.photo)
        denied('an approver cannot decide their own capture', lambda: face_queue.reject(own.name, 'mine'))
        frappe.set_user(boss)
        denied('a rejection needs a reason', lambda: face_queue.reject(own.name, ' '))
        rejected = face_queue.reject(own.name, 'Photograph of a photograph')
        check('rejected with the reason, photograph kept for now', rejected['state'] == 'Rejected' and item(own.name).photo)
        check('the supervisor is told', frappe.db.exists('Notification Log', {'for_user': a, 'document_name': own.name}))

        # 3. Face recognition on (stand-in engine): a recognised worker is recorded at once.
        frappe.conf['custom_hr_face'] = {'engine': ENGINE}
        frappe.set_user('Administrator')
        consent = {'accepted': True, 'agreement_version': 'test', 'language': 'English', 'identity_checked': True}
        face_service.enrol(second.name, [photo, photo, photo], consent)
        frappe.set_user(b)
        matched = face_queue.add(payload())
        doc = item(matched['name'])
        check('a recognised worker is recorded and submitted without a person',
              doc.state == 'Matched' and doc.employee == second.name and not doc.photo
              and frappe.db.get_value('Field Attendance Entry', doc.entry, 'state') == 'Submitted')
        files.append(frappe.db.get_value('Field Attendance Entry', doc.entry, 'photo'))

        # 4. Recognised, but a rule needs a person (machine allocation): it waits, and the project manager completes it.
        frappe.set_user('Administrator')
        face_service.withdraw(second.name, 'Synthetic check')
        face_service.enrol(operator.name, [photo, photo, photo], consent)
        frappe.set_user(b)
        waiting = item(face_queue.add(payload())['name'])
        files.append(waiting.photo)
        check('a recognised operator without a machine allocation waits for review',
              waiting.state == 'Needs review' and waiting.decision == 'match' and 'not recorded' in waiting.note
              and not waiting.entry)
        frappe.set_user(boss)
        completed = face_queue.resolve(waiting.name, operator.name, work_mode='Standby')
        check('the project manager completes it with the allocation', completed['state'] == 'Resolved'
              and frappe.db.get_value('Field Attendance Entry', completed['entry'], 'work_mode') == 'Standby')
        files.append(frappe.db.get_value('Field Attendance Entry', completed['entry'], 'photo'))

        # 5. Rejected captures lose their photograph after the retention period.
        frappe.db.set_value('Field Face Capture', own.name, 'resolved_at', add_days(now_datetime(), -face_queue.RETENTION_DAYS - 1))
        face_queue.purge_rejected()
        check('an old rejected capture keeps its record and loses its photograph',
              not item(own.name).photo and item(own.name).remarks == 'Photograph of a photograph')
        print('FACE_QUEUE_INTEGRATION_PASS', len(checks), checks)
    finally:
        frappe.db.rollback()
        frappe.flags.face_queue_integration_test = False
        if previous is None:
            frappe.conf.pop('custom_hr_face', None)
        else:
            frappe.conf['custom_hr_face'] = previous
        frappe.set_user(original)
        for url in files:
            path = Path(frappe.get_site_path('private', 'files', str(url or '').rsplit('/', 1)[-1])) if url else None
            if path and path.exists():
                path.unlink()
        for name in test_users:
            frappe.clear_cache(user=name)
        print('FACE_QUEUE_TEST_DATA_ROLLED_BACK')
