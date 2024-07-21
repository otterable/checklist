from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=True)
    phone = db.Column(db.String(20), nullable=True)

class Item(db.Model):
    id = db.Column(db.String(5), primary_key=True)  # Changed to String and length 5
    title = db.Column(db.String(128), nullable=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    image = db.Column(db.String(128), nullable=False)
    reported = db.Column(db.Boolean, default=True)  # Set default to True
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('items', lazy=True))

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String, nullable=False)
    p256dh = db.Column(db.String, nullable=False)
    auth = db.Column(db.String, nullable=False)
