import os

from flask import Flask

from src.db.schema import create_schema
from src.tools.actual_user import initialize_actual_user
from src.tools.message_files import prepare_message_upload_folder
from src.tools.settings import Settings
from src.tools.tls import provision_tls

INTERNAL_ENV = 'SOIDIED_INTERNAL'


def should_bootstrap() -> bool:
    if os.environ.get('SOIDIED_SKIP_BOOTSTRAP') == '1':
        return False
    if os.environ.get('PYTEST_CURRENT_TEST'):
        return False
    return True


def _print_actual_user_credentials(user) -> None:
    print('=' * 60)
    print('SoIDied actual user credentials (use as `id` / `token`):')
    print(f'  id:    {user.id}')
    print(f'  token: {user.access_token}')
    print('=' * 60)


def _provision_tls_quietly() -> None:
    """Generate the self-signed cert at startup if TLS is enabled; never block bootstrap."""
    try:
        provision_tls(Settings())
    except FileNotFoundError:
        pass
    except Exception as exc:  # noqa: BLE001 — TLS provisioning must not crash startup
        print(f'[TLS] certificate provisioning skipped: {exc}')


def _start_check_in_tracker(app: Flask) -> None:
    """Launch the background check-in time tracker; never block bootstrap on failure."""
    try:
        from src.tools.check_in_scheduler import start_check_in_scheduler

        start_check_in_scheduler(app)
    except Exception as exc:  # noqa: BLE001 — scheduler startup must not crash bootstrap
        print(f'[scheduler] check-in tracker not started: {exc}')


def bootstrap_app(app: Flask) -> None:
    """Create schema, ensure actual user exists, and write startup files."""
    if app.config.get('TESTING') or not should_bootstrap():
        return

    previous = os.environ.get(INTERNAL_ENV)
    os.environ[INTERNAL_ENV] = '1'
    try:
        with app.app_context():
            prepare_message_upload_folder()
            create_schema()
            user = initialize_actual_user()
            _print_actual_user_credentials(user)
        _provision_tls_quietly()
        _start_check_in_tracker(app)
    finally:
        if previous is None:
            os.environ.pop(INTERNAL_ENV, None)
        else:
            os.environ[INTERNAL_ENV] = previous
