from models import db


class Certification(db.Model):

    __tablename__ = "certifications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    name = db.Column(
        db.String(200),
        nullable=False
    )

    issuer = db.Column(
        db.String(200)
    )

    issue_date = db.Column(
        db.String(50)
    )

    credential_url = db.Column(
        db.String(300)
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "certifications",
            lazy=True
        )
    )

    def __repr__(self):
        return f"<Certification {self.name}>"
