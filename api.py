from flask import Flask
from flask_restful import Api

from src.api.check_in import CheckIn, CheckInStatus
from src.api.utils_api import UtilsApi
from src.bootstrap import bootstrap_app
from src.db.extensions import db
from src.models.user import User  # noqa: F401 — register model with SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

api = Api(app)
api.add_resource(CheckIn, '/api/v1/checkin')
api.add_resource(CheckInStatus, '/api/v1/checkin/status')
api.add_resource(UtilsApi, '/api/v1/utils/api')

bootstrap_app(app)


@app.route('/')
def home():
    return 'Welcome to the SoIDied App!'


if __name__ == '__main__':
    app.run(debug=True)
