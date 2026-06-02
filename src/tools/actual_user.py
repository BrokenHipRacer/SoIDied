from pathlib import Path

from src.db.extensions import db
from src.models.user import User
from src.tools.settings import Settings

DEFAULT_CREDENTIALS_PATH = 'startup/actual_user.md'
DEFAULT_API_STARTUP_PATH = 'startup/api.txt'

DOCUMENTED_API_ROUTES = [
    'PUT /api/v1/checkin',
    'GET /api/v1/checkin/status',
    'GET /api/v1/utils/api',
    'GET /api/v1/utils/ping',
    'PUT /api/v1/utils/unlock',
    'PUT /api/v1/utils/debug',
    'GET /api/v1/utils/ducky',
]


def credentials_file_path(settings: Settings | None = None) -> Path:
    settings = settings or Settings()
    configured = settings.get('settings', {}).get(
        'actual_user_credentials_file',
        DEFAULT_CREDENTIALS_PATH,
    )
    return Path(configured)


def api_startup_file_path(settings: Settings | None = None) -> Path:
    settings = settings or Settings()
    configured = settings.get('settings', {}).get(
        'api_startup_file',
        DEFAULT_API_STARTUP_PATH,
    )
    return Path(configured)


def get_actual_user() -> User | None:
    return User.query.filter_by(is_actual_user=True).first()


def _demote_extra_actual_users() -> None:
    actual_users = User.query.filter_by(is_actual_user=True).order_by(User.id).all()
    if len(actual_users) <= 1:
        return
    for duplicate in actual_users[1:]:
        duplicate.is_actual_user = False
    db.session.commit()


def ensure_actual_user() -> User:
    _demote_extra_actual_users()
    user = get_actual_user()
    if user is not None:
        return user

    user = User(is_actual_user=True)
    db.session.add(user)
    db.session.commit()
    return user


def format_credentials_markdown(user: User, settings: Settings | None = None) -> str:
    settings = settings or Settings()
    app_name = settings.get('app', {}).get('name', 'SoIDied')
    return (
        f'# {app_name} — Actual User Credentials\n\n'
        'Use these values in API requests as `id` and `token`.\n\n'
        f'- **id**: `{user.id}`\n'
        f'- **token**: `{user.access_token}`\n'
    )


def format_api_startup_file(user: User, settings: Settings | None = None) -> str:
    settings = settings or Settings()
    routes = '\n'.join(f'- {route}' for route in DOCUMENTED_API_ROUTES)
    return (
        f'{format_credentials_markdown(user, settings)}\n'
        '## Documented API routes\n\n'
        f'{routes}\n'
    )


def write_actual_user_credentials_file(
    user: User,
    settings: Settings | None = None,
) -> Path:
    settings = settings or Settings()
    path = credentials_file_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_credentials_markdown(user, settings), encoding='utf-8')
    return path


def write_api_startup_file(user: User, settings: Settings | None = None) -> Path:
    settings = settings or Settings()
    path = api_startup_file_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_api_startup_file(user, settings), encoding='utf-8')
    return path


def read_actual_user_credentials_file(settings: Settings | None = None) -> str | None:
    path = credentials_file_path(settings)
    if not path.is_file():
        return None
    return path.read_text(encoding='utf-8')


def read_api_startup_file(settings: Settings | None = None) -> str | None:
    path = api_startup_file_path(settings)
    if not path.is_file():
        return None
    return path.read_text(encoding='utf-8')


def initialize_actual_user(settings: Settings | None = None) -> User:
    """Ensure the actual user exists and refresh on-disk startup files."""
    settings = settings or Settings()
    user = ensure_actual_user()
    write_actual_user_credentials_file(user, settings)
    write_api_startup_file(user, settings)
    return user
