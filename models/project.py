from models import db


class Project(db.Model):

    __tablename__ = "projects"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    title = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    technologies = db.Column(
        db.String(300)
    )

    project_url = db.Column(
        db.String(300)
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "projects",
            lazy=True
        )
    )

    def __repr__(self):
        return f"<Project {self.title}>"
