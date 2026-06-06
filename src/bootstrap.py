import os

from flask import Flask

from src.db.schema import create_schema
from src.tools.actual_user import initialize_actual_user
from src.tools.message_files import prepare_message_upload_folder

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
    finally:
        if previous is None:
            os.environ.pop(INTERNAL_ENV, None)
        else:
            os.environ[INTERNAL_ENV] = previous
