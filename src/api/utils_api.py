from flask_restful import Resource

from src.api.auth import authenticate_credentials, load_json_payload
from src.api.guards import dark_mode_not_found, is_dark_mode_enabled
from src.tools.actual_user import read_api_startup_file
from src.tools.settings import Settings


class UtilsApi(Resource):
    """Return the startup API file (credentials and documented routes)."""

    def get(self):
        if is_dark_mode_enabled():
            return dark_mode_not_found()

        payload = load_json_payload()
        user, error = authenticate_credentials(payload)
        if error:
            return error

        if not user.is_actual_user:
            return {'message': 'Forbidden'}, 403

        content = read_api_startup_file(Settings())
        if content is None:
            return {'message': 'Startup API file not found'}, 404

        return {
            'file': content,
        }, 200
