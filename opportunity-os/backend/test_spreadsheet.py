from pathlib import Path

from backend.research import search_opportunities
from backend.ranking import rank_opportunities
from backend.spreadsheet import save_spreadsheet


# Example user profile.
user_request = {
    "degree": "B.E. CSE-AIML",
    "year": 3,
    "skills": ["Python", "SQL", "Machine Learning"],
    "preferred_role": "AI/ML Intern",
    "location": "India",
    "work_mode": "Remote",
    "experience": "Beginner",
    "number_of_results": 3
}


# Step 1: Collect sample opportunities.
opportunities = search_opportunities(user_request)


# Step 2: Rank the opportunities.
ranked_opportunities = rank_opportunities(
    opportunities,
    user_request
)


# Step 3: Save the top three to Excel.
file_path = save_spreadsheet(ranked_opportunities)


# Step 4: Verify the generated file.
assert Path(file_path).exists()

print("\nExcel file location:")
print(file_path)

print("\nSUCCESS: Spreadsheet generation is working correctly!")