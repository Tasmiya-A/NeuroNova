from backend.state_manager import (
    create_task_state,
    update_step_status,
    load_task_state
)


# Example user request
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


# 1. Create a task
task = create_task_state(user_request)

print("Task created successfully!")
print("Task ID:", task["task_id"])


# 2. Mark research as completed
update_step_status(
    task,
    "research",
    "completed",
    output={"message": "Research test completed"}
)

print("\nResearch marked as completed.")


# 3. Load the saved task again
saved_task = load_task_state(task["task_id"])

print("Task loaded successfully!")
print("Research status:", saved_task["steps"]["research"]["status"])
print("Research output:", saved_task["steps"]["research"]["output"])


# 4. Check that the saved status is correct
assert saved_task["steps"]["research"]["status"] == "completed"

print("\nSUCCESS: Task state manager is working correctly!")