# ==================================================
# CareerPilot - Flask Application
# ==================================================

# Standard library
import os
import joblib
import re
import sqlite3
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

# Third-party libraries
import fitz  # PyMuPDF: render generated PDF pages as images
from PIL import Image
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    session,
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)

# ==================================================
# APPLICATION CONFIGURATION
# ==================================================

app = Flask(__name__)
# Load the trained career prediction model
CAREER_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "career_model.joblib"
)

career_model = None

if os.path.exists(CAREER_MODEL_PATH):
    try:
        career_model = joblib.load(CAREER_MODEL_PATH)
        print("Career prediction model loaded successfully.")
    except Exception as error:
        print(f"Career model could not be loaded: {error}")
app.config["SECRET_KEY"] = os.environ.get(
    "CAREERPILOT_SECRET_KEY",
    "local-development-key-change-before-deployment",
)

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "careerpilot.db"

# ==================================================
# FLASK-LOGIN CONFIGURATION
# ==================================================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access that page."
login_manager.login_message_category = "error"

# ==================================================
# DATABASE
# ==================================================


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS student_profiles (
                user_id INTEGER PRIMARY KEY,
                phone TEXT DEFAULT '',
                location TEXT DEFAULT '',
                professional_summary TEXT DEFAULT '',
                education_level TEXT DEFAULT '',
                institution TEXT DEFAULT '',
                graduation_year TEXT DEFAULT '',
                technical_skills TEXT DEFAULT '',
                soft_skills TEXT DEFAULT '',
                projects TEXT DEFAULT '',
                internships TEXT DEFAULT '',
                certifications TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT DEFAULT '',
                job_type TEXT DEFAULT 'Full-time',
                experience TEXT DEFAULT 'Fresher',
                skills_required TEXT DEFAULT '',
                description TEXT DEFAULT '',
                salary TEXT DEFAULT '',
                application_url TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        
        # Create the student job applications table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Applied',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                UNIQUE(user_id, job_id)
            )
        """)



        # Create the student notifications table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
# ==================================================
# USER MODEL
# ==================================================


class User(UserMixin):
    def __init__(self, user_id, full_name, email, role):
        self.id = str(user_id)
        self.full_name = full_name
        self.email = email
        self.role = role


@login_manager.user_loader
def load_user(user_id):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT id, full_name, email, role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    if row is None:
        return None

    return User(row["id"], row["full_name"], row["email"], row["role"])

# ==================================================
# HOME PAGE
# ==================================================


@app.route("/")
def home():
    return render_template("home.html")

# ==================================================
# REGISTRATION
# ==================================================


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not full_name or len(full_name) > 100:
            flash("Please enter your name (up to 100 characters).", "error")
            return render_template("register.html")

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Please enter a valid email address.", "error")
            return render_template("register.html")

        if len(email) > 254:
            flash("Email address is too long.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        try:
            with get_db_connection() as conn:
                conn.execute(
                    "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
                    (full_name, email, password_hash),
                )
            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("An account with this email already exists.", "error")

    return render_template("register.html")

# ==================================================
# LOGIN
# ==================================================


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT id, full_name, email, password_hash, role
                FROM users WHERE email = ?
                """,
                (email,),
            ).fetchone()

        if row and check_password_hash(row["password_hash"], password):
            user = User(row["id"], row["full_name"], row["email"], row["role"])
            login_user(user)
            flash(f"Welcome back, {user.full_name}!", "success")
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("dashboard"))

        flash("Invalid email or password. Please try again.", "error")

    return render_template("login.html")

# ==================================================
# STUDENT DASHBOARD
# ==================================================


@app.route("/student/dashboard")
@login_required
def dashboard():
    if current_user.role != "student":
        flash("This page is for student accounts.", "error")
        return redirect(url_for("admin_dashboard"))

    with get_db_connection() as conn:
        profile = conn.execute(
            "SELECT * FROM student_profiles WHERE user_id = ?",
            (int(current_user.id),),
        ).fetchone()
        unread_notifications = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM notifications
            WHERE user_id = ? AND is_read = 0
            """,
            (current_user.id,),
        ).fetchone()["total"]

    profile = dict(profile) if profile else {}
    return render_template(
        "student/dashboard.html",
        profile=profile,
        unread_notifications=unread_notifications,
    )

# ==================================================
# STUDENT PROFILE
# ==================================================


@app.route("/student/profile", methods=["GET", "POST"])
@login_required
def student_profile():
    if current_user.role != "student":
        flash("This page is for student accounts.", "error")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        fields = [
            "phone", "location", "professional_summary", "education_level",
            "institution", "graduation_year", "technical_skills", "soft_skills",
            "projects", "internships", "certifications",
        ]
        profile_data = {
            field: request.form.get(field, "").strip() for field in fields
        }
        limits = {
            "phone": 30,
            "location": 150,
            "professional_summary": 2000,
            "education_level": 100,
            "institution": 200,
            "graduation_year": 4,
            "technical_skills": 2000,
            "soft_skills": 1000,
            "projects": 5000,
            "internships": 5000,
            "certifications": 5000,
        }

        for field, maximum in limits.items():
            if len(profile_data[field]) > maximum:
                flash(
                    f"{field.replace('_', ' ').title()} must be {maximum} characters or fewer.",
                    "error",
                )
                return render_template("student/profile.html", profile=profile_data)

        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO student_profiles (
                    user_id, phone, location, professional_summary,
                    education_level, institution, graduation_year,
                    technical_skills, soft_skills, projects, internships,
                    certifications, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    phone = excluded.phone,
                    location = excluded.location,
                    professional_summary = excluded.professional_summary,
                    education_level = excluded.education_level,
                    institution = excluded.institution,
                    graduation_year = excluded.graduation_year,
                    technical_skills = excluded.technical_skills,
                    soft_skills = excluded.soft_skills,
                    projects = excluded.projects,
                    internships = excluded.internships,
                    certifications = excluded.certifications,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    int(current_user.id), profile_data["phone"],
                    profile_data["location"], profile_data["professional_summary"],
                    profile_data["education_level"], profile_data["institution"],
                    profile_data["graduation_year"], profile_data["technical_skills"],
                    profile_data["soft_skills"], profile_data["projects"],
                    profile_data["internships"], profile_data["certifications"],
                ),
            )
        flash("Your profile has been saved successfully!", "success")
        return redirect(url_for("student_profile"))

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM student_profiles WHERE user_id = ?",
            (int(current_user.id),),
        ).fetchone()
    profile = dict(row) if row else {}
    return render_template("student/profile.html", profile=profile)

# ==================================================
# RESUME BUILDER: PDF GENERATION
# ==================================================

RESUME_FIELDS = [
    "professional_title", "phone", "location", "linkedin",
    "professional_summary", "education", "experience", "projects",
    "positions", "achievements", "certifications", "languages",
    "cloud_technologies", "tools", "soft_skills",
]


def create_resume_pdf(data, full_name, email):
    """Create an A4 resume PDF with grey section headings."""
    pdf_buffer = BytesIO()
    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.48 * inch,
        bottomMargin=0.55 * inch,
        title=f"{full_name} - Resume",
        author=full_name,
    )

    styles = getSampleStyleSheet()
    name_style = ParagraphStyle(
        "ResumeName", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=19, leading=22, textColor=colors.HexColor("#171717"), spaceAfter=2,
    )
    title_style = ParagraphStyle(
        "ResumeTitle", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=10, leading=13, textColor=colors.HexColor("#333333"),
    )
    contact_style = ParagraphStyle(
        "ResumeContact", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=11, alignment=TA_LEFT,
        textColor=colors.HexColor("#222222"), wordWrap="CJK",
    )
    section_style = ParagraphStyle(
        "ResumeSection", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=9, leading=12, textColor=colors.black,
    )
    body_style = ParagraphStyle(
        "ResumeBody", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8.5, leading=11, textColor=colors.HexColor("#202020"),
        spaceAfter=3, splitLongWords=True,
    )
    small_style = ParagraphStyle(
        "ResumeSmall", parent=body_style, fontSize=7.5, leading=9,
    )

    story = [Paragraph(escape(full_name), name_style)]
    professional_title = data.get("professional_title", "").strip()
    if professional_title:
        story.append(Paragraph(escape(professional_title), title_style))
    story.append(Spacer(1, 5))

    contact_items = [
        ("Email", email),
        ("Phone", data.get("phone", "")),
        ("Location", data.get("location", "")),
        ("LinkedIn", data.get("linkedin", "")),
    ]
    contact_items = [
        (label, value.strip()) for label, value in contact_items
        if value and value.strip()
    ]
    contact_rows = []
    for index in range(0, len(contact_items), 2):
        left = contact_items[index]
        right = contact_items[index + 1] if index + 1 < len(contact_items) else ("", "")
        left_text = f"<b>{escape(left[0])}:</b> {escape(left[1])}"
        right_text = f"<b>{escape(right[0])}:</b> {escape(right[1])}" if right[1] else ""
        contact_rows.append([
            Paragraph(left_text, contact_style),
            Paragraph(right_text, contact_style),
        ])

    if contact_rows:
        contact_table = Table(contact_rows, colWidths=[3.25 * inch, 3.25 * inch])
        contact_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        story.append(contact_table)
    story.append(Spacer(1, 7))

    def add_section_heading(title):
        heading = Table(
            [[Paragraph(escape(title.upper()), section_style)]],
            colWidths=[document.width],
        )
        heading.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#BFBFBF")),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(heading)
        story.append(Spacer(1, 4))

    def add_text_section(title, text, entry_mode=False):
        text = (text or "").strip()
        if not text:
            return
        add_section_heading(title)
        if entry_mode:
            entries = [block.strip() for block in text.split("\n\n") if block.strip()]
            for entry in entries:
                lines = [line.strip() for line in entry.splitlines() if line.strip()]
                if not lines:
                    continue
                block_flowables = [Paragraph(f"<b>{escape(lines[0])}</b>", body_style)]
                for line in lines[1:]:
                    clean_line = line.lstrip("-• ").strip()
                    if clean_line:
                        block_flowables.append(Paragraph(f"&bull; {escape(clean_line)}", body_style))
                block_flowables.append(Spacer(1, 3))
                story.append(KeepTogether(block_flowables))
        else:
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                line = line.lstrip("-• ").strip()
                story.append(Paragraph(f"&bull; {escape(line)}", body_style))
        story.append(Spacer(1, 4))

    add_text_section("Professional Summary", data.get("professional_summary", ""))

    education = data.get("education", "").strip()
    if education:
        add_section_heading("Education")
        table_data = [[
            Paragraph("<b>Degree</b>", small_style),
            Paragraph("<b>Specialization</b>", small_style),
            Paragraph("<b>Institute</b>", small_style),
            Paragraph("<b>Year</b>", small_style),
            Paragraph("<b>CGPA / %</b>", small_style),
        ]]
        for line in education.splitlines():
            if not line.strip():
                continue
            parts = [part.strip() for part in line.split("|")]
            parts = (parts + ["", "", "", "", ""])[:5]
            table_data.append([Paragraph(escape(part) if part else "-", small_style) for part in parts])
        education_table = Table(
            table_data,
            colWidths=[0.95 * inch, 1.15 * inch, 2.05 * inch, 0.85 * inch, 0.80 * inch],
            repeatRows=1,
            hAlign="LEFT",
        )
        education_table.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.black),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
            ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(education_table)
        story.append(Spacer(1, 7))

    add_text_section("Work Experience", data.get("experience", ""), entry_mode=True)
    add_text_section("Projects", data.get("projects", ""), entry_mode=True)
    add_text_section("Positions of Responsibility", data.get("positions", ""), entry_mode=True)
    add_text_section("Extra-curricular Achievements / Activities", data.get("achievements", ""))
    add_text_section("Certifications", data.get("certifications", ""))

    skill_categories = [
        ("Languages / Technical Skills", data.get("languages", "")),
        ("Cloud Technologies", data.get("cloud_technologies", "")),
        ("Tools", data.get("tools", "")),
        ("Soft Skills", data.get("soft_skills", "")),
    ]
    if any(value.strip() for _, value in skill_categories):
        add_section_heading("Technical Skills")
        for label, value in skill_categories:
            value = value.strip()
            if value:
                story.append(Paragraph(f"<b>{escape(label)}:</b> {escape(value)}", body_style))
                story.append(Spacer(1, 2))

    document.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer

# ==================================================
# RESUME BUILDER: FORM AND DOWNLOADS
# ==================================================


@app.route("/student/resume", methods=["GET", "POST"])
@login_required
def resume_builder():
    if current_user.role != "student":
        flash("This page is for student accounts.", "error")
        return redirect(url_for("admin_dashboard"))

    data = {field: "" for field in RESUME_FIELDS}

    # Prefill fields from the saved student profile.
    with get_db_connection() as conn:
        profile = conn.execute(
            "SELECT * FROM student_profiles WHERE user_id = ?",
            (int(current_user.id),),
        ).fetchone()

    if profile:
        data["phone"] = profile["phone"] or ""
        data["location"] = profile["location"] or ""
        data["professional_summary"] = profile["professional_summary"] or ""
        if profile["education_level"] or profile["institution"]:
            data["education"] = (
                f"{profile['education_level'] or ''} | - | "
                f"{profile['institution'] or ''} | "
                f"{profile['graduation_year'] or ''} | -"
            )
        data["languages"] = profile["technical_skills"] or ""
        data["soft_skills"] = profile["soft_skills"] or ""
        data["projects"] = profile["projects"] or ""
        data["experience"] = profile["internships"] or ""
        data["certifications"] = profile["certifications"] or ""

    if request.method == "POST":
        for field in RESUME_FIELDS:
            data[field] = request.form.get(field, "").strip()

        for field, value in data.items():
            if len(value) > 12000:
                flash(f"The {field.replace('_', ' ')} section is too long (maximum 12,000 characters).", "error")
                return render_template("student/resume.html", data=data)

        if not data["professional_title"]:
            flash("Please enter your professional title or degree.", "error")
            return render_template("student/resume.html", data=data)

        if not any(data[field] for field in [
            "education", "experience", "projects", "languages", "certifications"
        ]):
            flash("Please add at least one education, experience, project, skills, or certification entry.", "error")
            return render_template("student/resume.html", data=data)

        pdf_buffer = create_resume_pdf(data, current_user.full_name, current_user.email)
        download_format = request.form.get("download_format", "pdf").lower()

        # PNG export: render all PDF pages and combine them vertically.
        if download_format == "png":
            try:
                pdf_document = fitz.open(stream=pdf_buffer.getvalue(), filetype="pdf")
                if len(pdf_document) == 0:
                    raise ValueError("The generated PDF has no pages.")

                page_images = []
                for page in pdf_document:
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    image = Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")
                    page_images.append(image)
                pdf_document.close()

                total_width = max(img.width for img in page_images)
                total_height = sum(img.height for img in page_images)
                combined = Image.new("RGB", (total_width, total_height), "white")
                y_offset = 0
                for image in page_images:
                    x_offset = (total_width - image.width) // 2
                    combined.paste(image, (x_offset, y_offset))
                    y_offset += image.height
                    image.close()

                png_buffer = BytesIO()
                combined.save(png_buffer, format="PNG")
                combined.close()
                png_buffer.seek(0)
                return send_file(
                    png_buffer,
                    mimetype="image/png",
                    as_attachment=True,
                    download_name="CareerPilot_Resume.png",
                )
            except Exception:
                app.logger.exception("Resume PNG export failed.")
                flash("Could not create the PNG. Please try downloading the PDF instead.", "error")
                return render_template("student/resume.html", data=data)

        # PDF export (default).
        pdf_buffer.seek(0)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="CareerPilot_Resume.pdf",
        )

    return render_template("student/resume.html", data=data)



# ==============================
# EXPLORE JOBS
# ==============================



@app.route("/student/jobs")
@login_required
def explore_jobs():
    if current_user.role != "student":
        flash("This page is for student accounts.", "error")
        return redirect(url_for("admin_dashboard"))

    search_query = request.args.get("q", "").strip()
    location_query = request.args.get("location", "").strip()

    sql = """
        SELECT *
        FROM jobs
        WHERE (
            title LIKE ? OR
            company LIKE ? OR
            skills_required LIKE ?
        )
        AND location LIKE ?
        ORDER BY created_at DESC
    """

    search_pattern = f"%{search_query}%"
    location_pattern = f"%{location_query}%"

    with get_db_connection() as conn:
        jobs = conn.execute(
            sql,
            (
                search_pattern,
                search_pattern,
                search_pattern,
                location_pattern,
            ),
        ).fetchall()

        profile = conn.execute(
            """
            SELECT *
            FROM student_profiles
            WHERE user_id = ?
            """,
            (current_user.id,),
        ).fetchone()

    # Read the student's technical skills.
    student_text = ""

    if profile:
        profile_columns = profile.keys()

        for column in (
            "technical_skills",
            "skills",
            "key_skills",
        ):
            if column in profile_columns and profile[column]:
                student_text = str(profile[column])
                break

    # Normalize skill names consistently.
    def normalize_job_skills(text):
        aliases = {
            "js": "javascript",
            "ml": "machine learning",
            "scikit learn": "scikit-learn",
            "scikit_learn": "scikit-learn",
            "powerbi": "power bi",
            "structured query language": "sql",
        }

        normalized = []

        for skill in re.split(r"[,;\n|]+", str(text or "")):
            skill = " ".join(skill.lower().strip().split())

            if not skill:
                continue

            skill = aliases.get(skill, skill)

            if skill not in normalized:
                normalized.append(skill)

        return normalized

    student_skills = normalize_job_skills(student_text)

    min_match = request.args.get("min_match", "0")

    try:
        min_match = int(min_match)
    except ValueError:
        min_match = 0

    min_match = max(0, min(100, min_match))

    # Attach a compatibility score to every job.
    job_results = []

    for job in jobs:
        job_data = dict(job)

        required_skills = normalize_job_skills(
            job["skills_required"] or ""
        )

        matched_skills = [
            skill for skill in required_skills
            if skill in student_skills
        ]

        missing_skills = [
            skill for skill in required_skills
            if skill not in student_skills
        ]

        if required_skills:
            match_score = round(
                len(matched_skills) / len(required_skills) * 100
            )
        else:
            match_score = 0

        job_data["match_score"] = match_score
        job_data["matched_skills"] = matched_skills
        job_data["missing_skills"] = missing_skills

        job_results.append(job_data)

    # Show the best skill matches first.
    job_results.sort(
        key=lambda item: item["match_score"],
        reverse=True,
    )

    job_results = [
        job for job in job_results
        if job["match_score"] >= min_match
    ]

    return render_template(
        "student/jobs.html",
        jobs=job_results,
        search_query=search_query,
        location_query=location_query,
        min_match=min_match,
    )


# ==========================================
# STUDENT: JOB DETAILS
# ==========================================

@app.route("/student/jobs/<int:job_id>")
@login_required
def job_details(job_id):
    if current_user.role != "student":
        flash("This page is for student accounts.", "error")
        return redirect(url_for("admin_dashboard"))

    with get_db_connection() as conn:
        job = conn.execute(
            "SELECT * FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()

    if job is None:
        flash("Job listing not found.", "error")
        return redirect(url_for("explore_jobs"))

    return render_template("student/job_details.html", job=job)



@app.route("/student/jobs/<int:job_id>/apply", methods=["POST"])
@login_required
def track_job_application(job_id):
    if current_user.role != "student":
        flash("This feature is for student accounts only.", "error")
        return redirect(url_for("admin_dashboard"))

    with get_db_connection() as conn:
        job = conn.execute(
            "SELECT id FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()

        if job is None:
            flash("Job listing not found.", "error")
            return redirect(url_for("explore_jobs"))

        existing = conn.execute(
            "SELECT id FROM applications WHERE user_id = ? AND job_id = ?",
            (current_user.id, job_id)
        ).fetchone()

        if existing:
            flash("You are already tracking this application.", "error")
        else:
            conn.execute(
                """
                INSERT INTO applications (user_id, job_id, status)
                VALUES (?, ?, 'Applied')
                """,
                (current_user.id, job_id)
            )
            flash("Job application added to My Applications!", "success")

    return redirect(url_for("my_applications"))


@app.route("/student/applications")
@login_required
def my_applications():
    if current_user.role != "student":
        flash("This page is for student accounts only.", "error")
        return redirect(url_for("admin_dashboard"))

    with get_db_connection() as conn:
        applications = conn.execute(
            """
            SELECT
                applications.id,
                applications.job_id,
                applications.status,
                applications.applied_at,
                jobs.title,
                jobs.company,
                jobs.location
            FROM applications
            JOIN jobs ON applications.job_id = jobs.id
            WHERE applications.user_id = ?
            ORDER BY applications.applied_at DESC
            """,
            (current_user.id,)
        ).fetchall()

    return render_template(
        "student/applications.html",
        applications=applications
    )


# ==========================================
# STUDENT: SKILL MATCHING ANALYZER
# ==========================================
@app.route("/student/jobs/<int:job_id>/analyze")
@login_required
def analyze_job_skills(job_id):

    if current_user.role != "student":
        flash("This page is for student accounts.", "error")
        return redirect(url_for("admin_dashboard"))

    # Get the selected job
    with get_db_connection() as conn:
        job = conn.execute(
            "SELECT * FROM jobs WHERE id = ?",
            (job_id,)
        ).fetchone()

        # Get the student's profile
        profile = conn.execute(
            "SELECT * FROM student_profiles WHERE user_id = ?",
            (current_user.id,)
        ).fetchone()

    if job is None:
        flash("Job listing not found.", "error")
        return redirect(url_for("explore_jobs"))

    # Read skills from the job listing
    required_text = job["skills_required"] or ""

    # Read skills from the student profile
    student_text = ""

    if profile:
        profile_columns = profile.keys()

        # Check common names for the skills field
        for column in (
            "technical_skills",
            "skills",
            "key_skills"
        ):
            if column in profile_columns and profile[column]:
                student_text = str(profile[column])
                break

    # Convert skills into normalized lists
    def normalize_skills(text):
        return list(dict.fromkeys(
            skill.strip().lower()
            for skill in text.replace(";", ",")
                              .replace("\n", ",")
                              .split(",")
            if skill.strip()
        ))

    student_skills = normalize_skills(student_text)
    
    def calculate_job_match(student_skills, required_skills_text):
        """Calculate compatibility between student and job skills."""

        required_skills = normalize_skills(
            required_skills_text or ""
        )

        if not required_skills:
            return {
                "score": 0,
                "matched": [],
                "missing": []
            }

        matched = [
            skill for skill in required_skills
            if skill in student_skills
        ]

        missing = [
            skill for skill in required_skills
            if skill not in student_skills
        ]

        score = round(
            len(matched) / len(required_skills) * 100
        )

        return {
            "score": score,
            "matched": matched,
            "missing": missing
        }
    required_skills = normalize_skills(required_text)
    predicted_career = None
    prediction_probabilities = []

    # Predict a career using the trained ML model
    if career_model is not None and student_skills:
        student_input = " ".join(student_skills)

        predicted_career = career_model.predict(
            [student_input]
        )[0]

        if hasattr(career_model, "predict_proba"):
            probabilities = career_model.predict_proba(
                [student_input]
            )[0]

            classes = career_model.classes_

            prediction_probabilities = sorted(
                [
                    {
                        "career": str(classes[index]),
                        "confidence": round(
                            float(probabilities[index]) * 100, 2
                        )
                    }
                    for index in range(len(classes))
                ],
                key=lambda item: item["confidence"],
                reverse=True
            )
    # Compare student skills with job requirements
    matched_skills = [
        skill for skill in required_skills
        if skill in student_skills # pyright: ignore[reportUndefinedVariable]
    ]

    missing_skills = [
        skill for skill in required_skills
        if skill not in student_skills
    ]

    if required_skills:
        match_percentage = round(
            len(matched_skills) / len(required_skills) * 100
        )
    else:
        match_percentage = 0

    return render_template(
        "student/skill_analysis.html",
        job=job,
        student_skills=student_skills,
        required_skills=required_skills,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        match_percentage=match_percentage
    )


# ==========================================
# STUDENT: CAREER RECOMMENDATIONS
# ==========================================
@app.route("/student/careers")
@login_required
def career_recommendations():

    if current_user.role != "student":
        flash("This page is for student accounts.", "error")
        return redirect(url_for("admin_dashboard"))

    # Get the student's profile
    with get_db_connection() as conn:
        profile = conn.execute(
            "SELECT * FROM student_profiles WHERE user_id = ?",
            (current_user.id,)
        ).fetchone()

    # Read skills from the profile
    student_text = ""

    if profile:
        profile_columns = profile.keys()

        for column in ("technical_skills", "skills", "key_skills"):
            if column in profile_columns and profile[column]:
                student_text = str(profile[column])
                break

    
    def normalize_skills(text):
        """Normalize skill names for consistent career matching."""

        skill_aliases = {
            "js": "javascript",
            "ml": "machine learning",
            "scikit learn": "scikit-learn",
            "scikit_learn": "scikit-learn",
            "powerbi": "power bi",
            "structured query language": "sql",
        }

        normalized = []

        for skill in re.split(r"[,;\n|]+", str(text or "")):
            skill = " ".join(skill.lower().strip().split())

            if not skill:
                continue

            skill = skill_aliases.get(skill, skill)

            if skill not in normalized:
                normalized.append(skill)

        return normalized

    student_skills = normalize_skills(student_text)
    predicted_career = None
    prediction_probabilities = []

    # Predict a likely career path from the student's skill set
    if career_model is not None and student_skills:  # pyright: ignore[reportUndefinedVariable]
        try:
            student_input = " ".join(student_skills)
            predicted_career = str(career_model.predict([student_input])[0])

            if hasattr(career_model, "predict_proba"):
                probabilities = career_model.predict_proba([student_input])[0]
                classes = career_model.classes_

                prediction_probabilities = sorted(
                    [
                        {
                            "career": str(classes[index]),
                            "confidence": round(
                                float(probabilities[index]) * 100, 2
                            ),
                        }
                        for index in range(len(classes))
                    ],
                    key=lambda item: item["confidence"],
                    reverse=True,
                )
        except Exception:
            app.logger.exception("Career prediction failed.")
            predicted_career = None
            prediction_probabilities = []

    # Career roles and their commonly required skills
    career_paths = [
        {
            "title": "Python Developer",
            "description": "Develop applications, scripts, APIs and backend services using Python.",
            "skills": ["python", "sql", "git", "flask", "api"]
        },
        {
            "title": "Web Developer",
            "description": "Build and maintain websites and web applications.",
            "skills": ["html", "css", "javascript", "python", "sql"]
        },
        {
            "title": "Data Analyst",
            "description": "Analyze data and create reports to support business decisions.",
            "skills": ["python", "sql", "excel", "power bi", "statistics"]
        },
        {
            "title": "Machine Learning Engineer",
            "description": "Build and evaluate machine learning models and data-driven systems.",
            "skills": ["python", "statistics", "machine learning", "pandas", "scikit-learn"]
        },
        {
            "title": "Database Developer",
            "description": "Design, query and maintain databases for applications.",
            "skills": ["sql", "database", "mysql", "sqlite", "database design"]
        },
        {
            "title": "Frontend Developer",
            "description": "Create the visual and interactive parts of websites.",
            "skills": ["html", "css", "javascript", "bootstrap", "react"]
        },
        {
            "title": "Software Tester",
            "description": "Test software, identify defects and help improve product quality.",
            "skills": ["testing", "python", "selenium", "sql", "debugging"]
        },
        {
            "title": "Full Stack Developer",
            "description": "Build both the frontend and backend of web applications.",
            "skills": ["html", "css", "javascript", "python", "sql", "flask"]
        }
    ]

    # Rank careers by the percentage of listed skills that match
    recommendations = []

    for career in career_paths:
        required_skills = career["skills"]

        matched = [
            skill for skill in required_skills
            if skill in student_skills  # type: ignore
        ]

        missing = [
            skill for skill in required_skills
            if skill not in student_skills
        ]

        score = round(
            len(matched) / len(required_skills) * 100
        )

        recommendations.append({
            "title": career["title"],
            "description": career["description"],
            "skills": required_skills,
            "matched": matched,
            "missing": missing,
            "score": score
        })

    # Show the best matching careers first
    # Combine skill-match scores with the ML prediction.
    for career in recommendations:
        if predicted_career:
            if career["title"] == predicted_career:
                career["ml_match"] = True
                career["combined_score"] = round(
                    0.7 * career["score"] + 0.3 * 100
                )
            else:
                career["ml_match"] = False
                career["combined_score"] = round(
                    0.7 * career["score"]
                )
        else:
            career["ml_match"] = False
            career["combined_score"] = career["score"]

    recommendations.sort(
        key=lambda career: career["combined_score"],
        reverse=True
    )

    return render_template(
        "student/careers.html",
        recommendations=recommendations,
        student_skills=student_skills,
        predicted_career=predicted_career,
        prediction_probabilities=prediction_probabilities
    )

# ==========================================
# ADMIN: JOB MANAGEMENT
# ==========================================

def admin_only():
    """Return True only for authenticated administrator accounts."""
    if current_user.role != "admin":
        flash("Administrator access is required.", "error")
        return False
    return True


@app.route("/admin/jobs", methods=["GET", "POST"])
@login_required
def admin_jobs():
    if not admin_only():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        company = request.form.get("company", "").strip()
        location = request.form.get("location", "").strip()
        job_type = request.form.get("job_type", "Full-time").strip()
        experience = request.form.get("experience", "Fresher").strip()
        skills_required = request.form.get("skills_required", "").strip()
        description = request.form.get("description", "").strip()
        salary = request.form.get("salary", "").strip()
        application_url = request.form.get("application_url", "").strip()

        fields = {
            "Job title": (title, 150),
            "Company": (company, 150),
            "Location": (location, 150),
            "Job type": (job_type, 50),
            "Experience": (experience, 100),
            "Required skills": (skills_required, 2000),
            "Description": (description, 10000),
            "Salary": (salary, 100),
            "Application URL": (application_url, 1000),
        }

        invalid_field = next(
            (
                name for name, (value, limit) in fields.items()
                if len(value) > limit
            ),
            None,
        )

        if not title or not company:
            flash("Job title and company are required.", "error")
        elif invalid_field:
            flash(f"{invalid_field} is too long.", "error")
        elif application_url and not re.match(
            r"^https?://", application_url, re.IGNORECASE
        ):
            flash("Application URL must start with http:// or https://.", "error")
        else:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO jobs (
                        title, company, location, job_type, experience,
                        skills_required, description, salary, application_url
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        title, company, location, job_type, experience,
                        skills_required, description, salary, application_url,
                    ),
                )
            flash("Job listing added successfully.", "success")
            return redirect(url_for("admin_jobs"))

    with get_db_connection() as conn:
        jobs = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC, id DESC"
        ).fetchall()

    return render_template(
        "admin/jobs.html",
        jobs=jobs,
        edit_job=None,
    )


@app.route("/admin/jobs/<int:job_id>/edit", methods=["GET", "POST"])
@login_required
def admin_edit_job(job_id):
    if not admin_only():
        return redirect(url_for("dashboard"))

    with get_db_connection() as conn:
        job = conn.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()

    if job is None:
        flash("Job listing not found.", "error")
        return redirect(url_for("admin_jobs"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        company = request.form.get("company", "").strip()
        location = request.form.get("location", "").strip()
        job_type = request.form.get("job_type", "Full-time").strip()
        experience = request.form.get("experience", "Fresher").strip()
        skills_required = request.form.get("skills_required", "").strip()
        description = request.form.get("description", "").strip()
        salary = request.form.get("salary", "").strip()
        application_url = request.form.get("application_url", "").strip()

        fields = {
            "Job title": (title, 150),
            "Company": (company, 150),
            "Location": (location, 150),
            "Job type": (job_type, 50),
            "Experience": (experience, 100),
            "Required skills": (skills_required, 2000),
            "Description": (description, 10000),
            "Salary": (salary, 100),
            "Application URL": (application_url, 1000),
        }

        invalid_field = next(
            (
                name for name, (value, limit) in fields.items()
                if len(value) > limit
            ),
            None,
        )

        if not title or not company:
            flash("Job title and company are required.", "error")
        elif invalid_field:
            flash(f"{invalid_field} is too long.", "error")
        elif application_url and not re.match(
            r"^https?://", application_url, re.IGNORECASE
        ):
            flash("Application URL must start with http:// or https://.", "error")
        else:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    UPDATE jobs
                    SET title = ?, company = ?, location = ?,
                        job_type = ?, experience = ?, skills_required = ?,
                        description = ?, salary = ?, application_url = ?
                    WHERE id = ?
                    """,
                    (
                        title, company, location, job_type, experience,
                        skills_required, description, salary, application_url,
                        job_id,
                    ),
                )
            flash("Job listing updated successfully.", "success")
            return redirect(url_for("admin_jobs"))

    with get_db_connection() as conn:
        jobs = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC, id DESC"
        ).fetchall()

    return render_template(
        "admin/jobs.html",
        jobs=jobs,
        edit_job=job,
    )


@app.route("/admin/jobs/<int:job_id>/delete", methods=["POST"])
@login_required
def admin_delete_job(job_id):
    if not admin_only():
        return redirect(url_for("dashboard"))

    with get_db_connection() as conn:
        result = conn.execute(
            "DELETE FROM jobs WHERE id = ?", (job_id,)
        )

    if result.rowcount:
        flash("Job listing deleted successfully.", "success")
    else:
        flash("Job listing not found.", "error")

    return redirect(url_for("admin_jobs"))


# ==================================================
# STUDENT FEATURE PLACEHOLDER PAGES
# ==================================================

STUDENT_FEATURES = {
    "profile": {
        "title": "My Profile",
        "description": "Manage your education, skills, projects, internships, and certifications.",
    },
    "resume": {
        "title": "Resume Builder",
        "description": "Create and download your professional resume.",
    },
    "jobs": {
        "title": "Explore Jobs",
        "description": "Discover job opportunities that match your qualifications.",
    },
    "analyzer": {
        "title": "Skill Analyzer",
        "description": "Compare your skills with job requirements and identify gaps.",
    },
    "careers": {
        "title": "Career Recommendations",
        "description": "Explore career paths related to your skills and interests.",
    },
    "applications": {
        "title": "My Applications",
        "description": "Track your job applications and their status.",
    },
}


@app.route("/student/feature/<feature>")
@login_required
def student_feature(feature):
    if current_user.role != "student":
        flash("You are not authorized to access the student area.", "error")
        return redirect(url_for("admin_dashboard"))

    feature_info = STUDENT_FEATURES.get(feature)
    if feature_info is None:
        flash("The requested page could not be found.", "error")
        return redirect(url_for("dashboard"))

    # Send real Profile and Resume links to their implemented pages.
    if feature == "profile":
        return redirect(url_for("student_profile"))
    if feature == "resume":
        return redirect(url_for("resume_builder"))

    return render_template("student/coming_soon.html", feature=feature_info)


# ==================================================
# ADMIN DASHBOARD
# ==================================================

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        flash("You are not authorized to access the admin area.", "error")
        return redirect(url_for("dashboard"))

    with get_db_connection() as conn:

        # Get all registered users for the admin dashboard.
        users = conn.execute(
            """
            SELECT id, full_name, email, role, created_at
            FROM users
            ORDER BY created_at DESC
            """
        ).fetchall()

        # Calculate the six application statistics.
        stats_row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(
                    SUM(CASE WHEN status = 'Applied' THEN 1 ELSE 0 END),
                    0
                ) AS applied,
                COALESCE(
                    SUM(CASE WHEN status = 'Shortlisted' THEN 1 ELSE 0 END),
                    0
                ) AS shortlisted,
                COALESCE(
                    SUM(CASE WHEN status = 'Interview' THEN 1 ELSE 0 END),
                    0
                ) AS interviews,
                COALESCE(
                    SUM(CASE WHEN status = 'Selected' THEN 1 ELSE 0 END),
                    0
                ) AS selected,
                COALESCE(
                    SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END),
                    0
                ) AS rejected
            FROM applications
            """
        ).fetchone()

    # Convert the SQLite result into a dictionary for the template.
    application_stats = dict(stats_row)

    return render_template(
        "admin/dashboard.html",
        users=users,
        application_stats=application_stats
    )


# ==================================================
# CONTEXT PROCESSOR: UNREAD NOTIFICATIONS
# ==================================================

@app.context_processor
def inject_unread_notifications():
    count = 0

    if current_user.is_authenticated and current_user.role == "student":
        with get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM notifications
                WHERE user_id = ? AND is_read = 0
                """,
                (current_user.id,)
            ).fetchone()

            count = row["total"]

    return {"unread_notifications": count}


# ==================================================
# ADMIN: MANAGE APPLICATIONS
# ==================================================

@app.route("/admin/applications")
@login_required
def admin_applications():
    if current_user.role != "admin":
        flash("Access denied. Admins only.", "error")
        return redirect(url_for("dashboard"))

    with get_db_connection() as conn:
        applications = conn.execute("""
            SELECT
                applications.id,
                applications.user_id,
                applications.job_id,
                applications.status,
                applications.applied_at,
                users.email,
                jobs.title,
                jobs.company
            FROM applications
            JOIN users ON applications.user_id = users.id
            JOIN jobs ON applications.job_id = jobs.id
            ORDER BY applications.applied_at DESC
        """).fetchall()

    return render_template(
        "admin/applications.html",
        applications=applications
    )



@app.route(
    "/admin/applications/<int:application_id>/update",
    methods=["POST"]
)
@login_required
def update_application_status(application_id):
    if current_user.role != "admin":
        flash("Access denied. Admins only.", "error")
        return redirect(url_for("dashboard"))

    allowed_statuses = [
        "Applied",
        "Shortlisted",
        "Interview",
        "Selected",
        "Rejected"
    ]

    new_status = request.form.get("status", "").strip()

    if new_status not in allowed_statuses:
        flash("Invalid application status.", "error")
        return redirect(url_for("admin_applications"))

    with get_db_connection() as conn:
        application = conn.execute(
            "SELECT id, user_id, status FROM applications WHERE id = ?",
            (application_id,)
        ).fetchone()

        if application is None:
            flash("Application not found.", "error")
            return redirect(url_for("admin_applications"))

        if application["status"] != new_status:
            conn.execute(
                "UPDATE applications SET status = ? WHERE id = ?",
                (new_status, application_id)
            )
            conn.execute(
                "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
                (
                    application["user_id"],
                    f"Your application status has been updated to {new_status}."
                )
            )
            flash("Application status updated successfully!", "success")
        else:
            flash("Application already has this status.", "info")

    return redirect(url_for("admin_applications"))

#student notifications


@app.route("/student/notifications")
@login_required
def student_notifications():
    if getattr(current_user, "role", None) != "student":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    with get_db_connection() as conn:
        notifications = conn.execute(
            """
            SELECT id, message, is_read, created_at
            FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (current_user.id,)
        ).fetchall()

        conn.execute(
    """
    UPDATE notifications
    SET is_read = 1
    WHERE user_id = ?
    """,
    (current_user.id,)
)

    return render_template(
        "student/notifications.html",
        notifications=notifications
    )


# ==================================================
# LOGOUT
# ==================================================


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("home"))

# ==================================================
# INITIALIZE DATABASE AND START APPLICATION
# ==================================================

init_db()

if __name__ == "__main__":
    app.run(debug=True)
