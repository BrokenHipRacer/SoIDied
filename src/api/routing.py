from __future__ import annotations

import os

from flask import Flask
from flask_restful import Api

from src.api.route_registry import (
    DARKMODE_CANONICAL_PATH,
    DARKMODE_ENDPOINT,
    ROTATABLE_ROUTES,
    RouteSpec,
    canonical_route_lines,
)
from src.tools.dark_mode_routes import RotatedRoute, build_rotation
from src.tools.settings import Settings

RESTFUL_API_EXTENSION_KEY = 'soidied_restful_api'

_active_rotation: tuple[RotatedRoute, ...] | None = None
_routes_use_rotation = False


def bind_restful_api(app: Flask, api: Api) -> None:
    app.extensions[RESTFUL_API_EXTENSION_KEY] = api


def get_restful_api(app: Flask) -> Api:
    api = app.extensions.get(RESTFUL_API_EXTENSION_KEY)
    if api is None:
        raise RuntimeError('Flask-RESTful Api is not bound on this application')
    return api


def reset_routing_state() -> None:
    """Clear rotation state (tests only). Does not change Flask URL rules."""
    global _active_rotation, _routes_use_rotation
    _active_rotation = None
    _routes_use_rotation = False


def get_active_rotation() -> tuple[RotatedRoute, ...] | None:
    return _active_rotation


def routes_use_rotation() -> bool:
    return _routes_use_rotation


def get_active_route_lines() -> list[str]:
    if _routes_use_rotation and _active_rotation is not None:
        lines: list[str] = []
        for entry in _active_rotation:
            lines.extend(entry.route_lines())
        return lines
    return canonical_route_lines()


def is_dark_mode_config_enabled() -> bool:
    try:
        settings = Settings()
    except FileNotFoundError:
        return False
    return bool(settings.get('settings', {}).get('dark_mode', False))


def _allow_route_mutation(app: Flask) -> None:
    """Flask 3 blocks add_url_rule after the first request; rotation runs mid-lifecycle."""
    app._got_first_request = False


def _rebuild_url_map(app: Flask) -> None:
    """Rebuild the routing matcher; Werkzeug's update() only re-sorts, not removes stale paths."""
    from werkzeug.routing.matcher import StateMachineMatcher

    url_map = app.url_map
    matcher = StateMachineMatcher(url_map.merge_slashes)
    for rule in url_map._rules:
        if not rule.build_only:
            matcher.add(rule)
    url_map._matcher = matcher
    url_map._remap = False


def _remove_url_rule(app: Flask, rule) -> None:
    app.url_map._rules.remove(rule)
    if rule.endpoint in app.url_map._rules_by_endpoint:
        endpoint_rules = app.url_map._rules_by_endpoint[rule.endpoint]
        app.url_map._rules_by_endpoint[rule.endpoint] = [
            existing for existing in endpoint_rules if existing is not rule
        ]
        if not app.url_map._rules_by_endpoint[rule.endpoint]:
            del app.url_map._rules_by_endpoint[rule.endpoint]
    app.url_map._remap = True


def _remove_endpoint(app: Flask, api: Api, endpoint: str) -> None:
    app.view_functions.pop(endpoint, None)
    api.resources = [item for item in api.resources if item[2] != endpoint]

    rules_to_remove = [rule for rule in app.url_map.iter_rules() if rule.endpoint == endpoint]
    for rule in rules_to_remove:
        _remove_url_rule(app, rule)


def _remove_canonical_paths(app: Flask) -> None:
    canonical_paths = {spec.canonical_path for spec in ROTATABLE_ROUTES}
    stale_rules = [rule for rule in app.url_map.iter_rules() if rule.rule in canonical_paths]
    for rule in stale_rules:
        _remove_url_rule(app, rule)
        app.view_functions.pop(rule.endpoint, None)
    _rebuild_url_map(app)


def _register_spec(app: Flask, api: Api, spec: RouteSpec, path: str) -> None:
    _allow_route_mutation(app)
    _remove_endpoint(app, api, spec.endpoint)
    api.add_resource(spec.resource, path, endpoint=spec.endpoint)
    _rebuild_url_map(app)


def _register_darkmode_endpoint(app: Flask, api: Api) -> None:
    from src.api.dark_mode import DarkMode

    _remove_endpoint(app, api, DARKMODE_ENDPOINT)
    api.add_resource(DarkMode, DARKMODE_CANONICAL_PATH, endpoint=DARKMODE_ENDPOINT)


def register_canonical_routes(app: Flask, api: Api) -> None:
    global _active_rotation, _routes_use_rotation
    _active_rotation = None
    _routes_use_rotation = False

    for spec in ROTATABLE_ROUTES:
        _register_spec(app, api, spec, spec.canonical_path)
    _register_darkmode_endpoint(app, api)
    _rebuild_url_map(app)


def register_rotated_routes(app: Flask, api: Api, rotation: tuple[RotatedRoute, ...]) -> None:
    global _active_rotation, _routes_use_rotation
    _active_rotation = rotation
    _routes_use_rotation = True

    for entry in rotation:
        _register_spec(app, api, entry.spec, entry.path)
    _remove_canonical_paths(app)
    _register_darkmode_endpoint(app, api)
    _rebuild_url_map(app)


def apply_route_rotation(app: Flask, api: Api) -> tuple[RotatedRoute, ...]:
    rotation = build_rotation()
    register_rotated_routes(app, api, rotation)
    return rotation


def should_apply_config_rotation() -> bool:
    if os.environ.get('SOIDIED_SKIP_BOOTSTRAP') == '1':
        return False
    if os.environ.get('PYTEST_CURRENT_TEST'):
        return False
    return is_dark_mode_config_enabled()


def init_api_routes(app: Flask, api: Api) -> None:
    if should_apply_config_rotation():
        apply_route_rotation(app, api)
    else:
        register_canonical_routes(app, api)


def refresh_startup_api_file(app: Flask) -> None:
    if app.config.get('TESTING') or os.environ.get('SOIDIED_SKIP_BOOTSTRAP') == '1':
        return

    from src.tools.actual_user import ensure_actual_user, write_api_startup_file

    with app.app_context():
        user = ensure_actual_user()
        write_api_startup_file(user)


def activate_dark_mode_session(app: Flask, api: Api) -> tuple[RotatedRoute, ...]:
    from src.api.guards import DARK_MODE_ACTIVE_KEY

    app.config[DARK_MODE_ACTIVE_KEY] = True
    rotation = apply_route_rotation(app, api)
    refresh_startup_api_file(app)
    return rotation
