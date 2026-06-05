from flask_restful import Resource

from src.api.auth import authenticate_credentials, load_json_payload
from src.db.extensions import db
from src.tools.check_in import (
    compute_next_check_in_deadline,
    compute_check_in_status,
    format_next_check_in_message,
    record_compromised_check_in,
    record_successful_check_in,
)
from src.tools.settings import Settings


class CheckIn(Resource):
    def put(self):
        payload = load_json_payload()
        user, error = authenticate_credentials(payload)
        if error:
            return error

        settings = Settings()
        if user.is_actual_user:
            check_in_time = record_successful_check_in(user)
        else:
            check_in_time = record_compromised_check_in(user)

        db.session.commit()
        deadline = compute_next_check_in_deadline(check_in_time, settings)

        return {
            'message': format_next_check_in_message(deadline),
        }, 200


class CheckInStatus(Resource):
    def get(self):
        payload = load_json_payload()
        user, error = authenticate_credentials(payload)
        if error:
            return error

        return {
            'Status': compute_check_in_status(user, Settings()),
        }, 200
