from api import app, db
from src.models.message import Message


def test_message_model_persists_requested_fields():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        message = Message(
            network_name='email',
            recipient_name='Alex',
            message='This is the message body.',
            file_path='/safe/storage/attachment.pdf',
        )
        db.session.add(message)
        db.session.commit()

        saved = Message.query.one()

        assert saved.id == 1
        assert saved.network_name == 'email'
        assert saved.recipient_name == 'Alex'
        assert saved.message == 'This is the message body.'
        assert saved.file_path == '/safe/storage/attachment.pdf'
        assert saved.to_dict() == {
            'id': 1,
            'network_name': 'email',
            'recipient_name': 'Alex',
            'message': 'This is the message body.',
            'file_path': '/safe/storage/attachment.pdf',
        }

        db.session.remove()
        db.drop_all()


def test_message_model_allows_optional_recipient_and_file_path():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        message = Message(
            network_name='discord',
            message='A message without personalization or an attachment.',
        )
        db.session.add(message)
        db.session.commit()

        saved = Message.query.one()

        assert saved.recipient_name is None
        assert saved.file_path is None

        db.session.remove()
        db.drop_all()
