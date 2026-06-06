import io
import json

import pytest
from werkzeug.datastructures import MultiDict

from api import app, db
from src.models.message import Message
from src.models.user import User
from src.tools.message_files import prepare_message_upload_folder

MESSAGES_ADD_URL = '/api/v1/messages/add'


@pytest.fixture
def client(tmp_path, monkeypatch):
    upload_folder = tmp_path / 'message_files'
    monkeypatch.setattr(
        'src.tools.message_files.message_upload_folder_path',
        lambda settings=None: upload_folder,
    )

    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app.test_client(), upload_folder
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


def test_message_upload_fans_out_rows_and_reuses_one_file(client, main_auth):
    test_client, upload_folder = client
    recipients = ['alex@example.com', 'casey@example.com']
    response = test_client.post(
        MESSAGES_ADD_URL,
        data={
            **main_auth,
            'network': 'email',
            'recipients': json.dumps(recipients),
            'message': 'Shared message body.',
            'file': (io.BytesIO(b'attachment contents'), 'note.txt'),
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data['count'] == 2

    saved = Message.query.order_by(Message.id).all()
    assert [message.recipient for message in saved] == recipients
    assert {message.network_name for message in saved} == {'email'}
    assert {message.message for message in saved} == {'Shared message body.'}

    file_paths = {message.file_path for message in saved}
    assert len(file_paths) == 1
    saved_path = upload_folder / next(iter(file_paths)).split('/')[-1]
    assert saved_path.is_file()
    assert saved_path.read_bytes() == b'attachment contents'
    assert all(message_dict['file'] is True for message_dict in data['messages'])


def test_message_upload_accepts_repeated_recipient_fields_without_file(client, main_auth):
    test_client, _upload_folder = client
    form = MultiDict(
        [
            ('id', main_auth['id']),
            ('token', main_auth['token']),
            ('network', 'discord'),
            ('recipients', 'channel-1'),
            ('recipients', 'channel-2'),
            ('message', 'Discord message.'),
        ]
    )

    response = test_client.post(
        MESSAGES_ADD_URL,
        data=form,
        content_type='multipart/form-data',
    )

    assert response.status_code == 201
    saved = Message.query.order_by(Message.id).all()
    assert [message.recipient for message in saved] == ['channel-1', 'channel-2']
    assert all(message.file_path is None for message in saved)
    assert all(message.to_dict()['file'] is False for message in saved)


def test_message_upload_requires_actual_user(client):
    test_client, _upload_folder = client
    with app.app_context():
        user = User(is_actual_user=False)
        db.session.add(user)
        auth = _auth_fields(user)
        db.session.commit()

    response = test_client.post(
        MESSAGES_ADD_URL,
        data={
            **auth,
            'network': 'email',
            'recipients': json.dumps(['alex@example.com']),
            'message': 'Should not save.',
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 403
    assert Message.query.count() == 0


def test_prepare_message_upload_folder_clears_previous_runtime_files(tmp_path):
    upload_folder = tmp_path / 'message_files'
    upload_folder.mkdir()
    (upload_folder / 'old.txt').write_text('old', encoding='utf-8')
    nested = upload_folder / 'nested'
    nested.mkdir()
    (nested / 'old.txt').write_text('old', encoding='utf-8')

    class TestSettings:
        def get(self, key, default=None):
            if key == 'settings':
                return {'message_upload_folder': str(upload_folder)}
            return default

    prepared = prepare_message_upload_folder(TestSettings())

    assert prepared == upload_folder
    assert upload_folder.is_dir()
    assert list(upload_folder.iterdir()) == []
