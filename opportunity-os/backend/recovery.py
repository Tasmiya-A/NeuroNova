import time
from typing import Callable, Any


def execute_with_retry(
    action: Callable,
    action_name: str,
    max_attempts: int = 3,
    delay_seconds: int = 1
) -> dict:
    """
    Execute an action and retry it if it fails.

    The action can be attempted up to max_attempts times.
    A successful result is returned immediately.
    """

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    attempts = 0
    last_error = None

    while attempts < max_attempts:
        attempts += 1

        print(
            f"[{action_name}] Attempt "
            f"{attempts}/{max_attempts}"
        )

        try:
            result = action()

            print(f"[{action_name}] Completed successfully.")

            return {
                "status": "completed",
                "attempts": attempts,
                "result": result,
                "error": None
            }

        except Exception as error:
            last_error = f"{type(error).__name__}: {error}"

            print(
                f"[{action_name}] Failed: {last_error}"
            )

            if attempts < max_attempts:
                print(
                    f"[{action_name}] Retrying in "
                    f"{delay_seconds} second(s)..."
                )

                time.sleep(delay_seconds)

    print(f"[{action_name}] All attempts failed.")

    return {
        "status": "failed",
        "attempts": attempts,
        "result": None,
        "error": last_error
    }