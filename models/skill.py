from models import db


class Skill(db.Model):

    __tablename__ = "skills"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    skill_name = db.Column(
        db.String(100),
        nullable=False
    )

    skill_type = db.Column(
        db.String(50),
        default="technical"
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "skills",
            lazy=True
        )
    )

    def __repr__(self):
        return f"<Skill {self.skill_name}>"