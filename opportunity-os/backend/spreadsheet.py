from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"


def save_spreadsheet(opportunities, output_path=None):
    """Save all supplied ranked opportunities to an Excel file and verify it."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        output_path = OUTPUT_DIR / "internships.xlsx"
    else:
        output_path = Path(output_path)
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for rank, item in enumerate(opportunities, start=1):
        inspection = item.get("listing_inspection") or {}
        rows.append({
            "Rank": rank,
            "Internship Title": item.get("title", ""),
            "Company": item.get("company", ""),
            "Location": item.get("location", ""),
            "Work Mode": item.get("work_mode", ""),
            "Required Skills": ", ".join(item.get("required_skills", []) or []),
            "Matched Skills": ", ".join(item.get("matched_skills", []) or []),
            "Eligibility": item.get("eligibility", ""),
            "Experience": item.get("experience", ""),
            "Match Score": item.get("score", ""),
            "Verification Status": item.get("verification_status", "unverified"),
            "Page Reachable": inspection.get("page_reachable", False),
            "Page Title": inspection.get("page_title", ""),
            "Application URL": item.get("application_url") or item.get("url", ""),
            "Source": item.get("source", ""),
        })

    dataframe = pd.DataFrame(rows)
    dataframe.to_excel(output_path, index=False, engine="openpyxl")

    if not output_path.exists():
        raise RuntimeError("Excel file was not created.")
    saved = pd.read_excel(output_path)
    if len(saved) != len(opportunities):
        raise RuntimeError(
            f"Spreadsheet row count mismatch: expected {len(opportunities)}, got {len(saved)}."
        )

    print(f"Spreadsheet saved and verified: {output_path}")
    return str(output_path)
