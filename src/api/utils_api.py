from flask import Response
from flask_restful import Resource

from src.api.auth import authenticate_credentials, load_json_payload
from src.tools.actual_user import api_startup_file_path, read_api_startup_file
from src.tools.settings import Settings


class UtilsApi(Resource):
    """Serve the startup API file (credentials and routes) as a downloadable text file."""

    def get(self):
        payload = load_json_payload()
        user, error = authenticate_credentials(payload)
        if error:
            return error

        if not user.is_actual_user:
            return {'message': 'Forbidden'}, 403

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
