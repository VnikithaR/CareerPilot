from models import db


class Education(db.Model):

    __tablename__ = "education"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    degree = db.Column(
        db.String(100),
        nullable=False
    )

    institution = db.Column(
        db.String(200),
        nullable=False
    )

    year = db.Column(
        db.String(20)
    )

    cgpa = db.Column(
        db.String(20)
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "education",
            lazy=True
        )
    )

    def __repr__(self):
        return f"<Education {self.degree}>"