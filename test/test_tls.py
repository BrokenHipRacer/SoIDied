import os

import pytest

from src.tools import tls


def _settings(tls_config: dict) -> dict:
    """A plain dict is a drop-in for Settings here: both expose .get('tls', {})."""
    return {'tls': tls_config}


def test_disabled_returns_plain_run_options():
    options = tls.resolve_run_options(_settings({'enabled': False}))

    assert options == {'debug': False}
    assert 'ssl_context' not in options


def test_ensure_certificate_disabled_is_noop(tmp_path):
    cert = tmp_path / 'cert.pem'
    key = tmp_path / 'key.pem'

    result = tls.ensure_certificate(
        _settings({'enabled': False, 'cert_file': str(cert), 'key_file': str(key)})
    )

    assert result is None
    assert not cert.exists()
    assert not key.exists()


def test_ensure_certificate_generates_when_missing(tmp_path):
    cert = tmp_path / 'certs' / 'cert.pem'
    key = tmp_path / 'certs' / 'key.pem'
    settings = _settings({'enabled': True, 'cert_file': str(cert), 'key_file': str(key)})

    result = tls.ensure_certificate(settings)

    assert result == (str(cert), str(key))
    assert cert.exists()
    assert key.exists()
    assert 'BEGIN CERTIFICATE' in cert.read_text()
    assert 'PRIVATE KEY' in key.read_text()


def test_ensure_certificate_does_not_regenerate_existing(tmp_path):
    cert = tmp_path / 'cert.pem'
    key = tmp_path / 'key.pem'
    settings = _settings({'enabled': True, 'cert_file': str(cert), 'key_file': str(key)})

    tls.ensure_certificate(settings)
    original = cert.read_bytes()

    tls.ensure_certificate(settings)

    assert cert.read_bytes() == original


def test_auto_generate_off_skips_creation(tmp_path):
    cert = tmp_path / 'cert.pem'
    key = tmp_path / 'key.pem'
    settings = _settings(
        {'enabled': True, 'auto_generate': False, 'cert_file': str(cert), 'key_file': str(key)}
    )

    result = tls.ensure_certificate(settings)

    assert result is None
    assert not cert.exists()


def test_resolve_run_options_includes_ssl_context_when_cert_present(tmp_path):
    cert = tmp_path / 'cert.pem'
    key = tmp_path / 'key.pem'
    settings = _settings(
        {
            'enabled': True,
            'cert_file': str(cert),
            'key_file': str(key),
            'host': '0.0.0.0',
            'port': 8443,
        }
    )
    tls.ensure_certificate(settings)

    options = tls.resolve_run_options(settings)

    assert options['ssl_context'] == (str(cert), str(key))
    assert options['host'] == '0.0.0.0'
    assert options['port'] == 8443


def test_resolve_run_options_falls_back_when_cert_missing(tmp_path):
    settings = _settings(
        {
            'enabled': True,
            'auto_generate': False,
            'cert_file': str(tmp_path / 'missing.pem'),
            'key_file': str(tmp_path / 'missing.key'),
        }
    )

    options = tls.resolve_run_options(settings)

    assert 'ssl_context' not in options


def test_generated_cert_is_a_server_leaf_not_a_ca(tmp_path):
    from cryptography import x509
    from cryptography.x509.oid import ExtendedKeyUsageOID

    cert = tmp_path / 'cert.pem'
    key = tmp_path / 'key.pem'
    tls.ensure_certificate(
        _settings({'enabled': True, 'cert_file': str(cert), 'key_file': str(key)})
    )

    certificate = x509.load_pem_x509_certificate(cert.read_bytes())

    basic = certificate.extensions.get_extension_for_class(x509.BasicConstraints).value
    assert basic.ca is False

    eku = certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    assert ExtendedKeyUsageOID.SERVER_AUTH in eku


def test_run_options_debug_follows_config(tmp_path):
    cert = tmp_path / 'cert.pem'
    key = tmp_path / 'key.pem'
    base = {'enabled': True, 'cert_file': str(cert), 'key_file': str(key)}
    tls.ensure_certificate(_settings(base))

    debug_on = tls.resolve_run_options({'tls': base, 'settings': {'debug': True}})
    debug_off = tls.resolve_run_options({'tls': base, 'settings': {'debug': False}})

    assert debug_on['debug'] is True
    assert debug_off['debug'] is False


def test_run_options_debug_defaults_off_when_unset():
    options = tls.resolve_run_options(_settings({'enabled': False}))

    assert options['debug'] is False


def test_run_options_debug_forced_off_on_nonloopback_bind(tmp_path):
    cert = tmp_path / 'cert.pem'
    key = tmp_path / 'key.pem'
    base = {'enabled': True, 'cert_file': str(cert), 'key_file': str(key), 'host': '0.0.0.0'}
    tls.ensure_certificate(_settings(base))

    options = tls.resolve_run_options({'tls': base, 'settings': {'debug': True}})

    assert options['host'] == '0.0.0.0'
    assert options['debug'] is False


def test_run_options_debug_kept_on_loopback_tls(tmp_path):
    cert = tmp_path / 'cert.pem'
    key = tmp_path / 'key.pem'
    base = {'enabled': True, 'cert_file': str(cert), 'key_file': str(key), 'host': '127.0.0.1'}
    tls.ensure_certificate(_settings(base))

    options = tls.resolve_run_options({'tls': base, 'settings': {'debug': True}})

    assert options['debug'] is True


def test_certificate_fingerprint_format(tmp_path):
    cert = tmp_path / 'cert.pem'
    key = tmp_path / 'key.pem'
    settings = _settings({'enabled': True, 'cert_file': str(cert), 'key_file': str(key)})
    tls.ensure_certificate(settings)

    fingerprint = tls.certificate_fingerprint(str(cert))

    parts = fingerprint.split(':')
    assert len(parts) == 32  # SHA-256 = 32 bytes
    assert all(len(part) == 2 for part in parts)
    assert fingerprint == fingerprint.upper()


@pytest.mark.skipif(os.name != 'posix', reason='POSIX file mode only')
def test_key_file_is_chmod_600_on_posix(tmp_path):
    cert = tmp_path / 'cert.pem'
    key = tmp_path / 'key.pem'
    tls.ensure_certificate(
        _settings({'enabled': True, 'cert_file': str(cert), 'key_file': str(key)})
    )

    mode = key.stat().st_mode & 0o777
    assert mode == 0o600


def test_restrict_key_permissions_uses_icacls_on_windows(tmp_path, monkeypatch):
    key = tmp_path / 'key.pem'
    key.write_text('dummy')
    calls = []

    monkeypatch.setattr(tls.os, 'name', 'nt')
    monkeypatch.setenv('USERNAME', 'tester')

    def fake_run(cmd, **kwargs):
        calls.append(cmd)

        class _R:
            returncode = 0
        return _R()

    monkeypatch.setattr(tls.subprocess, 'run', fake_run)

    tls._restrict_key_permissions(str(key))

    assert calls, 'expected icacls to be invoked on Windows'
    cmd = calls[0]
    assert cmd[0] == 'icacls'
    assert str(key) in cmd
    assert '/inheritance:r' in cmd
    assert 'tester:F' in cmd


def test_restrict_key_permissions_never_raises_on_icacls_failure(tmp_path, monkeypatch):
    key = tmp_path / 'key.pem'
    key.write_text('dummy')

    monkeypatch.setattr(tls.os, 'name', 'nt')
    monkeypatch.setenv('USERNAME', 'tester')

    def boom(cmd, **kwargs):
        raise tls.subprocess.CalledProcessError(1, cmd, stderr='denied')

    monkeypatch.setattr(tls.subprocess, 'run', boom)

    tls._restrict_key_permissions(str(key))  # must not raise


class _FakeHeaders(dict):
    def setdefault(self, key, value):
        return dict.setdefault(self, key, value)


class _FakeResponse:
    def __init__(self):
        self.headers = _FakeHeaders()


def test_apply_hsts_sets_header_on_secure_request():
    response = _FakeResponse()

    tls.apply_hsts(_settings({'enabled': True, 'hsts': True}), response, is_secure=True)

    assert 'Strict-Transport-Security' in response.headers


def test_apply_hsts_skips_insecure_request():
    response = _FakeResponse()

    tls.apply_hsts(_settings({'enabled': True, 'hsts': True}), response, is_secure=False)

    assert 'Strict-Transport-Security' not in response.headers


def test_apply_hsts_skips_when_disabled():
    response = _FakeResponse()

    tls.apply_hsts(_settings({'enabled': False, 'hsts': True}), response, is_secure=True)

    assert 'Strict-Transport-Security' not in response.headers
