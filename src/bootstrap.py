import os

from flask import Flask

from src.db.schema import create_schema
from src.tools.actual_user import initialize_actual_user

INTERNAL_ENV = 'SOIDIED_INTERNAL'


def should_bootstrap() -> bool:
    if os.environ.get('SOIDIED_SKIP_BOOTSTRAP') == '1':
        return False
    if os.environ.get('PYTEST_CURRENT_TEST'):
        return False
    return True


def bootstrap_app(app: Flask) -> None:
    """Create schema, ensure actual user exists, and write startup files."""
    if app.config.get('TESTING') or not should_bootstrap():
        return

    previous = os.environ.get(INTERNAL_ENV)
    os.environ[INTERNAL_ENV] = '1'
    try:
        with app.app_context():
            create_schema()
            initialize_actual_user()
    finally:
        if previous is None:
            os.environ.pop(INTERNAL_ENV, None)
        else:
            os.environ[INTERNAL_ENV] = previous
