import pytest

from api import app, db
from src.models.user import User
from src.tools.actual_user import (
    ensure_actual_user,
    initialize_actual_user,
    read_api_startup_file,
    write_api_startup_file,
)

UTILS_API_URL = '/api/v1/utils/api'


@pytest.fixture
def client(tmp_path, monkeypatch):
    credentials_file = tmp_path / 'actual_user.md'
    api_file = tmp_path / 'api.txt'

    monkeypatch.setattr(
        'src.tools.actual_user.credentials_file_path',
        lambda settings=None: credentials_file,
    )
    monkeypatch.setattr(
        'src.tools.actual_user.api_startup_file_path',
        lambda settings=None: api_file,
    )

    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app.test_client(), credentials_file, api_file
        db.session.remove()
        db.drop_all()


def _auth_body(user: User) -> dict:
    return {'id': user.id, 'token': user.access_token}


def test_ensure_actual_user_creates_single_actual_user(client):
    with app.app_context():
        first = ensure_actual_user()
        second = ensure_actual_user()

        assert first.id == second.id
        assert User.query.filter_by(is_actual_user=True).count() == 1


def test_only_one_actual_user_allowed(client):
    with app.app_context():
        ensure_actual_user()
        with pytest.raises(ValueError, match='Only one actual user'):
            duplicate = User(is_actual_user=True)
            db.session.add(duplicate)
            db.session.commit()


def test_initialize_actual_user_writes_startup_files(client):
    _, credentials_file, api_file = client
    with app.app_context():
        user = initialize_actual_user()
        credentials = credentials_file.read_text(encoding='utf-8')
        api_content = api_file.read_text(encoding='utf-8')

        assert user.id in credentials
        assert user.access_token in credentials
        assert user.id in api_content
        assert 'PUT /api/v1/checkin' in api_content


def test_utils_api_endpoint_returns_startup_file_for_actual_user(client):
    test_client, _, api_file = client
    with app.app_context():
        user = ensure_actual_user()
        write_api_startup_file(user)

    response = test_client.get(UTILS_API_URL, json=_auth_body(user))

    assert response.status_code == 200
    data = response.get_json()
    assert user.id in data['file']
    assert user.access_token in data['file']
    assert 'PUT /api/v1/checkin' in data['file']
    assert read_api_startup_file() == api_file.read_text(encoding='utf-8')


def test_utils_api_endpoint_forbidden_for_non_actual_user(client):
    test_client, _, _ = client
    with app.app_context():
        actual = ensure_actual_user()
        write_api_startup_file(actual)
        other = User(is_actual_user=False)
        db.session.add(other)
        db.session.commit()
        other_auth = _auth_body(other)

    response = test_client.get(UTILS_API_URL, json=other_auth)

    assert response.status_code == 403


def test_create_db_rejects_manual_execution():
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, 'create_db.py'],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert 'internal use only' in result.stdout.lower() or 'internal use only' in result.stderr.lower()
