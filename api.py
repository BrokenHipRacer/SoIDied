from flask import Flask
from flask_restful import Api

from src.api.routing import bind_restful_api, init_api_routes
from src.bootstrap import bootstrap_app
from src.db.extensions import db
from src.models.message import Message  # noqa: F401 — register model with SQLAlchemy
from src.models.user import User  # noqa: F401 — register model with SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

api = Api(app)
bind_restful_api(app, api)
init_api_routes(app, api)

bootstrap_app(app)


@app.route('/')
def home():
    return 'Welcome to the SoIDied App!'


if __name__ == '__main__':
    app.run(debug=True)
