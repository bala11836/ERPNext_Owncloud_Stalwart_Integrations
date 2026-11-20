#!/usr/bin/env python3
"""Render complete workspace ingress for a controller's existing Traefik proxy.

Publish only to the administrator-selected proxy directory. The proxy must join
the workspace network. Existing SSO can be remote; test never hosts a copy of it.
"""
import argparse
import json
from pathlib import Path
import re
import yaml


def prepare(source, profile):
    source=Path(source)
    hosts=profile['hosts']
    prefix=profile.get('ingress_prefix','workspace')
    if not re.fullmatch(r'[a-z0-9-]+',prefix):raise ValueError('Invalid ingress prefix')
    routers,services,middlewares={},{},{}
    def service(name,url):
        services[name]={'loadBalancer':{'servers':[{'url':url}]}}
    def route(name,host,target,priority=200,path=None,middleware=()):
        rule='Host(`'+host+'`)'+(' && '+path if path else '')
        routers[name]={'rule':rule,'entryPoints':['https'],'priority':50000+priority,
            'service':target,'tls':{'certResolver':profile.get('cert_resolver','letsencrypt')}}
        # Behind a TCP pass-through relay HTTP/3 (UDP) cannot reach this host:
        # tell browsers to forget any HTTP/3 alternative they remembered.
        middleware=list(middleware)+(['alt-svc-clear'] if profile.get('relay_target') else [])
        if middleware:routers[name]['middlewares']=list(middleware)
    service('erp','http://erp-frontend:8080')
    service('drive','http://drive-ocis:9200')
    service('office','http://editor-onlyoffice:80')
    service('mail','http://mail-webmail:3000')
    service('jmap','http://mail-stalwart:8080')
    service('dms','http://dms-paperless:8000')
    service('website','http://website-web:8080')
    sso_url='https://'+hosts['sso'] if profile.get('existing_sso',True) else 'http://identity-server:9000'
    service('sso',sso_url)
    # Remote SSO must expose a test-host outpost route. Preserve the browser's
    # Host for that route; TLS still validates the server URL's SSO hostname.
    middlewares['identity-clean']={'headers':{'customRequestHeaders':{
        key:'' for key in ['X-authentik-username','X-authentik-email','X-authentik-groups',
            'X-authentik-uid','X-authentik-jwt','X-authentik-meta-jwks']}}}
    middlewares['sso-auth']={'forwardAuth':{'address':profile.get('forward_auth_url',sso_url+'/outpost.goauthentik.io/auth/traefik'),
        'trustForwardHeader':True,'authResponseHeaders':['X-authentik-username','X-authentik-groups',
                                                      'X-authentik-email','X-authentik-uid']}}
    middlewares['frame']={'headers':{'customResponseHeaders':{'X-Frame-Options':''}}}
    middlewares['alt-svc-clear']={'headers':{'customResponseHeaders':{'Alt-Svc':'clear'}}}
    middlewares['dms-frame']={'headers':{'customResponseHeaders':{'X-Frame-Options':'',
        'Content-Security-Policy':"frame-ancestors 'self' https://"+hosts['erp']}}}
    middlewares['private-admin']={'ipAllowList':{'sourceRange':profile.get('admin_networks',
                                                        ['100.64.0.0/10','127.0.0.1/32'])}}
    route('erp',hosts['erp'],'erp',middleware=['identity-clean','sso-auth'])
    if profile.get('website_front_page'):
        # P47: the company front page answers the exact front path of the host and
        # its own assets under /front/; every other path keeps going to the portal
        # and the ERP unchanged.
        route('website-front',hosts['erp'],'website',priority=5000,path='(Path(`/`) || PathPrefix(`/front/`))')
    route('outpost',hosts['erp'],'sso',300,'PathPrefix(`/outpost.goauthentik.io/`)')
    # These app endpoints perform their own signed OIDC / CSRF / token checks.
    # Only the exact public bootstrap/static endpoints bypass the outpost.
    method='/api/method/erpnext_drive_integrations.portal.'
    public=['Path(`/login`)','Path(`/signed-out`)','PathPrefix(`/assets/`)']
    public += ['Path(`'+method+name+'`)' for name in ['sso.start_signin','sso.finish_logout',
                'sso.session_status','sso.backchannel','push.worker']]
    route('erp-bootstrap',hosts['erp'],'erp',250,'('+' || '.join(public)+')',middleware=['identity-clean'])
    route('drive',hosts['drive'],'drive',middleware=['frame'])
    route('office',hosts['office'],'office',middleware=['frame'])
    route('office-admin',hosts['office'],'office',400,
          '(PathPrefix(`/browser/dist/admin`) || PathPrefix(`/cool/adminws`))',middleware=['private-admin'])
    route('mail',hosts['mail'],'mail',middleware=['frame'])
    route('mail-jmap',hosts['mail'],'jmap',300,
          '(PathPrefix(`/jmap`) || PathPrefix(`/dav`) || PathPrefix(`/.well-known/`))')
    route('mail-admin',hosts['mail'],'mail',400,
          '(PathPrefix(`/admin`) || PathPrefix(`/api/admin`))',middleware=['private-admin'])
    # Native webmail deliberately publishes a filtered read-only feature
    # policy here. Blocking it with the admin UI also hides organisation gates.
    # Writes and every other administration route remain private.
    route('mail-public-policy',hosts['mail'],'mail',450,
          '(Path(`/api/admin/policy`) && Method(`GET`))')
    route('dms',hosts['dms'],'dms',middleware=['dms-frame'])
    middlewares['office-home']={'redirectRegex':{'regex':'^https://'+re.escape(hosts['office'])+'/?$',
        'replacement':'https://'+hosts['drive']+'/files/spaces/personal','permanent':False}}
    route('office-home',hosts['office'],'noop@internal',1000,'Path(`/`)',middleware=['office-home'])
    # Public vendor response methods remain narrowed by the application's guest
    # gate, random expiring links and first-device binding. No general guest API.
    response=yaml.safe_load((source/'deployment/config/proxy/onboarding-response.yaml').read_text())
    replacements={'erp.example.com':hosts['erp'],'respond.example.com':hosts['respond']}
    def replace(value):
        if isinstance(value,dict):return {k:replace(v) for k,v in value.items()}
        if isinstance(value,list):return [replace(v) for v in value]
        if isinstance(value,str):
            for a,b in replacements.items():value=value.replace(a,b)
        return value
    response=replace(response['http'])
    response['middlewares']['onboarding-response-help']['redirectRegex'].update({
        'regex':'^https://'+re.escape(hosts['respond'])+'/?$',
        'replacement':'https://'+hosts['respond']+'/link-help'})
    for name,value in response.get('routers',{}).items():
        value['priority']=50000+value.get('priority',300)
        if value['service']!='noop@internal':value['service']='erp'
        routers[name]=value
    middlewares.update(response.get('middlewares',{}))
    if not profile.get('existing_sso',True):route('sso',hosts['sso'],'sso')
    # Prefix every local reference, allowing this file alongside other projects.
    result={'http':{'routers':{},'services':{},'middlewares':{}}}
    for name,value in routers.items():
        value['service']=prefix+'-'+value['service'] if '@' not in value['service'] else value['service']
        value['middlewares']=[prefix+'-'+m if '@' not in m else m for m in value.get('middlewares',[])]
        result['http']['routers'][prefix+'-'+name]=value
    for category,items in [('services',services),('middlewares',middlewares)]:
        result['http'][category]={prefix+'-'+k:v for k,v in items.items()}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--profile',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    data=prepare(args.source,json.loads(Path(args.profile).read_text()))
    Path(args.output).write_text(yaml.safe_dump(data,sort_keys=False))
