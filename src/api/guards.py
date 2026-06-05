from flask import current_app, has_request_context

from src.tools.settings import Settings

DARK_MODE_ACTIVE_KEY = 'DARK_MODE_ACTIVE'


def is_dark_mode_active() -> bool:
    """True when route rotation is active (config.yaml and/or in-memory session flag)."""
    if has_request_context():
        if current_app.config.get(DARK_MODE_ACTIVE_KEY):
            return True
        if current_app.config.get('TESTING'):
            return False

    try:
        settings = Settings()
    except FileNotFoundError:
        return False
    return bool(settings.get('settings', {}).get('dark_mode', False))


def is_dark_mode_enabled() -> bool:
    """Alias for rotation-active checks; response masking is a separate future pass."""
    return is_dark_mode_active()
