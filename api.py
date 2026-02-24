from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api, reqparse, fields, marshal_with, abort


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

user_args = reqparse.RequestParser()
user_args.add_argument('username', type=str, required=True, help="Username is required")
user_args.add_argument('email', type=str, required=True, help="Email is required")

@app.route('/')
def home():
    return "Welcome to the SoIDied App!"


if __name__ == '__main__':
    app.run(debug=True)
