import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "careerpilot-dev-secret-key")

    SQLALCHEMY_DATABASE_URI = "sqlite:///careerpilot.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
