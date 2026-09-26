from flask import Flask, redirect, url_for
from config import Config

from models import db, login_manager
from models.user import User

from routes.auth import auth


app = Flask(__name__)

app.config.from_object(Config)

db.init_app(app)
login_manager.init_app(app)

login_manager.login_view = "auth.login"

app.register_blueprint(auth)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def home():
    return """
    <h1>Welcome to CareerPilot</h1>

    <p>AI-Powered Career Development Platform</p>

    <a href="/register">Register</a>
    |
    <a href="/login">Login</a>
    """


@app.route("/dashboard")
def student_dashboard():

    from flask_login import login_required, current_user

    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    return f"""
    <h1>CareerPilot Dashboard</h1>

    <h2>Welcome, {current_user.name}!</h2>

    <p>Email: {current_user.email}</p>

    <p>Role: {current_user.role}</p>

    <a href="/logout">Logout</a>
    """


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
