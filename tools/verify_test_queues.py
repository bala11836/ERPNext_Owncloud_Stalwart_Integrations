#!/usr/bin/env python3
"""Run a timestamp-only job through each test ERP queue, without business writes."""
import argparse
import json
from pathlib import Path
import subprocess

from test_refresh_worker import private_profile


def verify(config):
    if config['tier']!='test':raise ValueError('Test only')
    code='''import os,json,time,uuid
os.chdir('/home/frappe/frappe-bench/sites')
import frappe
from frappe.utils.background_jobs import enqueue
frappe.init(SITE);frappe.connect()
try:
    assert os.environ.get('CLOUD_DEPLOYMENT_TIER')=='test' and frappe.conf.cloud_test_copy is True
    assert frappe.conf.disable_scheduler and frappe.conf.mute_emails
    result={}
    for queue in ['short','long']:
        job=enqueue('frappe.utils.now',queue=queue,job_id='test-queue-'+uuid.uuid4().hex,timeout=30)
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            status=str(job.get_status(refresh=True)).lower()
            if 'finished' in status or 'failed' in status:break
            time.sleep(1)
        if 'finished' not in status:raise RuntimeError('Native test queue did not complete: '+queue)
        result[queue]='finished'
    print('QUEUE_ACCEPTANCE='+json.dumps(result))
finally:frappe.destroy()
'''.replace('SITE',repr(config['site']))
    completed=subprocess.run(['docker','exec',config['containers']['erp_backend'],
        '/home/frappe/frappe-bench/env/bin/python','-c',code],capture_output=True,text=True,check=True)
    result=json.loads(completed.stdout.split('QUEUE_ACCEPTANCE=',1)[1].strip())
    receipt=Path(config['state_root'])/'queue-acceptance.private.json'
    receipt.write_text(json.dumps(result,indent=2)+'\n');receipt.chmod(0o600)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True)
    print(json.dumps(verify(private_profile(p.parse_args().config))))
