import uuid

import pytest

from api import app, db
from src.models.user import User

CHECKIN_URL = '/api/v1/checkin'
CHECKIN_STATUS_URL = '/api/v1/checkin/status'


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def _auth_body(user: User) -> dict:
    return {'id': user.id, 'token': user.access_token}


@pytest.fixture
def main_user(client):
    user = User(is_actual_user=True)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def non_main_user(client):
    user = User(is_actual_user=False)
    db.session.add(user)
    db.session.commit()
    return user


def test_checkin_put_main_user_resets_missed_count(client, main_user):
    main_user.missed_check_in_count = 2
    db.session.commit()

    response = client.put(CHECKIN_URL, json=_auth_body(main_user))

    assert response.status_code == 200
    data = response.get_json()
    assert data['message'].startswith('Next required Check-In by:')

    db.session.refresh(main_user)
    assert main_user.missed_check_in_count == 0
    assert main_user.last_check_in is not None
    assert main_user.next_check_in_deadline is not None
    assert main_user.next_check_in_deadline > main_user.last_check_in


def test_checkin_put_message_matches_stored_deadline(client, main_user):
    response = client.put(CHECKIN_URL, json=_auth_body(main_user))

    assert response.status_code == 200
    db.session.refresh(main_user)
    assert main_user.next_check_in_deadline is not None
    assert main_user.next_check_in_deadline.isoformat() in response.get_json()['message']


def test_checkin_put_non_main_user_does_not_reset_missed_count(client, non_main_user):
    non_main_user.missed_check_in_count = 2
    db.session.commit()

    response = client.put(CHECKIN_URL, json=_auth_body(non_main_user))

    assert response.status_code == 200
    assert response.get_json()['message'].startswith('Next required Check-In by:')

    db.session.refresh(non_main_user)
    assert non_main_user.missed_check_in_count == 2
    assert non_main_user.last_check_in is not None


def test_checkin_invalid_token_increments_auth_fail_not_missed_count(client, main_user):
    response = client.put(
        CHECKIN_URL,
        json={'id': main_user.id, 'token': str(uuid.uuid4())},
    )

    assert response.status_code == 401
    db.session.refresh(main_user)
    assert main_user.auth_fail_count == 1
    assert main_user.missed_check_in_count == 0


def test_checkin_unknown_user_returns_401(client):
    response = client.put(
        CHECKIN_URL,
        json={'id': str(uuid.uuid4()), 'token': str(uuid.uuid4())},
    )

    assert response.status_code == 401
    assert User.query.count() == 0


def test_checkin_requires_id_and_token_fields(client):
    response = client.put(CHECKIN_URL, json={'id': 'not-a-uuid'})

    assert response.status_code == 400


def test_checkin_status_ok(client, main_user):
    client.put(CHECKIN_URL, json=_auth_body(main_user))

    response = client.get(CHECKIN_STATUS_URL, json=_auth_body(main_user))

    assert response.status_code == 200
    assert response.get_json()['Status'] == 'OK'


def test_checkin_status_dead_when_missed_count_reaches_miss_count(client, main_user):
    main_user.missed_check_in_count = 2
    db.session.commit()

    response = client.get(CHECKIN_STATUS_URL, json=_auth_body(main_user))

    assert response.status_code == 200
    assert response.get_json()['Status'] == 'DEAD'


def test_checkin_status_alert_without_check_in(client, main_user):
    main_user.last_check_in = None
    main_user.missed_check_in_count = 0
    db.session.commit()

    response = client.get(CHECKIN_STATUS_URL, json=_auth_body(main_user))

    assert response.status_code == 200
    assert response.get_json()['Status'] == 'ALERT'
