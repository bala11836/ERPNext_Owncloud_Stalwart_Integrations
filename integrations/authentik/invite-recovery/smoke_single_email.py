from datetime import timedelta
from uuid import uuid4
from django.db import transaction
from django.utils.timezone import now
from django.test import Client
from authentik.core.models import User,Group
from authentik.flows.models import Flow
from authentik.stages.invitation.models import Invitation

with transaction.atomic():
 admin=User.objects.get(username='alex@example.com')
 for slug in ['cloud-first-time-enrollment','cloud-passkey-recovery-invitation']:
  user=User.objects.create(username='single-email-smoke-'+uuid4().hex,email=uuid4().hex+'@example.invalid',type='internal')
  user.ak_groups.add(Group.objects.get(name='Workspace Users'))
  invite=Invitation.objects.create(name='single-email-smoke-'+uuid4().hex,flow=Flow.objects.get(slug=slug),created_by=admin,single_use=True,expiring=True,expires=now()+timedelta(hours=1),fixed_data={'email':user.email,'user_id':user.pk})
  result=Client().get('/api/v3/flows/executor/'+slug+'/',{'query':'itoken='+str(invite.invite_uuid)}, follow=True, secure=True, HTTP_HOST='sso.example.com', HTTP_ACCEPT='application/json')
  print('EXECUTOR_HTTP',result.status_code,result.get('Content-Type'),result.get('Location',''))
  data=result.json()
  component=data.get('component','')
  print('EXECUTOR_SMOKE',slug,result.status_code,component)
  assert result.status_code==200 and component=='ak-stage-authenticator-webauthn', data.get('type')
  assert not Invitation.objects.filter(pk=invite.pk).exists()
 transaction.set_rollback(True)
print('BOTH_NATIVE_EXECUTORS_REACH_PASSKEY_WITHOUT_SECOND_EMAIL')
