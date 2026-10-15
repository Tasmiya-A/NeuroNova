from backend.agent import run_agent

user_request = {
    "degree": "Computer Science",
    "year": 3,
    "skills": ["Python", "Machine Learning", "SQL"],
    "location": "India",
    "work_mode": "Remote",
}

result = run_agent(user_request)

print("\nFinal result:")
print(result["status"])

if result["status"] == "failed":
    print("Error:", result["error"])