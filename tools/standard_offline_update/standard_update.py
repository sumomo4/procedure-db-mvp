"""Offline update for the specific Standard 7ecf683 -> 4c4fe7b release."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone


BUNDLE = Path(__file__).resolve().parent
SERVICES = ('standard-web', 'standard-api', 'standard-db')
APPS = SERVICES[:2]
FILES = ('docker-compose.yml', 'docker-compose.standard.yml', 'docker-compose.standard.server.yml')
OVERRIDE = 'docker-compose.standard.update.yml'
STATE = '.standard-update-state.json'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(args, **kwargs):
    result = subprocess.run([str(arg) for arg in args], check=True, **kwargs)
    return result


def output(args, **kwargs):
    return run(args, stdout=subprocess.PIPE, text=True, **kwargs).stdout.strip()


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=True) + '\n', encoding='ascii')
    os.chmod(temp, 0o600)
    temp.replace(path)


def checksums(root):
    root = Path(root).resolve()
    lines = (root / 'SHA256SUMS').read_text(encoding='ascii').splitlines()
    require(lines, 'Empty checksum manifest')
    for line in lines:
        expected, relative = line.split('  ', 1)
        path = (root / relative).resolve()
        require(root in path.parents and path.is_file(), f'Invalid checksum path: {relative}')
        require(digest(path) == expected, f'Checksum mismatch: {relative}')


def save_checksums(root):
    lines = []
    for path in sorted(root.rglob('*')):
        if path.is_file() and path.name != 'SHA256SUMS':
            lines.append(f'{digest(path)}  {path.relative_to(root).as_posix()}')
    (root / 'SHA256SUMS').write_text('\n'.join(lines) + '\n', encoding='ascii')


def version_fields(path):
    return dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)


def image_ids(image):
    return {image['id'], image.get('config_id', image['id'])}


def validate_config(config, install, ports_expected=(80, 8000, 5432)):
    require(set(config['services']) == set(SERVICES), 'Only the three Standard services are supported')
    for service in APPS:
        binds = {v['target']: v for v in config['services'][service].get('volumes', [])}
        for target, relative in (('/app/storage', 'storage/standard'), ('/app/logs', 'logs/standard')):
            require(target in binds and binds[target]['type'] == 'bind', f'Missing {service} bind: {target}')
            require(Path(binds[target]['source']).resolve() == install / relative, f'Unexpected bind: {service} {target}')
    for service, expected in zip(SERVICES, ports_expected):
        ports = config['services'][service].get('ports', [])
        require(len(ports) == 1 and int(ports[0]['published']) == expected, f'Unexpected port: {service}')
        if service != 'standard-web':
            require(ports[0].get('host_ip') == '127.0.0.1', f'{service} must be localhost-only')
    require(str(config['services']['standard-api']['environment'].get('AUTH_COOKIE_SECURE')).lower() == 'false', 'This updater is for HTTP80 only')


class Deployment:
    def __init__(self, args):
        self.args = args
        self.release = read_json(BUNDLE / 'RELEASE.json')
        user = os.environ.get('SUDO_USER') or os.environ.get('TARGET_USER') or pwd.getpwuid(os.getuid()).pw_name
        self.home = Path(pwd.getpwnam(user).pw_dir)
        self.install = Path(args.install_dir or self.home / 'procedure-db-mvp').resolve()
        self.project = args.project
        require(re.fullmatch(r'[a-z0-9][a-z0-9_-]+', self.project), 'Invalid project name')
        require(self.install.is_dir() and self.install != Path('/'), 'Installation directory not found')
        for name in FILES:
            require((self.install / name).is_file(), f'Missing installed file: {name}')
        require((self.install / 'storage/standard').is_dir(), 'Existing storage is missing')
        self.base = ['docker', 'compose', '-p', self.project, '--project-directory', str(self.install)]
        for name in FILES:
            self.base += ['-f', str(self.install / name)]
        self.containers = {}
        self.backup = None

    def compose(self, *args):
        command = list(self.base)
        if (self.install / OVERRIDE).exists():
            command += ['-f', str(self.install / OVERRIDE)]
        return command + list(args)

    def inspect(self):
        config = json.loads(output(self.compose('config', '--format', 'json')))
        validate_config(config, self.install, (self.args.web_port, self.args.api_port, self.args.db_port))
        for service in SERVICES:
            ids = output(['docker', 'ps', '-aq', '--filter', f'label=com.docker.compose.project={self.project}', '--filter', f'label=com.docker.compose.service={service}']).splitlines()
            require(len(ids) == 1, f'Expected one existing container: {service}')
            info = json.loads(output(['docker', 'inspect', ids[0]]))[0]
            labels = info['Config']['Labels']
            require(Path(labels['com.docker.compose.project.working_dir']).resolve() == self.install, 'Container belongs to a different installation directory')
            expected_files = set(self.base[index + 1] for index, value in enumerate(self.base) if value == '-f')
            if (self.install / OVERRIDE).exists():
                expected_files.add(str(self.install / OVERRIDE))
            actual_files = set(labels['com.docker.compose.project.config_files'].split(','))
            require(actual_files <= expected_files, 'Container uses an unsupported Compose override')
            target_port = {'standard-web': 80, 'standard-api': 8000, 'standard-db': 5432}[service]
            host_port = {'standard-web': self.args.web_port, 'standard-api': self.args.api_port, 'standard-db': self.args.db_port}[service]
            bindings = info['HostConfig']['PortBindings'].get(f'{target_port}/tcp', [])
            require(len(bindings) == 1 and int(bindings[0]['HostPort']) == host_port, f'Live port differs from configuration: {service}')
            if service != 'standard-web':
                require(bindings[0]['HostIp'] == '127.0.0.1', f'Live {service} port must be localhost-only')
            if service in APPS:
                mounts = {m['Destination']: m for m in info['Mounts']}
                require(mounts['/app/storage']['Source'] == str(self.install / 'storage/standard'), 'Live storage mount differs from installed configuration')
            self.containers[service] = info
        db = self.containers['standard-db']
        require(db['State']['Running'], 'Existing database must be running')
        volumes = [m for m in db['Mounts'] if m['Destination'] == '/var/lib/postgresql/data']
        require(len(volumes) == 1 and volumes[0]['Type'] == 'volume', 'Expected existing named DB volume')
        self.db_volume = volumes[0]['Name']
        self.db = db['Id']
        require(self.sql('SHOW server_version_num;').startswith('16'), 'PostgreSQL 16 is required')

    def sql(self, statement):
        return output(['docker', 'exec', self.db, 'psql', '-X', '-v', 'ON_ERROR_STOP=1', '-U', 'standard_user', '-d', 'mvp_standard', '-Atc', statement])

    def sql_file(self, path, capture=False):
        with Path(path).open('rb') as stream:
            result = run(['docker', 'exec', '-i', self.db, 'psql', '-X', '-v', 'ON_ERROR_STOP=1', '-U', 'standard_user', '-d', 'mvp_standard', '-At', '-f', '-'], stdin=stream, stdout=subprocess.PIPE if capture else None)
        return result.stdout if capture else None

    def baseline(self):
        fields = version_fields(self.install / '.deploy-version')
        require(fields.get('BUNDLE_VERSION') == self.release['supported_base'], 'Not the supported base release; stop and review the version')
        require(fields.get('DEPLOY_SHA') == self.release['supported_base_commit'], 'Base commit mismatch')
        for service in APPS:
            require(self.containers[service]['Image'] in self.release['baseline_images'][service], f'Unexpected running image: {service}')
            require(self.containers[service]['State']['Running'], f'{service} is not running; recover before updating')
        require(self.sql("SELECT to_regclass('proc.module_similarity_signatures') IS NOT NULL;") == 't', 'Expected similarity table is missing')

    def stop(self):
        run(self.compose('stop', '-t', '60', *APPS))

    def fingerprint(self, path):
        Path(path).write_bytes(self.sql_file(BUNDLE / 'snapshot.sql', capture=True))

    def backup_data(self, path):
        print(f'Backing up database and storage: {path}', flush=True)
        with (path / 'database.dump').open('wb') as stream:
            run(['docker', 'exec', self.db, 'pg_dump', '-U', 'standard_user', '-d', 'mvp_standard', '-Fc', '--no-owner', '--no-acl'], stdout=stream)
        with (path / 'database.dump').open('rb') as stream:
            run(['docker', 'exec', '-i', self.db, 'pg_restore', '--list'], stdin=stream, stdout=subprocess.DEVNULL)
        run(['tar', '-czf', path / 'storage.tar.gz', '-C', self.install, 'storage/standard'])
        self.fingerprint(path / 'business-data.jsonl')

    def create_backup(self):
        root = Path(self.args.backup_root or self.home / 'procedure-db-backups/standard').resolve()
        require(root != self.install and self.install not in root.parents, 'Backup must be outside the installation directory')
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        self.backup = root / f'{stamp}-{self.release["version"]}'
        self.backup.mkdir(mode=0o700)
        metadata = {'version': self.release['version'], 'install': str(self.install), 'project': self.project, 'db_id': self.db, 'db_image': self.containers['standard-db']['Image'], 'db_volume': self.db_volume, 'images': {}}
        for service in APPS:
            tag = f'procedure-db-standard-rollback:{stamp.lower()}-{service}'
            image_id = self.containers[service]['Image']
            run(['docker', 'image', 'tag', image_id, tag])
            metadata['images'][service] = {'name': tag, 'id': image_id}
        print(f'Saving old application images: {self.backup}', flush=True)
        run(['docker', 'image', 'save', '-o', self.backup / 'old-images.tar', *[v['name'] for v in metadata['images'].values()]])
        self.backup_data(self.backup)
        configuration = list(FILES) + ['infra/env/standard.env.example', '.deploy-version']
        configuration += [name for name in (OVERRIDE, STATE, '.env') if (self.install / name).exists()]
        run(['tar', '-czf', self.backup / 'configuration.tar.gz', '-C', self.install, *configuration])
        shutil.copy2(self.install / '.deploy-version', self.backup / 'previous-deploy-version')
        write_json(self.backup / 'BACKUP.json', metadata)
        save_checksums(self.backup)
        checksums(self.backup)
        (self.backup / 'READY').touch(mode=0o600)
        print(f'BACKUP_READY={self.backup}', flush=True)
        return metadata

    def disk_check(self):
        database_size = int(self.sql("SELECT pg_database_size('mvp_standard');"))
        storage_size = sum(p.stat().st_size for p in (self.install / 'storage/standard').rglob('*') if p.is_file() and not p.is_symlink())
        needed = database_size * 3 + storage_size * 2 + (BUNDLE / 'payload/standard-images.tar').stat().st_size * 4 + 512 * 1024 ** 2
        backup_root = Path(self.args.backup_root or self.home / 'procedure-db-backups/standard')
        ancestor = backup_root
        while not ancestor.exists():
            ancestor = ancestor.parent
        require(shutil.disk_usage(ancestor).free > needed, f'Insufficient backup disk space; need at least {needed // (1024 ** 2)} MiB')
        print(f'Backup space estimate: {needed // (1024 ** 2)} MiB. Also check Docker data-root free space.', flush=True)

    def image_override(self, images):
        for service, image in images.items():
            actual = json.loads(output(['docker', 'image', 'inspect', image['name']]))[0]
            require(actual['Id'] in image_ids(image), f'Loaded image ID mismatch: {service}')
            require(actual['Os'] == 'linux' and actual['Architecture'] == 'amd64', 'Image platform mismatch')
        write_json(self.install / OVERRIDE, {'services': {service: {'image': image['name']} for service, image in images.items()}})

    def start_and_check(self, before):
        run(self.compose('up', '-d', '--no-build', '--pull', 'never', '--no-deps', '--wait', '--wait-timeout', '180', 'standard-api'))
        after = before.with_name('business-data-after.jsonl')
        self.fingerprint(after)
        require(before.read_bytes() == after.read_bytes(), 'Business data changed unexpectedly; WebUI remains stopped')
        run(self.compose('up', '-d', '--no-build', '--pull', 'never', '--no-deps', 'standard-web'))
        self.health()

    def health(self):
        self.inspect()
        for service in SERVICES:
            state = self.containers[service]['State']
            require(state['Running'], f'{service} is not running')
            if service != 'standard-web':
                require(state.get('Health', {}).get('Status') == 'healthy', f'{service} is not healthy')
        # Probe through Nginx inside the container without depending on DNS or host networking.
        for path in ('/api/v1/health', '/api/v1/health/db', '/modules'):
            for attempt in range(30):
                result = subprocess.run(['docker', 'exec', self.containers['standard-web']['Id'], 'wget', '-q', '-O', '/dev/null', f'http://127.0.0.1{path}'])
                if result.returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError(f'Web health probe failed: {path}')

    def confirm(self, word, message):
        if not self.args.yes:
            print(message, flush=True)
            require(input(f'Type {word} to continue: ').strip() == word, 'Cancelled; no application changes made')

    def update(self):
        self.inspect()
        self.baseline()
        self.disk_check()
        if self.args.check:
            print('PREFLIGHT_OK: No containers or business data changed.')
            return
        self.confirm('UPDATE', f'Update {self.project} at {self.install}. All users must stop work until verification completes.')
        changed = False
        try:
            self.stop()
            metadata = self.create_backup()
            run(['docker', 'image', 'load', '-i', BUNDLE / 'payload/standard-images.tar'])
            changed = True
            self.sql_file(BUNDLE / 'migrate.sql')
            self.image_override(self.release['images'])
            self.start_and_check(self.backup / 'business-data.jsonl')
            require(self.db == metadata['db_id'] and self.db_volume == metadata['db_volume'], 'DB container or volume changed')
            source_changed = str(bool(self.release.get('source_has_uncommitted_changes', False))).lower()
            text = f'DEPLOY_SHA={self.release["commit"]}\nBUNDLE_VERSION={self.release["version"]}\nSOURCE_HAS_UNCOMMITTED_CHANGES={source_changed}\n'
            (self.install / '.deploy-version').write_text(text, encoding='ascii')
            write_json(self.install / STATE, {'version': self.release['version'], 'status': 'updated', 'backup': str(self.backup)})
            print('UPDATE_OK: Verify login, administrator access, existing data and Excel output before resuming use.')
        except BaseException:
            if changed:
                self.stop()
                print(f'UPDATE_STOPPED: Keep use suspended. Run rollback_standard.sh --backup {self.backup}', file=sys.stderr)
            else:
                run(['docker', 'start', self.containers['standard-api']['Id'], self.containers['standard-web']['Id']])
                print('Update not applied. Original application containers restarted.', file=sys.stderr)
            raise

    def verify(self):
        self.health()
        fields = version_fields(self.install / '.deploy-version')
        state = read_json(self.install / STATE)
        backup = Path(state['backup'])
        metadata = read_json(backup / 'BACKUP.json')
        require(self.db == metadata['db_id'] and self.db_volume == metadata['db_volume'], 'DB identity differs from the update backup')
        expected = self.release['images'] if state['status'] == 'updated' else metadata['images']
        expected_version = self.release['version'] if state['status'] == 'updated' else self.release['supported_base']
        require(fields.get('BUNDLE_VERSION') == expected_version, 'Deployment version mismatch')
        for service in APPS:
            require(self.containers[service]['Image'] in image_ids(expected[service]), f'Unexpected image: {service}')
        print(f'VERIFY_OK: {expected_version}; DB volume retained: {self.db_volume}')
        print('Manual checks still required: login/roles, module/source/case data, images and Excel export.')

    def rollback(self):
        require(self.args.backup, '--backup is required')
        backup = Path(self.args.backup).resolve()
        require((backup / 'READY').is_file(), 'Backup is incomplete; do not attempt rollback')
        checksums(backup)
        metadata = read_json(backup / 'BACKUP.json')
        require(metadata['version'] == self.release['version'], 'Backup is from another release')
        require(metadata['install'] == str(self.install) and metadata['project'] == self.project, 'Backup is from another installation')
        self.inspect()
        require(metadata['db_id'] == self.db and metadata['db_volume'] == self.db_volume, 'DB changed since backup; manual recovery review required')
        for service in APPS:
            require(self.containers[service]['Image'] in image_ids(metadata['images'][service]) | image_ids(self.release['images'][service]), 'Unexpected application version; refusing rollback')
        self.confirm('ROLLBACK', 'Restore old application images. Keep current business data; rebuild only the derived similarity cache.')
        self.stop()
        try:
            recovery = backup.parent / f'pre-rollback-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}'
            recovery.mkdir(mode=0o700)
            self.backup_data(recovery)
            save_checksums(recovery)
            run(['docker', 'image', 'load', '-i', backup / 'old-images.tar'])
            self.sql_file(BUNDLE / 'rollback_cache.sql')
            self.image_override(metadata['images'])
            self.start_and_check(recovery / 'business-data.jsonl')
            shutil.copy2(backup / 'previous-deploy-version', self.install / '.deploy-version')
            write_json(self.install / STATE, {'version': self.release['version'], 'status': 'rolled_back', 'backup': str(backup)})
            print('ROLLBACK_OK: Business data retained. Verify the old application before resuming use.')
        except BaseException:
            self.stop()
            print('ROLLBACK_STOPPED: Keep use suspended and preserve all backups.', file=sys.stderr)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('update', 'verify', 'rollback'))
    parser.add_argument('--install-dir')
    parser.add_argument('--project', default='procedure-db-mvp')
    parser.add_argument('--web-port', type=int, default=80)
    parser.add_argument('--api-port', type=int, default=8000)
    parser.add_argument('--db-port', type=int, default=5432)
    parser.add_argument('--backup-root')
    parser.add_argument('--backup')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--yes', action='store_true')
    args = parser.parse_args()
    require(os.geteuid() == 0, 'Run with sudo')
    os.umask(0o077)
    checksums(BUNDLE)
    deployment = Deployment(args)
    with (deployment.install / '.standard-update.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        getattr(deployment, args.action)()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
