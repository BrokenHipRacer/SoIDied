from flask import current_app, has_request_context

from src.tools.settings import Settings


def is_dark_mode_enabled() -> bool:
    if has_request_context() and current_app.config.get('TESTING'):
        return False

    settings = Settings()
    return bool(settings.get('settings', {}).get('dark_mode', False))


def dark_mode_not_found():
    return {'message': 'Not found'}, 404
