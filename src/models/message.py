from src.db.extensions import db


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    network_name = db.Column(db.String(120), nullable=False)
    recipient_name = db.Column(db.String(255), nullable=True)
    message = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(1024), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'network_name': self.network_name,
            'recipient_name': self.recipient_name,
            'message': self.message,
            'file_path': self.file_path,
        }
