"""Transport security (Option 1): serve the dev server over HTTPS with a self-signed cert.

This is config-driven via the ``tls`` block in ``config.yaml``. When enabled, a self-signed
certificate is generated at startup (if missing) and handed to Flask's ``ssl_context``.
The certificate fingerprint is printed so it can be pinned client-side, which closes the
man-in-the-middle gap that plaintext-over-HTTP leaves open.

``cryptography`` is imported lazily so this module loads even where the package is absent
and TLS is disabled.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

DEFAULT_CERT_FILE = 'certs/cert.pem'
DEFAULT_KEY_FILE = 'certs/key.pem'
DEFAULT_COMMON_NAME = 'localhost'
DEFAULT_VALID_DAYS = 825
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 5000
LOOPBACK_HOSTS = {'127.0.0.1', '::1', 'localhost', ''}


def _is_loopback_host(host: str) -> bool:
    """True when the bind address only accepts connections from this machine."""
    return str(host).strip().lower() in LOOPBACK_HOSTS


def _tls(settings) -> dict:
    return settings.get('tls', {}) or {}


def is_tls_enabled(settings) -> bool:
    return bool(_tls(settings).get('enabled', False))


def cert_paths(settings) -> tuple[str, str]:
    tls = _tls(settings)
    return (
        str(tls.get('cert_file', DEFAULT_CERT_FILE)),
        str(tls.get('key_file', DEFAULT_KEY_FILE)),
    )


def _restrict_key_permissions(key_path: str | Path) -> None:
    """Lock the private key to the current user across operating systems.

    POSIX: chmod 0600. Windows: drop inherited ACEs and grant the current user only,
    via the built-in ``icacls`` (no extra dependency). Never raises — a key that cannot
    be locked is reported but must not crash startup.
    """
    key_path = str(key_path)

    if os.name == 'posix':
        try:
            os.chmod(key_path, 0o600)
        except OSError as exc:
            print(f'[TLS] could not chmod key file {key_path}: {exc}')
        return

    if os.name == 'nt':
        user = os.environ.get('USERNAME') or os.environ.get('USER')
        if not user:
            print(f'[TLS] key file {key_path} left with default ACLs (no USERNAME env).')
            return
        try:
            subprocess.run(
                ['icacls', key_path, '/inheritance:r', '/grant:r', f'{user}:F'],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            detail = getattr(exc, 'stderr', '') or exc
            print(f'[TLS] could not restrict key file {key_path} via icacls: {detail}')
        return

    print(f'[TLS] unknown OS ({os.name}); key file {key_path} permissions not restricted.')


def generate_self_signed_cert(
    cert_path: str | Path,
    key_path: str | Path,
    common_name: str = DEFAULT_COMMON_NAME,
    valid_days: int = DEFAULT_VALID_DAYS,
) -> tuple[str, str]:
    """Create a 2048-bit RSA self-signed cert (with localhost/127.0.0.1 SANs) and write PEMs."""
    import ipaddress
    from datetime import datetime, timedelta, timezone

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    cert_path = Path(cert_path)
    key_path = Path(key_path)
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])

    dns_names = {common_name, 'localhost'}
    san_entries: list = [x509.DNSName(value) for value in sorted(dns_names)]
    for ip in ('127.0.0.1', '::1'):
        san_entries.append(x509.IPAddress(ipaddress.ip_address(ip)))

    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=valid_days))
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    _restrict_key_permissions(key_path)

    return (str(cert_path), str(key_path))


def certificate_fingerprint(cert_path: str | Path) -> str:
    """Uppercase, colon-separated SHA-256 fingerprint suitable for client-side pinning."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes

    certificate = x509.load_pem_x509_certificate(Path(cert_path).read_bytes())
    digest = certificate.fingerprint(hashes.SHA256())
    return ':'.join(f'{byte:02X}' for byte in digest)


def ensure_certificate(settings) -> tuple[str, str] | None:
    """Return (cert, key) paths, generating a self-signed pair if enabled and missing."""
    if not is_tls_enabled(settings):
        return None

    cert_path, key_path = cert_paths(settings)
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return (cert_path, key_path)

    tls = _tls(settings)
    if not tls.get('auto_generate', True):
        return None

    return generate_self_signed_cert(
        cert_path,
        key_path,
        common_name=str(tls.get('common_name', DEFAULT_COMMON_NAME)),
        valid_days=int(tls.get('valid_days', DEFAULT_VALID_DAYS)),
    )


def provision_tls(settings) -> tuple[str, str] | None:
    """Startup hook: ensure a certificate exists and print the pinning fingerprint."""
    if not is_tls_enabled(settings):
        return None

    result = ensure_certificate(settings)
    if result is None:
        print('[TLS] enabled but no certificate available '
              '(auto_generate is off and cert/key files are missing).')
        return None

    cert_path, key_path = result
    print('=' * 60)
    print('SoIDied TLS enabled (self-signed certificate).')
    print(f'  cert: {cert_path}')
    print(f'  key:  {key_path}')
    print('  SHA-256 fingerprint (pin this client-side):')
    print(f'    {certificate_fingerprint(cert_path)}')
    print('=' * 60)
    return result


def resolve_run_options(settings) -> dict:
    """Build kwargs for ``app.run``. Adds ssl_context/host/port only when TLS is usable.

    ``debug`` follows ``settings.debug`` (config-driven, not hardcoded) so the Werkzeug
    debugger/reloader is off by default — important once this is exposed over TLS.
    """
    debug = bool((settings.get('settings', {}) or {}).get('debug', False))
    options: dict = {'debug': debug}
    if not is_tls_enabled(settings):
        return options

    cert_path, key_path = cert_paths(settings)
    if os.path.exists(cert_path) and os.path.exists(key_path):
        tls = _tls(settings)
        host = str(tls.get('host', DEFAULT_HOST))
        options['ssl_context'] = (cert_path, key_path)
        options['host'] = host
        options['port'] = int(tls.get('port', DEFAULT_PORT))
        if debug and not _is_loopback_host(host):
            print(f'[TLS] SECURITY: forcing debug off — refusing to run the Werkzeug '
                  f'debugger (remote code execution) on a network-exposed bind ({host}). '
                  f'debug=true is only honored on loopback addresses.')
            options['debug'] = False
    else:
        print('[TLS] enabled but certificate/key missing; serving plain HTTP. '
              'Start via bootstrap (python api.py) or set tls.auto_generate: true.')
    return options


def apply_hsts(settings, response, is_secure: bool):
    """Set HSTS on secure responses when configured. Returns the response for chaining."""
    if is_secure and is_tls_enabled(settings) and _tls(settings).get('hsts', True):
        response.headers.setdefault(
            'Strict-Transport-Security', 'max-age=31536000; includeSubDomains'
        )
    return response
