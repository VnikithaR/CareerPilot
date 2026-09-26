from models import db


class Profile(db.Model):

    __tablename__ = "profiles"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        unique=True,
        nullable=False
    )

    phone = db.Column(
        db.String(20)
    )

    location = db.Column(
        db.String(100)
    )

    career_interest = db.Column(
        db.String(100)
    )

    summary = db.Column(
        db.Text
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "profile",
            uselist=False
        )
    )

    def __repr__(self):
        return f"<Profile {self.id}>"