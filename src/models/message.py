from pathlib import Path

from src.db.extensions import db


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    network_name = db.Column(db.String(120), nullable=False)
    recipient = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(1024), nullable=True)
    file_ext = db.Column(db.String(32), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'network_name': self.network_name,
            'recipient': self.recipient,
            'message': self.message,
            'file_path': self.file_path,
            'file': self.file_path is not None,
            'file_ext': self.file_ext,
        }

    def to_list_dict(self):
        file_ext = self.file_ext
        if file_ext is None and self.file_path and not self.file_path.endswith('.enc'):
            file_ext = Path(self.file_path).suffix or None
        return {
            'id': self.id,
            'network_name': self.network_name,
            'recipient': self.recipient,
            'message': self.message,
            'file': self.file_path is not None,
            'file_ext': file_ext or None,
        }
