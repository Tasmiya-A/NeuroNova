from backend.recovery import execute_with_retry


# Track how many times our test action runs.
attempt_counter = {
    "count": 0
}


def temporary_failure_action():
    """
    Simulate an action that fails twice
    and succeeds on its third attempt.
    """

    attempt_counter["count"] += 1

    if attempt_counter["count"] < 3:
        raise RuntimeError("Simulated temporary failure")

    return {
        "message": "Action completed successfully"
    }


print("Testing recovery with temporary failures...\n")

result = execute_with_retry(
    action=temporary_failure_action,
    action_name="Test Action",
    max_attempts=3,
    delay_seconds=1
)


print("\nFinal result:", result)

assert result["status"] == "completed"
assert result["attempts"] == 3
assert attempt_counter["count"] == 3

print("\nSUCCESS: Recovery module passed the test!")