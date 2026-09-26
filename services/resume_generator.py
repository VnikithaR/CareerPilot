from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)


def generate_resume(user):

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=45,
        leftMargin=45,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    name_style = ParagraphStyle(
        "ResumeName",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1f2937")
    )

    contact_style = ParagraphStyle(
        "Contact",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=9,
        leading=13
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#2563eb"),
        spaceBefore=12,
        spaceAfter=6
    )

    normal_style = ParagraphStyle(
        "NormalResume",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=14
    )

    story = []

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    story.append(
        Paragraph(
            user.name,
            name_style
        )
    )

    contact_items = []

    if user.email:
        contact_items.append(user.email)

    if hasattr(user, "profile") and user.profile:

        if user.profile.phone:
            contact_items.append(user.profile.phone)

        if user.profile.location:
            contact_items.append(user.profile.location)

    contact_text = " | ".join(contact_items)

    if contact_text:
        story.append(
            Paragraph(
                contact_text,
                contact_style
            )
        )

    story.append(Spacer(1, 12))

    # --------------------------------------------------
    # PROFILE / SUMMARY
    # --------------------------------------------------

    if hasattr(user, "profile") and user.profile:

        profile = user.profile

        if profile.summary:

            story.append(
                Paragraph(
                    "PROFILE",
                    section_style
                )
            )

            story.append(
                Paragraph(
                    profile.summary,
                    normal_style
                )
            )

    # --------------------------------------------------
    # EDUCATION
    # --------------------------------------------------

    if user.education:

        story.append(
            Paragraph(
                "EDUCATION",
                section_style
            )
        )

        for education in user.education:

            text = (
                f"<b>{education.degree}</b>"
                f"<br/>{education.institution}"
            )

            if education.year:
                text += f" | {education.year}"

            if education.cgpa:
                text += f" | CGPA: {education.cgpa}"

            story.append(
                Paragraph(
                    text,
                    normal_style
                )
            )

            story.append(
                Spacer(1, 5)
            )

    # --------------------------------------------------
    # SKILLS
    # --------------------------------------------------

    if user.skills:

        story.append(
            Paragraph(
                "SKILLS",
                section_style
            )
        )

        skill_names = [
            skill.skill_name
            for skill in user.skills
        ]

        skills_text = " • ".join(skill_names)

        story.append(
            Paragraph(
                skills_text,
                normal_style
            )
        )

    # --------------------------------------------------
    # PROJECTS
    # --------------------------------------------------

    if user.projects:

        story.append(
            Paragraph(
                "PROJECTS",
                section_style
            )
        )

        for project in user.projects:

            story.append(
                Paragraph(
                    f"<b>{project.title}</b>",
                    normal_style
                )
            )

            if project.description:

                story.append(
                    Paragraph(
                        project.description,
                        normal_style
                    )
                )

            if project.technologies:

                story.append(
                    Paragraph(
                        f"<b>Technologies:</b> "
                        f"{project.technologies}",
                        normal_style
                    )
                )

            story.append(
                Spacer(1, 6)
            )

    # --------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------

    if user.experience:

        story.append(
            Paragraph(
                "EXPERIENCE",
                section_style
            )
        )

        for item in user.experience:

            story.append(
                Paragraph(
                    f"<b>{item.job_title}</b> "
                    f"- {item.company}",
                    normal_style
                )
            )

            dates = []

            if item.start_date:
                dates.append(item.start_date)

            if item.end_date:
                dates.append(item.end_date)

            if dates:

                story.append(
                    Paragraph(
                        " - ".join(dates),
                        normal_style
                    )
                )

            if item.description:

                story.append(
                    Paragraph(
                        item.description,
                        normal_style
                    )
                )

            story.append(
                Spacer(1, 6)
            )

    # --------------------------------------------------
    # CERTIFICATIONS
    # --------------------------------------------------

    if user.certifications:

        story.append(
            Paragraph(
                "CERTIFICATIONS",
                section_style
            )
        )

        for certification in user.certifications:

            text = (
                f"<b>{certification.name}</b>"
            )

            if certification.issuer:
                text += (
                    f" - {certification.issuer}"
                )

            if certification.issue_date:
                text += (
                    f" ({certification.issue_date})"
                )

            story.append(
                Paragraph(
                    text,
                    normal_style
                )
            )

            story.append(
                Spacer(1, 4)
            )

    document.build(story)

    buffer.seek(0)

    return buffer
