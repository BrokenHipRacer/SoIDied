from flask import Response, current_app
from flask_restful import Resource

from src.api.auth import authenticate_credentials, load_json_payload
from src.api.routing import activate_dark_mode_session, get_restful_api
from src.tools.actual_user import api_startup_file_path, read_api_startup_file
from src.tools.settings import Settings


class DarkMode(Resource):
    """Enable dark mode for this process (in-memory), rotate API paths, and return the file."""

    def put(self):
        payload = load_json_payload()
        _user, error = authenticate_credentials(payload)
        if error:
            return error

        activate_dark_mode_session(current_app, get_restful_api(current_app))

        settings = Settings()
        content = read_api_startup_file(settings)
        if content is None:
            return {'message': 'Startup API file not found'}, 404

        filename = api_startup_file_path(settings).name
        return Response(
            content,
            status=200,
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'},
        )
