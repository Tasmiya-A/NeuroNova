from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"


def _ordinal_year(year):
    try:
        number = int(year)
    except (TypeError, ValueError):
        return str(year)
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def create_email_draft(user_request, internship):
    """Create a personalized application email draft; never send it."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    degree = user_request.get("degree", "Computer Science student")
    year = user_request.get("year", "")
    skills = user_request.get("skills", [])
    role = internship.get("title", "Internship")
    company = internship.get("company", "the organization")

    skills_text = ", ".join(skills) if skills else "my technical skills"
    subject = f"Application for {role} - {company}"

    email_body = (
        "Dear Hiring Team,\n\n"
        f"I am writing to express my interest in the {role} position at {company}.\n\n"
        f"I am pursuing {degree}"
    )
    if year not in ("", None):
        email_body += f", currently in my {_ordinal_year(year)} year"
    email_body += (
        f".\n\nMy technical skills include {skills_text}, and I am eager to "
        "apply my knowledge to practical projects while learning from your team.\n\n"
        "I would appreciate the opportunity to be considered for this internship. "
        "I would be happy to provide my resume and any additional information required.\n\n"
        "Thank you for your time and consideration.\n\n"
        "Best regards,\n[Your Name]\n"
    )

    output_path = OUTPUT_DIR / "application_email.txt"
    draft_content = f"Subject: {subject}\n\n{email_body}"
    output_path.write_text(draft_content, encoding="utf-8")

    saved = output_path.read_text(encoding="utf-8")
    if not saved.strip() or saved != draft_content:
        raise RuntimeError("Email draft verification failed.")

    return {
        "subject": subject,
        "body": email_body,
        "file_path": str(output_path),
        "status": "drafted",
        "email_sent": False,
        "review_required": True,
    }
