from flask import Flask, request
from flask_restful import Api

from src.api.routing import bind_restful_api, init_api_routes
from src.bootstrap import bootstrap_app
from src.db.extensions import db
from src.models.message import Message  # noqa: F401 — register model with SQLAlchemy
from src.models.user import User  # noqa: F401 — register model with SQLAlchemy
from src.tools.settings import Settings
from src.tools.tls import apply_hsts, resolve_run_options

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

api = Api(app)
bind_restful_api(app, api)
init_api_routes(app, api)

bootstrap_app(app)

try:
    _settings = Settings()
except FileNotFoundError:
    _settings = None


@app.route('/')
def home():
    return 'Welcome to the SoIDied App!'


@app.after_request
def _security_headers(response):
    if _settings is None:
        return response
    return apply_hsts(_settings, response, request.is_secure)


if __name__ == '__main__':
    app.run(**resolve_run_options(_settings or Settings()))
