import pytest
from flask import Flask
from flask_restful import Api

from src.api.route_registry import (
    DARKMODE_CANONICAL_PATH,
    ROTATABLE_ROUTES,
    canonical_route_lines,
)
from src.api.routing import (
    activate_dark_mode_session,
    bind_restful_api,
    get_active_route_lines,
    init_api_routes,
    register_canonical_routes,
    reset_routing_state,
    routes_use_rotation,
)
from src.db.extensions import db
from src.models.user import User
from src.tools.actual_user import write_api_startup_file
from src.tools.dark_mode_routes import build_rotation

CHECKIN_URL = '/api/v1/checkin'
CHECKIN_STATUS_URL = '/api/v1/checkin/status'


@pytest.fixture
def routing_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    db.init_app(app)
    api = Api(app)
    bind_restful_api(app, api)
    register_canonical_routes(app, api)

    with app.app_context():
        db.create_all()
        yield app, api
        db.session.remove()
        db.drop_all()


def _auth_body(user: User) -> dict:
    return {'id': user.id, 'token': user.access_token}


@pytest.fixture
def main_user(routing_app):
    app, _api = routing_app
    with app.app_context():
        user = User(is_actual_user=True)
        db.session.add(user)
        db.session.commit()
        yield user


def test_build_rotation_uses_unique_cryptographic_paths():
    rotation = build_rotation()
    paths = [entry.path for entry in rotation]
    assert len(paths) == len(set(paths))
    for path in paths:
        assert path.startswith('/api/v1/')
        assert path not in {spec.canonical_path for spec in ROTATABLE_ROUTES}


def test_init_api_routes_rotates_when_config_dark_mode(monkeypatch):
    monkeypatch.setattr('src.api.routing.should_apply_config_rotation', lambda: True)
    fresh = Flask(__name__)
    fresh.config['TESTING'] = True
    fresh_api = Api(fresh)
    bind_restful_api(fresh, fresh_api)
    try:
        init_api_routes(fresh, fresh_api)

        assert routes_use_rotation()
        rules = {rule.rule for rule in fresh.url_map.iter_rules()}
        for spec in ROTATABLE_ROUTES:
            assert spec.canonical_path not in rules
    finally:
        reset_routing_state()


def test_activate_dark_mode_session_rotates_routes(routing_app, main_user):
    app, api = routing_app
    client = app.test_client()
    rotation = activate_dark_mode_session(app, api)

    assert routes_use_rotation()
    assert len(rotation) == len(ROTATABLE_ROUTES)

    checkin_path = next(entry.path for entry in rotation if entry.spec.endpoint == 'checkin')
    status_path = next(
        entry.path for entry in rotation if entry.spec.endpoint == 'checkin_status'
    )

    assert client.put(CHECKIN_URL, json=_auth_body(main_user)).status_code == 404
    assert client.get(CHECKIN_STATUS_URL, json=_auth_body(main_user)).status_code == 404

    response = client.put(checkin_path, json=_auth_body(main_user))
    assert response.status_code == 200

    client.put(checkin_path, json=_auth_body(main_user))
    status_response = client.get(status_path, json=_auth_body(main_user))
    assert status_response.status_code == 200
    assert status_response.get_json()['Status'] == 'OK'


def test_darkmode_endpoint_enables_session_rotation(routing_app, main_user, tmp_path, monkeypatch):
    app, _api = routing_app
    api_file = tmp_path / 'api.txt'
    monkeypatch.setattr(
        'src.tools.actual_user.api_startup_file_path',
        lambda settings=None: api_file,
    )
    with app.app_context():
        write_api_startup_file(main_user)

    client = app.test_client()
    response = client.put(DARKMODE_CANONICAL_PATH, json=_auth_body(main_user))

    assert response.status_code == 200
    assert response.mimetype == 'text/plain'
    assert 'attachment' in response.headers['Content-Disposition']
    assert routes_use_rotation()
    assert client.put(CHECKIN_URL, json=_auth_body(main_user)).status_code == 404


def test_re_rotate_produces_new_paths(routing_app, main_user):
    app, api = routing_app
    first = activate_dark_mode_session(app, api)
    first_paths = {entry.path for entry in first}

    second = activate_dark_mode_session(app, api)
    second_paths = {entry.path for entry in second}

    assert first_paths.isdisjoint(second_paths)


def test_startup_route_lines_match_rotation(routing_app, main_user):
    app, api = routing_app
    activate_dark_mode_session(app, api)

    lines = get_active_route_lines()
    assert lines != canonical_route_lines()
    for line in lines:
        assert line.startswith(('PUT ', 'GET ', 'POST '))


def test_write_api_startup_file_uses_rotated_paths(routing_app, main_user, tmp_path, monkeypatch):
    app, api = routing_app
    api_file = tmp_path / 'api.txt'
    monkeypatch.setattr(
        'src.tools.actual_user.api_startup_file_path',
        lambda settings=None: api_file,
    )
    activate_dark_mode_session(app, api)

    with app.app_context():
        write_api_startup_file(main_user)

    content = api_file.read_text(encoding='utf-8')
    assert 'dark mode' in content.lower()
    assert CHECKIN_URL not in content
    for line in get_active_route_lines():
        assert line.split(' ', 1)[1] in content
