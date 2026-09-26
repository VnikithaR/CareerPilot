from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file
)

from flask_login import login_required, current_user

from models import db
from models.profile import Profile
from models.education import Education
from models.skill import Skill
from models.project import Project
from models.certification import Certification
from models.experience import Experience

from services.resume_generator import generate_resume


# ---------------------------------------------------------
# STUDENT BLUEPRINT
# ---------------------------------------------------------

student = Blueprint(
    "student",
    __name__,
    url_prefix="/student"
)


# ---------------------------------------------------------
# STUDENT PROFILE
# ---------------------------------------------------------

@student.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    profile = Profile.query.filter_by(
        user_id=current_user.id
    ).first()

    # Create profile automatically if it does not exist
    if profile is None:

        profile = Profile(
            user_id=current_user.id
        )

        db.session.add(profile)
        db.session.commit()

    # Update profile
    if request.method == "POST":

        profile.phone = request.form.get("phone")
        profile.location = request.form.get("location")
        profile.career_interest = request.form.get(
            "career_interest"
        )
        profile.summary = request.form.get("summary")

        db.session.commit()

        flash("Profile updated successfully.")

        return redirect(
            url_for("student.profile")
        )

    # Get student's education
    education = Education.query.filter_by(
        user_id=current_user.id
    ).all()

    # Get student's skills
    skills = Skill.query.filter_by(
        user_id=current_user.id
    ).all()

    # Get student's projects
    projects = Project.query.filter_by(
        user_id=current_user.id
    ).all()

    # Get student's certifications
    certifications = Certification.query.filter_by(
        user_id=current_user.id
    ).all()

    # Get student's experience
    experience = Experience.query.filter_by(
        user_id=current_user.id
    ).all()

    return render_template(
        "student/profile.html",
        profile=profile,
        education=education,
        skills=skills,
        projects=projects,
        certifications=certifications,
        experience=experience
    )


# ---------------------------------------------------------
# ADD EDUCATION
# ---------------------------------------------------------

@student.route("/education/add", methods=["POST"])
@login_required
def add_education():

    education = Education(
        user_id=current_user.id,
        degree=request.form.get("degree"),
        institution=request.form.get("institution"),
        year=request.form.get("year"),
        cgpa=request.form.get("cgpa")
    )

    db.session.add(education)
    db.session.commit()

    flash("Education added successfully.")

    return redirect(
        url_for("student.profile")
    )


# ---------------------------------------------------------
# ADD SKILL
# ---------------------------------------------------------

@student.route("/skill/add", methods=["POST"])
@login_required
def add_skill():

    skill_name = request.form.get(
        "skill_name"
    )

    skill_type = request.form.get(
        "skill_type"
    ) or "technical"

    if not skill_name:

        flash("Please enter a skill.")

        return redirect(
            url_for("student.profile")
        )

    skill = Skill(
        user_id=current_user.id,
        skill_name=skill_name.strip(),
        skill_type=skill_type
    )

    db.session.add(skill)
    db.session.commit()

    flash("Skill added successfully.")

    return redirect(
        url_for("student.profile")
    )


# ---------------------------------------------------------
# ADD PROJECT
# ---------------------------------------------------------

@student.route("/project/add", methods=["POST"])
@login_required
def add_project():

    project = Project(
        user_id=current_user.id,
        title=request.form.get("title"),
        description=request.form.get("description"),
        technologies=request.form.get("technologies"),
        project_url=request.form.get("project_url")
    )

    db.session.add(project)
    db.session.commit()

    flash("Project added successfully.")

    return redirect(
        url_for("student.profile")
    )


# ---------------------------------------------------------
# ADD CERTIFICATION
# ---------------------------------------------------------

@student.route("/certification/add", methods=["POST"])
@login_required
def add_certification():

    certification = Certification(
        user_id=current_user.id,
        name=request.form.get("name"),
        issuer=request.form.get("issuer"),
        issue_date=request.form.get("issue_date"),
        credential_url=request.form.get("credential_url")
    )

    db.session.add(certification)
    db.session.commit()

    flash("Certification added successfully.")

    return redirect(
        url_for("student.profile")
    )


# ---------------------------------------------------------
# ADD EXPERIENCE
# ---------------------------------------------------------

@student.route("/experience/add", methods=["POST"])
@login_required
def add_experience():

    experience = Experience(
        user_id=current_user.id,
        job_title=request.form.get("job_title"),
        company=request.form.get("company"),
        start_date=request.form.get("start_date"),
        end_date=request.form.get("end_date"),
        description=request.form.get("description")
    )

    db.session.add(experience)
    db.session.commit()

    flash("Experience added successfully.")

    return redirect(
        url_for("student.profile")
    )


# ---------------------------------------------------------
# RESUME PAGE
# ---------------------------------------------------------

@student.route("/resume")
@login_required
def resume():

    return render_template(
        "student/resume.html"
    )


# ---------------------------------------------------------
# DOWNLOAD RESUME
# ---------------------------------------------------------

@student.route("/resume/download")
@login_required
def download_resume():

    pdf = generate_resume(current_user)

    return send_file(
        pdf,
        as_attachment=True,
        download_name="CareerPilot_Resume.pdf",
        mimetype="application/pdf"
    )
