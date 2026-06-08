import io
import json
from pathlib import Path

import pytest
from werkzeug.datastructures import MultiDict

from api import app, db
from src.models.message import Message
from src.models.user import User
from src.tools.message_files import prepare_message_upload_folder, read_message_attachment

MESSAGES_ADD_URL = '/api/v1/messages/add'


@pytest.fixture
def client(tmp_path, monkeypatch):
    upload_folder = tmp_path / 'message_files'
    monkeypatch.setattr(
        'src.tools.message_files.message_upload_folder_path',
        lambda settings=None: upload_folder,
    )
    monkeypatch.setenv('SOIDIED_MASTER_KEY', 'test-master-key')

    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app.test_client(), upload_folder
        db.session.remove()
        db.drop_all()


def _auth_fields(user: User) -> dict:
    return {'id': user.id, 'token': user.access_token}


def _folder_entries(upload_folder: Path) -> list[Path]:
    if not upload_folder.exists():
        return []
    return list(upload_folder.iterdir())


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
    saved_path = Path(next(iter(file_paths)))
    assert saved_path.parent == upload_folder
    assert saved_path.name.endswith('.txt.enc')
    assert saved_path.is_file()
    assert saved_path.read_bytes() != b'attachment contents'
    assert read_message_attachment(str(saved_path)) == b'attachment contents'
    assert {message.file_ext for message in saved} == {'.txt'}
    assert all(message_dict['file'] is True for message_dict in data['messages'])
    assert all(message_dict['file_ext'] == '.txt' for message_dict in data['messages'])


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
    assert _folder_entries(_upload_folder) == []


@pytest.mark.parametrize(
    ('missing_field', 'expected_message'),
    [
        ('network', 'Missing required field: network'),
        ('message', 'Missing required field: message'),
        ('recipients', 'Missing required field: recipients'),
    ],
)
def test_message_upload_rejects_missing_required_fields_without_side_effects(
    client,
    main_auth,
    missing_field,
    expected_message,
):
    test_client, upload_folder = client
    data = {
        **main_auth,
        'network': 'email',
        'recipients': json.dumps(['alex@example.com']),
        'message': 'Should not save.',
        'file': (io.BytesIO(b'should not save'), 'payload.txt'),
    }
    del data[missing_field]

    response = test_client.post(
        MESSAGES_ADD_URL,
        data=data,
        content_type='multipart/form-data',
    )

    assert response.status_code == 400
    assert response.get_json()['message'] == expected_message
    assert Message.query.count() == 0
    assert _folder_entries(upload_folder) == []


@pytest.mark.parametrize(
    ('recipients', 'expected_message'),
    [
        ('[not-json', 'Invalid JSON array for field: recipients'),
        (json.dumps(['alex@example.com', 3]), 'Field recipients must be an array of strings'),
        (json.dumps([' ', '']), 'Field recipients must include at least one recipient'),
        ('  ', 'Field recipients must include at least one recipient'),
    ],
)
def test_message_upload_rejects_invalid_recipients_without_side_effects(
    client,
    main_auth,
    recipients,
    expected_message,
):
    test_client, upload_folder = client
    response = test_client.post(
        MESSAGES_ADD_URL,
        data={
            **main_auth,
            'network': 'email',
            'recipients': recipients,
            'message': 'Should not save.',
            'file': (io.BytesIO(b'should not save'), 'payload.txt'),
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 400
    assert response.get_json()['message'] == expected_message
    assert Message.query.count() == 0
    assert _folder_entries(upload_folder) == []


def test_message_upload_rejects_invalid_token_before_saving_file(client, main_auth):
    test_client, upload_folder = client

    response = test_client.post(
        MESSAGES_ADD_URL,
        data={
            'id': main_auth['id'],
            'token': User.generate_access_token(),
            'network': 'email',
            'recipients': json.dumps(['alex@example.com']),
            'message': 'Should not save.',
            'file': (io.BytesIO(b'should not save'), 'payload.txt'),
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 401
    assert Message.query.count() == 0
    assert _folder_entries(upload_folder) == []
    user = User.query.filter_by(id=main_auth['id']).one()
    assert user.auth_fail_count == 1


def test_message_upload_sanitizes_attachment_filename(client, main_auth):
    test_client, upload_folder = client

    response = test_client.post(
        MESSAGES_ADD_URL,
        data={
            **main_auth,
            'network': 'email',
            'recipients': json.dumps(['alex@example.com']),
            'message': 'Sanitize this file name.',
            'file': (io.BytesIO(b'attachment'), '../../secret.txt'),
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 201
    saved = Message.query.one()
    saved_path = Path(saved.file_path)
    assert saved_path.parent == upload_folder
    assert '..' not in saved_path.name
    assert '/' not in saved_path.name
    assert saved_path.name.endswith('_secret.txt.enc')
    assert saved.file_ext == '.txt'
    assert saved_path.read_bytes() != b'attachment'
    assert read_message_attachment(str(saved_path)) == b'attachment'


def test_message_upload_with_file_requires_master_key(client, main_auth, monkeypatch):
    test_client, upload_folder = client
    monkeypatch.delenv('SOIDIED_MASTER_KEY', raising=False)

    response = test_client.post(
        MESSAGES_ADD_URL,
        data={
            **main_auth,
            'network': 'email',
            'recipients': json.dumps(['alex@example.com']),
            'message': 'Should not save without a key.',
            'file': (io.BytesIO(b'should not save'), 'payload.txt'),
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 500
    assert 'SOIDIED_MASTER_KEY is required' in response.get_json()['message']
    assert Message.query.count() == 0
    assert _folder_entries(upload_folder) == []


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


@pytest.mark.parametrize('configured_path', ['/', '.'])
def test_prepare_message_upload_folder_rejects_unsafe_cleanup_targets(configured_path):
    class TestSettings:
        def get(self, key, default=None):
            if key == 'settings':
                return {'message_upload_folder': configured_path}
            return default

    with pytest.raises(ValueError, match='dedicated subdirectory'):
        prepare_message_upload_folder(TestSettings())
