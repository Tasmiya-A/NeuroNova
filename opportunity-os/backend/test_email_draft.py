from pathlib import Path

from backend.research import search_opportunities
from backend.ranking import rank_opportunities
from backend.email_draft import create_email_draft


# Student profile.
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


# Step 1: Collect internship opportunities.
opportunities = search_opportunities(user_request)


# Step 2: Rank them.
ranked_opportunities = rank_opportunities(
    opportunities,
    user_request
)


# Step 3: Select the highest-ranked opportunity.
best_internship = ranked_opportunities[0]


# Step 4: Draft a personalized email.
result = create_email_draft(
    user_request,
    best_internship
)


# Step 5: Verify the output.
assert Path(result["file_path"]).exists()
assert result["status"] == "drafted"
assert best_internship["company"] in result["subject"]

print("\nGenerated email subject:")
print(result["subject"])

print("\nGenerated email body:")
print(result["body"])

print("\nEmail draft location:")
print(result["file_path"])

print("\nSUCCESS: Email-drafting module is working correctly!")