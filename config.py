import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'OttersRAwesome'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///lost.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = 'smtp.easyname.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'office@stimmungskompass.at'
    MAIL_PASSWORD = '.75sq6oao1ar'
    TWILIO_PHONE_NUMBER = '+1 424 329 4447'
    TWILIO_ACCOUNT_SID = 'ACc21e0ab649ebe0280c1cab26ebdb92be'
    TWILIO_AUTH_TOKEN = '8b95b2099441c3decf4381b6ec6a385b'
    LANGUAGES = ['en', 'de', 'fr', 'it']
