from backend.research import search_opportunities
from backend.ranking import rank_opportunities


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


# Step 1: Collect internship records.
opportunities = search_opportunities(user_request)

# Step 2: Rank the collected records.
ranked_opportunities = rank_opportunities(
    opportunities,
    user_request
)

# Step 3: Display the ranking.
print("\nRanked Internship Opportunities\n")

for position, opportunity in enumerate(ranked_opportunities, start=1):

    print(f"Rank: {position}")
    print("Title:", opportunity["title"])
    print("Company:", opportunity["company"])
    print("Score:", opportunity["score"])
    print("Matched skills:", opportunity["matched_skills"])
    print("Reasons:")

    for reason in opportunity["reasons"]:
        print("-", reason)

    print("-" * 45)


# Step 4: Verify the result.
assert len(ranked_opportunities) == len(opportunities)

scores = [item["score"] for item in ranked_opportunities]

assert scores == sorted(scores, reverse=True)

print("\nSUCCESS: Ranking module is working correctly!")