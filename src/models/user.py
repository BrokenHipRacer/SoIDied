import uuid

from sqlalchemy import DateTime
from sqlalchemy.orm import validates

from src.db.extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, unique=True, nullable=False)
    access_token = db.Column(db.String(36), nullable=False)
    is_actual_user = db.Column(db.Boolean, nullable=False, default=False)
    last_check_in = db.Column(DateTime(timezone=True), nullable=True)
    next_check_in_deadline = db.Column(DateTime(timezone=True), nullable=True)
    missed_check_in_count = db.Column(db.Integer, nullable=False, default=0)
    auth_fail_count = db.Column(db.Integer, nullable=False, default=0)

    @staticmethod
    def generate_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def generate_access_token() -> str:
        return str(uuid.uuid4())

    def __init__(self, **kwargs):
        if 'id' not in kwargs:
            kwargs['id'] = self.generate_id()
        if 'access_token' not in kwargs:
            kwargs['access_token'] = self.generate_access_token()
        super().__init__(**kwargs)

    @validates('is_actual_user')
    def validate_single_actual_user(self, _key, is_actual: bool) -> bool:
        if not is_actual:
            return is_actual
        query = User.query.filter(User.is_actual_user.is_(True))
        if self.id is not None:
            query = query.filter(User.id != self.id)
        if query.first() is not None:
            raise ValueError('Only one actual user is allowed')
        return is_actual

    def to_dict(self):
        return {
            'id': self.id,
            'is_actual_user': self.is_actual_user,
            'last_check_in': self.last_check_in.isoformat() if self.last_check_in else None,
            'next_check_in_deadline': (
                self.next_check_in_deadline.isoformat()
                if self.next_check_in_deadline
                else None
            ),
            'missed_check_in_count': self.missed_check_in_count,
            'auth_fail_count': self.auth_fail_count,
        }
