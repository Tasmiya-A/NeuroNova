import json
import os
import time
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TASKS_DIR = DATA_DIR / "tasks"

_SAVE_LOCK = threading.RLock()

STEP_NAMES = (
    "research",
    "filter_and_rank",
    "verify_listings",
    "save_spreadsheet",
    "draft_email",
    "verify_results",
)


def get_current_time():
    return datetime.now(timezone.utc).isoformat()


def _default_step():
    return {"status": "pending", "attempts": 0, "output": None, "error": None}


def create_task_state(user_request):
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    task_id = str(uuid.uuid4())
    state = {
        "task_id": task_id,
        "status": "running",
        "user_request": user_request,
        "created_at": get_current_time(),
        "updated_at": get_current_time(),
        "current_step": None,
        "steps": {name: _default_step() for name in STEP_NAMES},
        "errors": [],
    }
    save_task_state(state)
    return state


def save_task_state(task_state):
    """Persist task state safely on Windows, including concurrent status updates."""
    with _SAVE_LOCK:
        task_state["updated_at"] = get_current_time()
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        path = TASKS_DIR / f"{task_state['task_id']}.json"
        # A unique temp file avoids collisions when more than one update happens
        # close together. os.replace is retried because Windows scanners/readers
        # can briefly hold a handle to the destination file.
        temp_path = TASKS_DIR / f"{task_state['task_id']}.{uuid.uuid4().hex}.tmp"
        try:
            temp_path.write_text(
                json.dumps(task_state, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            last_error = None
            for attempt in range(6):
                try:
                    os.replace(temp_path, path)
                    last_error = None
                    break
                except PermissionError as exc:
                    last_error = exc
                    if attempt < 5:
                        time.sleep(0.1 * (attempt + 1))
            if last_error is not None:
                raise last_error
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def load_task_state(task_id):
    # Treat task IDs as UUIDs to prevent path traversal.
    try:
        normalized_id = str(uuid.UUID(str(task_id)))
    except (ValueError, TypeError, AttributeError):
        return None

    path = TASKS_DIR / f"{normalized_id}.json"
    if not path.exists():
        return None

    state = json.loads(path.read_text(encoding="utf-8"))
    state.setdefault("steps", {})
    for name in STEP_NAMES:
        state["steps"].setdefault(name, _default_step())
    state.setdefault("errors", [])
    state.setdefault("user_request", {})
    state.setdefault("status", "failed")
    state.setdefault("task_id", normalized_id)
    return state


def update_step_status(task_state, step_name, status, output=None, error=None):
    if step_name not in task_state["steps"]:
        task_state["steps"][step_name] = _default_step()

    step = task_state["steps"][step_name]
    step["status"] = status
    task_state["current_step"] = step_name

    if status == "running":
        step["attempts"] = int(step.get("attempts", 0)) + 1
        step["error"] = None

    if output is not None:
        step["output"] = output

    if error is not None:
        step["error"] = str(error)
        task_state.setdefault("errors", []).append({
            "step": step_name,
            "message": str(error),
            "time": get_current_time(),
        })

    save_task_state(task_state)
    return task_state
