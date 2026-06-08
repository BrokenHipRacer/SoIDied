import pytest

from api import app, db
from src.models.message import Message
from src.models.user import User

MESSAGES_URL = '/api/v1/messages'
MESSAGES_LIST_URL = '/api/v1/messages/list'


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def _auth_fields(user: User) -> dict:
    return {'id': user.id, 'token': user.access_token}


@pytest.fixture
def main_auth(client):
    with app.app_context():
        user = User(is_actual_user=True)
        db.session.add(user)
        auth = _auth_fields(user)
        db.session.commit()
        return auth


def test_message_list_returns_metadata_without_file_paths(client, main_auth):
    messages = [
        Message(
            network_name='email',
            recipient='alex@example.com',
            message='Email message.',
            file_path='startup/message_files/shared-note.txt.enc',
            file_ext='.txt',
        ),
        Message(
            network_name='discord',
            recipient='channel-1',
            message='Discord message.',
            file_path='startup/message_files/no_extension',
        ),
        Message(
            network_name='Twitter',
            recipient='@casey',
            message='Social message.',
        ),
    ]
    db.session.add_all(messages)
    db.session.commit()

    response = client.get(MESSAGES_URL, json=main_auth)

    assert response.status_code == 200
    data = response.get_json()
    assert data == [
        {
            'id': 1,
            'network_name': 'email',
            'recipient': 'alex@example.com',
            'message': 'Email message.',
            'file': True,
            'file_ext': '.txt',
        },
        {
            'id': 2,
            'network_name': 'discord',
            'recipient': 'channel-1',
            'message': 'Discord message.',
            'file': True,
            'file_ext': None,
        },
        {
            'id': 3,
            'network_name': 'Twitter',
            'recipient': '@casey',
            'message': 'Social message.',
            'file': False,
            'file_ext': None,
        },
    ]
    assert all('file_path' not in message for message in data)


def test_message_list_alias_returns_same_metadata(client, main_auth):
    message = Message(
        network_name='email',
        recipient='alex@example.com',
        message='Email message.',
        file_path='startup/message_files/shared-note.pdf.enc',
        file_ext='.pdf',
    )
    db.session.add(message)
    db.session.commit()

    canonical = client.get(MESSAGES_URL, json=main_auth)
    alias = client.get(MESSAGES_LIST_URL, json=main_auth)

    assert canonical.status_code == 200
    assert alias.status_code == 200
    assert alias.get_json() == canonical.get_json()
    assert alias.get_json()[0]['file_ext'] == '.pdf'


def test_message_list_returns_empty_array(client, main_auth):
    response = client.get(MESSAGES_URL, json=main_auth)

    assert response.status_code == 200
    assert response.get_json() == []


def test_message_list_requires_actual_user(client):
    with app.app_context():
        user = User(is_actual_user=False)
        db.session.add(user)
        auth = _auth_fields(user)
        db.session.commit()

    response = client.get(MESSAGES_URL, json=auth)

    assert response.status_code == 403


def test_message_list_rejects_invalid_token(client, main_auth):
    response = client.get(
        MESSAGES_URL,
        json={
            'id': main_auth['id'],
            'token': User.generate_access_token(),
        },
    )

    assert response.status_code == 401
    user = User.query.filter_by(id=main_auth['id']).one()
    assert user.auth_fail_count == 1


def test_message_list_requires_id_and_token(client):
    response = client.get(MESSAGES_URL, json={'id': 'not-a-uuid'})

    assert response.status_code == 400
