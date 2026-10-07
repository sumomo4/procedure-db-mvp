import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location('updater', Path(__file__).resolve().parents[1] / 'standard_update.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


def config():
    services = {}
    for name, port in zip(updater.SERVICES, (80, 8000, 5432)):
        services[name] = {'ports': [{'published': str(port), 'host_ip': '0.0.0.0' if name == 'standard-web' else '127.0.0.1'}]}
        if name in updater.APPS:
            services[name]['volumes'] = [
                {'type': 'bind', 'target': '/app/storage', 'source': '/appdir/storage/standard'},
                {'type': 'bind', 'target': '/app/logs', 'source': '/appdir/logs/standard'},
            ]
    services['standard-api']['environment'] = {'AUTH_COOKIE_SECURE': 'false'}
    return {'services': services}


def test_production_config():
    updater.validate_config(config(), Path('/appdir'))


@pytest.mark.parametrize('problem', ['lab', 'storage', 'public_db', 'https', 'wrong_port'])
def test_unsafe_config_rejected(problem):
    value = config()
    if problem == 'lab':
        value['services']['lab-api'] = {}
    elif problem == 'storage':
        value['services']['standard-api']['volumes'][0]['source'] = '/different/storage'
    elif problem == 'public_db':
        value['services']['standard-db']['ports'][0]['host_ip'] = '0.0.0.0'
    elif problem == 'https':
        value['services']['standard-api']['environment']['AUTH_COOKIE_SECURE'] = 'true'
    else:
        value['services']['standard-web']['ports'][0]['published'] = '3000'
    with pytest.raises(RuntimeError):
        updater.validate_config(value, Path('/appdir'))


def test_engine_image_id_forms():
    assert updater.image_ids({'id': 'sha256:index', 'config_id': 'sha256:config'}) == {'sha256:index', 'sha256:config'}
    assert updater.image_ids({'id': 'sha256:captured'}) == {'sha256:captured'}


def test_checksums_accept_and_reject_tampering(tmp_path):
    (tmp_path / 'file').write_text('original')
    updater.save_checksums(tmp_path)
    updater.checksums(tmp_path)
    (tmp_path / 'file').write_text('changed')
    with pytest.raises(RuntimeError, match='mismatch'):
        updater.checksums(tmp_path)


def test_checksum_path_escape_rejected(tmp_path):
    (tmp_path / 'SHA256SUMS').write_text('0' * 64 + '  ../outside\n')
    with pytest.raises(RuntimeError, match='Invalid checksum path'):
        updater.checksums(tmp_path)


def test_empty_manifest_rejected(tmp_path):
    (tmp_path / 'SHA256SUMS').write_text('')
    with pytest.raises(RuntimeError, match='Empty'):
        updater.checksums(tmp_path)


def test_baseline_wrong_version_does_not_stop(tmp_path):
    (tmp_path / '.deploy-version').write_text('BUNDLE_VERSION=unknown\nDEPLOY_SHA=unknown\n')
    deployment = object.__new__(updater.Deployment)
    deployment.install = tmp_path
    deployment.release = {'supported_base': 'known'}
    with pytest.raises(RuntimeError, match='supported base'):
        deployment.baseline()


def test_rollback_without_complete_backup_rejected(tmp_path):
    deployment = object.__new__(updater.Deployment)
    deployment.args = Mock(backup=str(tmp_path))
    deployment.stop = Mock()
    with pytest.raises(RuntimeError, match='incomplete'):
        deployment.rollback()
    deployment.stop.assert_not_called()


def test_cancel_confirmation(monkeypatch):
    deployment = object.__new__(updater.Deployment)
    deployment.args = Mock(yes=False)
    monkeypatch.setattr('builtins.input', lambda prompt: 'cancel')
    with pytest.raises(RuntimeError, match='Cancelled'):
        deployment.confirm('UPDATE', 'Test')


@pytest.mark.parametrize('failure_stage', ['backup', 'migration'])
def test_failure_keeps_safe_application_state(monkeypatch, tmp_path, failure_stage):
    deployment = object.__new__(updater.Deployment)
    deployment.args = Mock(check=False)
    deployment.project = 'test-project'
    deployment.install = tmp_path
    deployment.backup = tmp_path / 'backup'
    deployment.inspect = Mock()
    deployment.baseline = Mock()
    deployment.disk_check = Mock()
    deployment.confirm = Mock()
    deployment.stop = Mock()
    deployment.create_backup = Mock(return_value={})
    deployment.sql_file = Mock()
    deployment.containers = {'standard-api': {'Id': 'old-api'}, 'standard-web': {'Id': 'old-web'}}
    command = Mock()
    monkeypatch.setattr(updater, 'run', command)
    if failure_stage == 'backup':
        deployment.create_backup.side_effect = RuntimeError('backup failed')
    else:
        deployment.sql_file.side_effect = RuntimeError('migration failed')
    with pytest.raises(RuntimeError):
        deployment.update()
    if failure_stage == 'backup':
        command.assert_called_once_with(['docker', 'start', 'old-api', 'old-web'])
    else:
        assert deployment.stop.call_count == 2
        assert all(call.args[0][:2] != ['docker', 'start'] for call in command.call_args_list)
