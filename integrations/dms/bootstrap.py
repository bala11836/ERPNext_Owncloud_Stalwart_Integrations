"""Django-shell bootstrap for approved DMS roles and private worker enrollment.

Not an HTTP view. The host-side operator passes an explicit enrollment profile.
Tokens returned here must be captured privately, never displayed or committed.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework.authtoken.models import Token


def configure(profile):
    group,_=Group.objects.get_or_create(name=profile.get('group','office'))
    editable={'document','tag','correspondent','documenttype','savedview','uisettings'}
    readable=editable|{'storagepath','customfield'}
    permissions=[p for p in Permission.objects.filter(content_type__app_label='documents')
        if (p.codename.startswith('view_') and p.content_type.model in readable)
        or (p.codename.startswith(('add_','change_')) and p.content_type.model in editable)]
    group.permissions.set(permissions)
    result=[]
    User=get_user_model()
    if profile.get('tier')=='test':
        # Copied production passwords/tokens are never test credentials.
        Token.objects.all().delete()
        for existing in User.objects.all():
            existing.set_unusable_password();existing.save(update_fields=['password'])
    for enrollment in profile['users']:
        email=enrollment['email'].casefold()
        user=User.objects.filter(email__iexact=email).first()
        if user is None:
            user=User.objects.create_user(username=email,email=email)
            user.set_unusable_password();user.save()
        if profile.get('tier')=='test':
            user.set_unusable_password();user.save(update_fields=['password'])
        if email==profile.get('administrator_email','').casefold():
            user.is_staff=True;user.is_superuser=True;user.save(update_fields=['is_staff','is_superuser'])
        user.groups.add(group)
        token,_=Token.objects.get_or_create(user=user)
        result.append({'email':email,'paperless_user_id':user.pk,'paperless_token':token.key,'office_group_id':group.pk})
    return result
