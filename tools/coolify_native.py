#!/usr/bin/env python3
"""Register a prepared Compose service through local Coolify's native models.

Run as the controller host's administrator. No API token is created or exported.
This only creates/updates the explicitly named service; it never deletes records.
Prepared Compose and rendered controller files contain private runtime values.
"""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import yaml


PHP = r'''
require '/var/www/html/vendor/autoload.php';
$app=require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$p=json_decode(base64_decode('PAYLOAD'),true,512,JSON_THROW_ON_ERROR);
$servers=App\Models\Server::where('team_id',$p['team_id']);
if($p['server_uuid'])$servers->where('uuid',$p['server_uuid']);
if($servers->count()!==1)throw new Exception('Select one controller server explicitly');
$server=$servers->first();
$destinations=$server->destinations();
if($p['destination_uuid'])$destinations=$destinations->where('uuid',$p['destination_uuid']);
elseif($destinations->count()>1)$destinations=$destinations->where('network','coolify');
if($destinations->count()!==1)throw new Exception('Select one destination explicitly');
$dest=$destinations->first();
$project=App\Models\Project::firstOrCreate(['team_id'=>$p['team_id'],'name'=>$p['project']],
    ['description'=>'Repository-built workspace deployment']);
if($project->wasRecentlyCreated && $p['environment']!=='production'){
    $initial=$project->environments()->first();
    $initial->name=$p['environment'];$initial->save();
}
$environment=$project->environments()->firstOrCreate(['name'=>$p['environment']],['uuid'=>new_public_id()]);
$service=App\Models\Service::firstOrNew(['environment_id'=>$environment->id,'name'=>$p['name']]);
$isNew=!$service->exists;
$service->docker_compose_raw=$p['compose'];
$service->server_id=$server->id;
$service->destination_id=$dest->id;
$service->destination_type=$dest->getMorphClass();
$service->connect_to_docker_network=false;
$service->redact_all_env_values_in_logs=true;
$service->description='Source commit '.$p['commit'];
$service->save();
$service->parse(isNew:$isNew);
$service->refresh();
echo 'RESULT_B64='.base64_encode(json_encode(['uuid'=>$service->uuid,
    'project_uuid'=>$project->uuid,'compose'=>$service->docker_compose],JSON_THROW_ON_ERROR));
'''


def register(compose, project, environment, name, commit, team_id=1,
             server_uuid=None, destination_uuid=None):
    spec=yaml.safe_load(Path(compose).read_text())
    # Coolify's native parser serializes an empty ports sequence as null and an
    # empty volumes sequence as a mapping ({}), which current Compose rejects.
    # An omitted field has the same semantics.
    for service in spec.get('services',{}).values():
        for field in ('ports','volumes'):
            if service.get(field)==[]:service.pop(field)
    payload = dict(compose=yaml.safe_dump(spec,sort_keys=False), project=project,
        environment=environment, name=name, commit=commit, team_id=team_id,
        server_uuid=server_uuid, destination_uuid=destination_uuid)
    # Encoding structured input avoids interpolating names/configuration as PHP.
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    process = subprocess.run(['docker', 'exec', '-i', 'coolify', 'php'],
        input='<?php\n' + PHP.replace('PAYLOAD', encoded), text=True, capture_output=True)
    if process.returncode or 'RESULT_B64=' not in process.stdout:
        raise RuntimeError('Coolify registration failed; inspect controller logs privately')
    result = json.loads(base64.b64decode(process.stdout.split('RESULT_B64=', 1)[1].strip()))
    # Native model parsing expects its service network to have been provisioned
    # by the deployment job. Keep that per-service network private; applications
    # explicitly join the separate workspace network where required.
    network=subprocess.run(['docker','network','inspect',result['uuid']],
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if network.returncode:
        subprocess.run(['docker','network','create','--internal',result['uuid']],
                       check=True,stdout=subprocess.DEVNULL)
    directory = Path('/data/coolify/services') / result['uuid']
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    (directory / 'docker-compose.yml').write_text(result.pop('compose'))
    (directory / 'docker-compose.yml').chmod(0o600)
    env_file = directory / '.env'
    if not env_file.exists():
        env_file.touch(mode=0o600)
    subprocess.run(['docker', 'compose', '-p', result['uuid'], '-f',
                    str(directory / 'docker-compose.yml'), '--env-file', str(env_file),
                    'config', '--quiet'], check=True, stdout=subprocess.DEVNULL)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for option in ['compose', 'project', 'environment', 'name', 'commit']:
        parser.add_argument('--' + option, required=True)
    parser.add_argument('--team-id', type=int, default=1)
    parser.add_argument('--server-uuid')
    parser.add_argument('--destination-uuid')
    parser.add_argument('--receipt', required=True)
    args = vars(parser.parse_args())
    receipt = Path(args.pop('receipt'))
    result = register(**args)
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    receipt.chmod(0o600)
    print('Registered', args['name'], result['uuid'])
