import uuid

from flask import request

from src.db.extensions import db
from src.models.user import User


def load_json_payload() -> dict:
    return request.get_json(silent=True) or {}


def parse_uuid(value, field_name: str) -> tuple[str | None, dict | None]:
    if value is None:
        return None, {'message': f'Missing required field: {field_name}'}
    try:
        return str(uuid.UUID(str(value))), None
    except (ValueError, AttributeError, TypeError):
        return None, {'message': f'Invalid UUID for field: {field_name}'}


def record_auth_failure(user: User) -> None:
    """Track failed authentication separately from missed check-ins (panic mode, etc.)."""
    user.auth_fail_count += 1


def authenticate_credentials(payload: dict) -> tuple[User | None, tuple[dict, int] | None]:
    user_id, id_error = parse_uuid(payload.get('id'), 'id')
    if id_error:
        return None, (id_error, 400)

    token, token_error = parse_uuid(payload.get('token'), 'token')
    if token_error:
        return None, (token_error, 400)

    user = User.query.filter_by(id=user_id).first()
    if user is None or user.access_token != token:
        if user is not None:
            record_auth_failure(user)
            db.session.commit()
        return None, ({'message': 'Unauthorized'}, 401)

    return user, None
