from flask_restful import Resource

from src.api.auth import authenticate_credentials, load_json_payload
from src.db.extensions import db
from src.tools.check_in import (
    compute_check_in_status,
    effective_deadline,
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
            record_successful_check_in(user, settings)
        else:
            record_compromised_check_in(user, settings)

        db.session.commit()

        return {
            'message': format_next_check_in_message(effective_deadline(user, settings)),
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
