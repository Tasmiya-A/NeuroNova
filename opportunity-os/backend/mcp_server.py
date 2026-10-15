from pathlib import Path

from mcp.server.fastmcp import FastMCP

from backend.research import search_opportunities
from backend.ranking import rank_opportunities
from backend.spreadsheet import save_spreadsheet
from backend.email_draft import create_email_draft
from backend.verification import inspect_internship_listing


mcp = FastMCP("Opportunity OS")


@mcp.tool()
def research_internships(
    degree: str,
    year: int,
    skills: list[str],
    location: str = "India",
    work_mode: str = "Remote"
) -> dict:
    """
    Search the web for internship leads matching a student's profile.

    Search results are live web search results, but individual listings
    and their details have not been independently verified.
    """

    user_request = {
        "degree": degree,
        "year": year,
        "skills": skills,
        "location": location,
        "work_mode": work_mode
    }

    opportunities = search_opportunities(user_request)

    return {
        "count": len(opportunities),
        "opportunities": opportunities,
        "data_type": "Live web search results",
        "verification_status": "Unverified",
        "message": (
            "Results were collected through live web search. "
            "Individual vacancies, employer details, availability, "
            "work mode, and eligibility have not been independently "
            "verified. Check the original listing before applying."
        )
    }


@mcp.tool()
def rank_internships(
    opportunities: list[dict],
    degree: str,
    year: int,
    skills: list[str],
    location: str = "India",
    work_mode: str = "Remote"
) -> dict:
    """
    Rank collected internship leads against a student's profile.

    Ranking indicates estimated relevance, not verified eligibility.
    """

    user_request = {
        "degree": degree,
        "year": year,
        "skills": skills,
        "location": location,
        "work_mode": work_mode
    }

    ranked_opportunities = rank_opportunities(
        opportunities,
        user_request
    )

    return {
        "count": len(ranked_opportunities),
        "ranked_opportunities": ranked_opportunities,
        "ranking_status": "Estimated relevance; eligibility unverified"
    }


@mcp.tool()
def verify_internship_listing(url: str) -> dict:
    """
    Inspect an internship webpage for preliminary evidence about its status.

    Checks whether the page is reachable and looks for internship-related,
    application-related, and possible closure language.

    This is preliminary verification, not proof that a vacancy is genuine,
    currently active, or suitable for the applicant.
    """

    return inspect_internship_listing(url)


@mcp.tool()
def save_internships_to_spreadsheet(
    opportunities: list[dict]
) -> dict:
    """Save internship leads to an Excel spreadsheet."""

    output_dir = (
        Path(__file__).resolve().parent.parent / "outputs"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "mcp_internships.xlsx"

    result = save_spreadsheet(
        opportunities,
        output_path=str(output_path)
    )

    file_exists = output_path.exists()

    return {
        "status": "completed" if file_exists else "failed",
        "file_path": str(output_path),
        "file_exists": file_exists,
        "result": str(result)
    }


@mcp.tool()
def draft_application_email(
    degree: str,
    year: int,
    skills: list[str],
    internship: dict
) -> dict:
    """
    Draft an application email without sending it.

    The user must review the draft before using it.
    """

    user_request = {
        "degree": degree,
        "year": year,
        "skills": skills
    }

    draft = create_email_draft(
        user_request,
        internship
    )

    return {
        "status": "drafted",
        "subject": draft["subject"],
        "body": draft["body"],
        "file_path": str(draft["file_path"]),
        "email_sent": False,
        "review_required": True
    }


if __name__ == "__main__":
    mcp.run()