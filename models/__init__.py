from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager


db = SQLAlchemy()

login_manager = LoginManager()


# Import models so SQLAlchemy knows about them
from models.user import User
from models.profile import Profile
from models.education import Education
from models.skill import Skill
