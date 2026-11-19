from authentik.core.models import Application
from authentik.policies.expression.models import ExpressionPolicy
from authentik.policies.models import PolicyBinding
app=Application.objects.get(slug='cloud-invite-user')
policy=ExpressionPolicy.objects.get(name='cloud-invite-admin-only')
assert PolicyBinding.objects.filter(policy=policy).count()==1
assert PolicyBinding.objects.filter(policy=policy,target=app).exists()
policy.expression='return False  # Moved to Directory in Authentik administration.'
policy.save(update_fields=['expression'])
assert app.provider_id is None
app.meta_launch_url=''
app.save(update_fields=['meta_launch_url'])
assert app.get_launch_url() is None
print('INVITATION_TILE_HIDDEN; BACKEND_PERMISSIONS_UNCHANGED')
