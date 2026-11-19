"""Opt-in ERP workflow/system push through the native hosted relay.

Device credentials are encrypted in the existing private SSO registry. UI subscription
never grants app or document access. Lockscreen payloads deliberately contain no
business document names, message text, amounts or approval action tokens.
"""
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlsplit
import requests
import frappe
from . import sso

PROJECT = 'hrms'
RELAY = 'https://push-notification-relay.frappe.cloud'
SDK = '10.8.0'

def enabled():
    return bool(frappe.conf.get('cloud_push_enabled'))

def init_state():
    sso.init_state()
    with sso.registry() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS push_devices (
            id TEXT PRIMARY KEY, site TEXT NOT NULL, user TEXT NOT NULL,
            browser TEXT NOT NULL, token TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
            created INTEGER NOT NULL, updated INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS push_owner ON push_devices(site,user,browser);
        CREATE TABLE IF NOT EXISTS push_receipts (
            site TEXT NOT NULL, event TEXT NOT NULL, user TEXT NOT NULL,
            status TEXT NOT NULL, updated INTEGER NOT NULL, PRIMARY KEY(site,event,user));
        ''')

def authenticated_browser():
    if frappe.session.user == 'Guest':
        raise frappe.PermissionError('Sign in first')
    record = sso.current_record()
    if not record or sso.revoked(record) or record['user'] != frappe.session.user:
        raise frappe.AuthenticationError('A fresh Authentik session is required')
    return record

def _relay(method, values):
    if not enabled() or frappe.conf.get('push_relay_server_url', '').rstrip('/') != RELAY:
        raise RuntimeError('Native push relay is not configured')
    doc = frappe.get_single('Push Notification Settings')
    if not doc.enable_push_notification_relay or not doc.api_key or not doc.api_secret:
        raise RuntimeError('Native push relay registration is incomplete')
    payload = dict(values, project_name=PROJECT, site_name=urlsplit(frappe.utils.get_url()).hostname)
    response = requests.post(RELAY+'/api/method/notification_relay.api.'+method,
        json=payload, headers={'Authorization':'token '+doc.api_key+':'+doc.get_password('api_secret')},
        timeout=10, allow_redirects=False)
    response.raise_for_status()
    data = response.json()
    if isinstance(data.get('message'), dict): data = data['message']
    if data.get('success') is not True:
        raise RuntimeError('Push relay declined the request')
    return data

def _encrypt(value):
    from frappe.utils.password import encrypt
    return encrypt(value)

def _decrypt(value):
    from frappe.utils.password import decrypt
    return decrypt(value)

def _devices(user):
    init_state()
    with sso.registry() as db:
        return db.execute('''SELECT p.* FROM push_devices p JOIN browsers b ON b.id=p.browser
            WHERE p.site=? AND p.user=? AND p.enabled=1 AND b.revoked=0 AND b.user=p.user
            AND EXISTS(SELECT 1 FROM sessions s LEFT JOIN revoked_oidc r ON r.sid=s.oidc_sid
                WHERE s.browser=p.browser AND s.site=p.site AND s.user=p.user AND r.sid IS NULL)''',
            (frappe.local.site,user)).fetchall()

@frappe.whitelist(methods=['GET'])
def status():
    record = authenticated_browser()
    init_state()
    with sso.registry() as db:
        count = db.execute('SELECT COUNT(*) FROM push_devices WHERE site=? AND user=? AND browser=? AND enabled=1',
            (frappe.local.site,frappe.session.user,record['browser'])).fetchone()[0]
    return {'available':enabled(), 'enabled':bool(count), 'project':PROJECT, 'sdk_version':SDK}

@frappe.whitelist(methods=['GET'])
def configuration():
    authenticated_browser()
    if not enabled(): raise frappe.PermissionError('Push is not enabled')
    response = requests.get(RELAY+'/api/method/notification_relay.api.get_config',
        params={'project_name':PROJECT},timeout=10,allow_redirects=False)
    response.raise_for_status(); data=response.json()
    if not isinstance(data.get('config'),dict) or not data.get('vapid_public_key'):
        raise RuntimeError('Browser push configuration is unavailable')
    return {'config':data['config'],'vapid_public_key':data['vapid_public_key'],'sdk_version':SDK}

@frappe.whitelist(methods=['POST'])
def subscribe(token):
    record=authenticated_browser()
    if not enabled(): raise frappe.PermissionError('Push is not enabled')
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9:_\-]{40,4096}',token):
        raise frappe.ValidationError('Invalid device token')
    init_state(); key=hashlib.sha256(token.encode()).hexdigest(); now=int(time.time())
    with sso.registry() as db:
        old=db.execute('SELECT p.*,b.revoked FROM push_devices p LEFT JOIN browsers b ON b.id=p.browser WHERE p.id=?',(key,)).fetchone()
        if old and old['user']!=frappe.session.user and old['enabled'] and not old['revoked']:
            raise frappe.PermissionError('Device already belongs to another active session')
        count=db.execute('SELECT COUNT(*) FROM push_devices WHERE browser=? AND enabled=1',(record['browser'],)).fetchone()[0]
        if count>=5 and not old:raise frappe.ValidationError('Too many devices for this browser')
    try:
        if old and old['user']!=frappe.session.user:
            _relay('token.remove',{'user_id':old['user'],'fcm_token':token})
        _relay('token.add',{'user_id':frappe.session.user,'fcm_token':token})
    except Exception:
        return {'success':False,'message':'Device registration failed. Please retry; no notification has been sent.'}
    with sso.registry() as db:
        db.execute('INSERT OR REPLACE INTO push_devices VALUES(?,?,?,?,?,?,?,?)',
            (key,frappe.local.site,frappe.session.user,record['browser'],_encrypt(token),1,now,now))
    return {'success':True}

@frappe.whitelist(methods=['POST'])
def unsubscribe():
    record=authenticated_browser();init_state()
    with sso.registry() as db:
        rows=db.execute('SELECT id FROM push_devices WHERE site=? AND user=? AND browser=?',
            (frappe.local.site,frappe.session.user,record['browser'])).fetchall()
        db.execute('UPDATE push_devices SET enabled=0,updated=? WHERE site=? AND user=? AND browser=?',
            (int(time.time()),frappe.local.site,frappe.session.user,record['browser']))
    for row in rows:remove_device(row['id'])
    return {'success':True}

def remove_device(device):
    init_state()
    with sso.registry() as db:row=db.execute('SELECT * FROM push_devices WHERE id=? AND site=?',(device,frappe.local.site)).fetchone()
    if not row or row['enabled']:return
    try:_relay('token.remove',{'user_id':row['user'],'fcm_token':_decrypt(row['token'])})
    except Exception:return  # Retain encrypted retry material; scheduler retries.
    with sso.registry() as db:db.execute('DELETE FROM push_devices WHERE id=? AND enabled=0',(device,))

def cleanup():
    if not enabled():return
    init_state()
    with sso.registry() as db:
        db.execute('''UPDATE push_devices SET enabled=0 WHERE site=? AND
            (browser IN(SELECT id FROM browsers WHERE revoked=1) OR NOT EXISTS(
              SELECT 1 FROM sessions s LEFT JOIN revoked_oidc r ON r.sid=s.oidc_sid
              WHERE s.site=push_devices.site AND s.browser=push_devices.browser AND r.sid IS NULL))''',(frappe.local.site,))
        rows=db.execute('SELECT id FROM push_devices WHERE site=? AND enabled=0',(frappe.local.site,)).fetchall()
    for row in rows:remove_device(row['id'])

def on_logout(login_manager):
    if not enabled() or frappe.session.user=='Guest':return
    try:
        record=sso.current_record()
        if not record:return
        init_state()
        with sso.registry() as db:
            db.execute('UPDATE push_devices SET enabled=0 WHERE site=? AND browser=?',(frappe.local.site,record['browser']))
        # Local eligibility is revoked immediately; relay removal is retried independently.
        frappe.enqueue('erpnext_drive_integrations.portal.push.cleanup',queue='short',enqueue_after_commit=True)
    except Exception:
        # Never prevent the native security logout. Revoked browser JOIN is also authoritative.
        pass

def notification_created(doc,method=None):
    if not enabled() or frappe.in_test or frappe.flags.in_install or frappe.flags.in_migrate:return
    frappe.enqueue('erpnext_drive_integrations.portal.push.deliver_notification',queue='short',
        name=doc.name,enqueue_after_commit=True)

def can_deliver(doc,user):
    if doc.for_user!=user or not frappe.db.get_value('User',user,'enabled'):return False
    if doc.document_type and doc.document_name:
        if not frappe.db.exists(doc.document_type,doc.document_name):return False
        if not frappe.has_permission(doc.document_type,'read',doc=doc.document_name,user=user):return False
        if doc.document_type=='Workflow Action':
            action=frappe.get_doc('Workflow Action',doc.document_name)
            if action.status!='Open':return False
            if not frappe.has_permission(action.reference_doctype,'read',doc=action.reference_name,user=user):return False
    return True

def deliver_notification(name):
    if not enabled() or not frappe.db.exists('Notification Log',name):return
    doc=frappe.get_doc('Notification Log',name);user=doc.for_user
    if not can_deliver(doc,user) or not _devices(user):return
    event='log:'+name;now=int(time.time())
    with sso.registry() as db:
        receipt=db.execute('SELECT status,updated FROM push_receipts WHERE site=? AND event=? AND user=?',
            (frappe.local.site,event,user)).fetchone()
        if receipt:return  # A timeout may still have delivered; do not duplicate automatically.
        db.execute('INSERT OR REPLACE INTO push_receipts VALUES(?,?,?,?,?)',(frappe.local.site,event,user,'attempt',now))
    try:
        _relay('send_notification.user',{'user_id':user,'title':'ERPNext notification',
            'body':'You have a new approval or notification. Open ERPNext to view it.',
            'data':json.dumps({'click_action':frappe.utils.get_url('/desk/notification-log/'+name),
                'notification_icon':'/assets/erpnext_drive_integrations/company-logo-approved-v6.svg','event_id':name})})
    except Exception:
        with sso.registry() as db:db.execute('UPDATE push_receipts SET status=? WHERE site=? AND event=? AND user=?',('unconfirmed',frappe.local.site,event,user))
        return
    with sso.registry() as db:db.execute('UPDATE push_receipts SET status=? WHERE site=? AND event=? AND user=?',('queued',frappe.local.site,event,user))

@frappe.whitelist(methods=['POST'])
def test_notification():
    authenticated_browser()
    if not enabled() or not _devices(frappe.session.user):raise frappe.ValidationError('Enable this browser first')
    key='cloud:push:test:'+hashlib.sha256(frappe.session.user.encode()).hexdigest()
    if not frappe.cache.set(key,'1',nx=True,ex=60):raise frappe.ValidationError('Please wait a minute before testing again')
    try:
        _relay('send_notification.user',{'user_id':frappe.session.user,'title':'ERPNext push test',
            'body':'Push notifications are connected.','data':json.dumps({'click_action':frappe.utils.get_url('/desk')})})
    except Exception:return {'success':False,'message':'Relay did not confirm the test. Please retry later.'}
    return {'success':True,'message':'Relay accepted the test; confirm that it arrived on your device.'}

def workflow_created(doc,method=None):
    if not enabled() or frappe.in_test or doc.status!='Open':return
    frappe.enqueue('erpnext_drive_integrations.portal.push.workflow_notifications',queue='short',name=doc.name,enqueue_after_commit=True)

def workflow_notifications(name):
    if not enabled() or not frappe.db.exists('Workflow Action',name):return
    from frappe.workflow.doctype.workflow_action.workflow_action import (
        get_workflow_name,get_doc_workflow_state,get_next_possible_transitions,get_users_next_action_data)
    action=frappe.get_doc('Workflow Action',name)
    if action.status!='Open':return
    reference=frappe.get_doc(action.reference_doctype,action.reference_name)
    if get_doc_workflow_state(reference)!=action.workflow_state:return
    workflow=get_workflow_name(reference.doctype)
    if not workflow:return
    recipients=get_users_next_action_data(get_next_possible_transitions(workflow,action.workflow_state,reference),reference)
    for user in recipients:
        if not frappe.db.get_value('User',user,'enabled'):continue
        key='uf-approval-'+hashlib.sha256((name+'|'+user).encode()).hexdigest()[:32]
        if frappe.db.exists('Notification Log',key):continue
        # Native role, transition condition and self-approval filtering above is authoritative.
        frappe.get_doc({'doctype':'Notification Log','for_user':user,'type':'Alert',
            'subject':'Approval required','document_type':'Workflow Action','document_name':name}).insert(
                ignore_permissions=True,set_name=key)

@frappe.whitelist(allow_guest=True,methods=['GET'])
def worker(config=None):
    from werkzeug.wrappers import Response
    source=Path(frappe.get_app_path('erpnext_drive_integrations','public','push-worker.js')).read_text()
    return Response(source,content_type='application/javascript; charset=utf-8',headers={
        'Service-Worker-Allowed':'/cloud-push/','Cache-Control':'no-cache','X-Content-Type-Options':'nosniff'})
