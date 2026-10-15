from pathlib import Path
import threading

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.agent import _run_task, resume_agent
from backend.state_manager import create_task_state, load_task_state

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = (PROJECT_ROOT / "outputs").resolve()

app = FastAPI(
    title="Opportunity OS API",
    description="API for researching, ranking, and preparing internship applications.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Avoid launching duplicate background work for the same task in this process.
_active_tasks = set()
_active_lock = threading.Lock()


def _run_new_task(state):
    task_id = state["task_id"]
    try:
        _run_task(state)
    finally:
        with _active_lock:
            _active_tasks.discard(task_id)


def _resume_task(task_id):
    try:
        resume_agent(task_id)
    finally:
        with _active_lock:
            _active_tasks.discard(task_id)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Opportunity OS API"}


@app.post("/api/tasks", status_code=202)
def start_task(payload: dict, background_tasks: BackgroundTasks):
    """Start an internship search and return immediately with a task ID."""
    required = ("degree", "year", "skills")
    missing = [key for key in required if key not in payload]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required fields: {', '.join(missing)}",
        )
    if not isinstance(payload["skills"], list):
        raise HTTPException(status_code=422, detail="'skills' must be a list of strings.")
    if not all(isinstance(skill, str) for skill in payload["skills"]):
        raise HTTPException(status_code=422, detail="Every skill must be a string.")

    try:
        int(payload["year"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="'year' must be an integer.")

    state = create_task_state(payload)
    task_id = state["task_id"]
    with _active_lock:
        _active_tasks.add(task_id)
    background_tasks.add_task(_run_new_task, state)
    return {
        "task_id": task_id,
        "status": "running",
        "status_url": f"/api/tasks/{task_id}",
        "message": "Task accepted. Poll the status URL for progress and results.",
    }


@app.get("/api/tasks/{task_id}")
def task_status(task_id: str):
    state = load_task_state(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="Task ID not found.")
    return state


@app.post("/api/tasks/{task_id}/resume", status_code=202)
def resume_existing_task(task_id: str, background_tasks: BackgroundTasks):
    state = load_task_state(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="Task ID not found.")
    if state.get("status") == "completed":
        return {"task_id": task_id, "status": "completed", "message": "Task is already complete."}
    with _active_lock:
        if task_id in _active_tasks:
            return {"task_id": task_id, "status": "running", "message": "Task is already running."}
        _active_tasks.add(task_id)
    background_tasks.add_task(_resume_task, task_id)
    return {"task_id": task_id, "status": "running", "message": "Task resumption started."}


@app.get("/api/files/{filename}")
def download_output(filename: str):
    """Download a generated file from outputs; directory traversal is blocked."""
    candidate = (OUTPUT_DIR / filename).resolve()
    if candidate.parent != OUTPUT_DIR or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Output file not found.")
    if candidate.suffix.lower() not in {".xlsx", ".txt"}:
        raise HTTPException(status_code=404, detail="This file type is not available.")
    return FileResponse(
        path=candidate,
        filename=candidate.name,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if candidate.suffix.lower() == ".xlsx"
            else "text/plain; charset=utf-8"
        ),
    )
