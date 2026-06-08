from flask import Flask

from src.db.extensions import db

DEFAULT_DATABASE_URI = 'sqlite:///database.db'


def create_schema() -> None:
    db.create_all()


def run_standalone_schema_init(database_uri: str = DEFAULT_DATABASE_URI) -> None:
    """Create tables using a minimal Flask app (no api import or bootstrap)."""
    import src.models.message  # noqa: F401 — register models with metadata
    import src.models.user  # noqa: F401 — register models with metadata

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    db.init_app(app)
    with app.app_context():
        create_schema()
