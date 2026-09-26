from models import db


class Experience(db.Model):

    __tablename__ = "experience"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    job_title = db.Column(
        db.String(150),
        nullable=False
    )

    company = db.Column(
        db.String(200),
        nullable=False
    )

    start_date = db.Column(
        db.String(50)
    )

    end_date = db.Column(
        db.String(50)
    )

    description = db.Column(
        db.Text
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "experience",
            lazy=True
        )
    )

    def __repr__(self):
        return f"<Experience {self.job_title}>"
