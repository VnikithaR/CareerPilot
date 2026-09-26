from flask import Flask, render_template
from flask_login import login_required

from config import Config

from models import db, login_manager
from models.user import User

from routes.auth import auth
from routes.student import student



app = Flask(__name__)

app.config.from_object(Config)


# -----------------------------
# Database
# -----------------------------

db.init_app(app)


# -----------------------------
# Login Manager
# -----------------------------

login_manager.init_app(app)

login_manager.login_view = "auth.login"


# -----------------------------
# Register Blueprints
# -----------------------------

app.register_blueprint(auth)
app.register_blueprint(student)



# -----------------------------
# User Loader
# -----------------------------

@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))


# -----------------------------
# Home Page
# -----------------------------

@app.route("/")
def home():

    return render_template("index.html")


# -----------------------------
# Student Dashboard
# -----------------------------

@app.route("/dashboard")
@login_required
def student_dashboard():

    return render_template(
        "student/dashboard.html"
    )


# -----------------------------
# Create Database
# -----------------------------

with app.app_context():

    db.create_all()


# -----------------------------
# Run Application
# -----------------------------

if __name__ == "__main__":

    app.run(debug=True)