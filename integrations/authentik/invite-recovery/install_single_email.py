"""Convert only the two invitation flows to native single-email bearer links."""
from pathlib import Path
from django.core import serializers
from django.db import transaction
from authentik.flows.models import Flow, FlowStageBinding
from authentik.policies.models import PolicyBinding
from authentik.policies.expression.models import ExpressionPolicy
from authentik.stages.email.models import EmailStage
from authentik.stages.authenticator_webauthn.models import WebAuthnDevice

ROOT=Path('/data/cloud-invitations')
source=(ROOT/'native_recovery.py').read_text()
slugs=['cloud-first-time-enrollment','cloud-passkey-recovery-invitation']
flows=list(Flow.objects.filter(slug__in=slugs))
assert len(flows)==2
backup=ROOT/'single-email-before.json'
if not backup.exists():
 backup.write_text(serializers.serialize('json', [*FlowStageBinding.objects.filter(target__in=flows),*ExpressionPolicy.objects.filter(name__startswith='cloud-enrollment-'),*ExpressionPolicy.objects.filter(name__startswith='cloud-invite-')]))
 backup.chmod(0o600)

def expression(function):
 return source+"\ntry:\n    plan=request.context.get('flow_plan')\n    ctx=plan.context if plan else request.context\n    return "+function+"(ctx)\nexcept Exception:\n    return False\n"

with transaction.atomic():
 for flow in flows:
  FlowStageBinding.objects.filter(target=flow,stage_id__in=EmailStage.objects.values('pk')).delete()
 for name in ['cloud-enrollment-approved-first-time-user','cloud-enrollment-verified-first-time-user']:
  p=ExpressionPolicy.objects.get(name=name)
  p.expression=expression('single_email_enrollment');p.save(update_fields=['expression'])
  PolicyBinding.objects.filter(policy=p).update(negate=True,failure_result=True)
 for function in ['begin_recovery','verified_snapshot','commit_recovery','allowed_signin']:
  p=ExpressionPolicy.objects.get(name='cloud-invite-'+function)
  p.expression=expression(function);p.save(update_fields=['expression'])
 assert not FlowStageBinding.objects.filter(target__in=flows,stage_id__in=EmailStage.objects.values('pk')).exists()
 print('SINGLE_EMAIL_FLOWS_INSTALLED; EXISTING_KEYS',WebAuthnDevice.objects.count())
