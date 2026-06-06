import json

from flask import request
from flask_restful import Resource

from src.api.auth import authenticate_credentials
from src.db.extensions import db
from src.models.message import Message
from src.tools.message_files import save_message_attachment
from src.tools.settings import Settings


def _parse_recipients() -> tuple[list[str], dict | None]:
    raw_values = request.form.getlist('recipients')
    if not raw_values:
        return [], {'message': 'Missing required field: recipients'}

    recipients: list[str] = []
    for raw_value in raw_values:
        value = raw_value.strip()
        if not value:
            continue
        if value.startswith('['):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return [], {'message': 'Invalid JSON array for field: recipients'}
            if not isinstance(decoded, list) or not all(isinstance(item, str) for item in decoded):
                return [], {'message': 'Field recipients must be an array of strings'}
            recipients.extend(item.strip() for item in decoded if item.strip())
        else:
            recipients.extend(item.strip() for item in value.split(',') if item.strip())

    if not recipients:
        return [], {'message': 'Field recipients must include at least one recipient'}

    return recipients, None


class MessageUpload(Resource):
    def post(self):
        payload = request.form.to_dict(flat=True)
        user, error = authenticate_credentials(payload)
        if error:
            return error

        if not user.is_actual_user:
            return {'message': 'Forbidden'}, 403

        network = (request.form.get('network') or '').strip()
        if not network:
            return {'message': 'Missing required field: network'}, 400

        message_text = (request.form.get('message') or '').strip()
        if not message_text:
            return {'message': 'Missing required field: message'}, 400

        recipients, recipients_error = _parse_recipients()
        if recipients_error:
            return recipients_error, 400

        file_path = save_message_attachment(request.files.get('file'), Settings())
        messages = [
            Message(
                network_name=network,
                recipient=recipient,
                message=message_text,
                file_path=file_path,
            )
            for recipient in recipients
        ]

        db.session.add_all(messages)
        db.session.commit()

        return {
            'count': len(messages),
            'messages': [message.to_dict() for message in messages],
        }, 201
