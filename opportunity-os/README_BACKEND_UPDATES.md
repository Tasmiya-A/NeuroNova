# Opportunity OS backend updates

## Files updated
- `backend/agent.py`: retries MCP calls, inspects each selected listing, validates outputs, and resumes from persisted completed steps.
- `backend/state_manager.py`: atomic state saves, safe task-ID loading, and migration of older task state files.
- `backend/spreadsheet.py`: exports all selected results and includes preliminary verification status.
- `backend/email_draft.py`: fixes ordinal year formatting and explicitly marks the email as an unsent draft.
- `backend/api.py`: FastAPI endpoints for starting tasks, checking status, resuming failed tasks, and downloading generated files.
- `requirements.txt`: dependencies for the backend and API.

The existing `backend/mcp_server.py`, `backend/verification.py`, `backend/research.py`, `backend/ranking.py`, and `backend/recovery.py` are retained. `mcp_server.py` already exposes `verify_internship_listing`.

## Install
From the project root in PowerShell, with your virtual environment activated:

```powershell
pip install -r requirements.txt
```

## Run the existing CLI agent
```powershell
python -m backend.test_agent
```

## Run the API
```powershell
uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload
```

Open `http://127.0.0.1:8000/docs` to try the API.

## API routes
- `GET /api/health` — health check.
- `POST /api/tasks` — start a task. JSON example:
  ```json
  {
    "degree": "Computer Science",
    "year": 3,
    "skills": ["Python", "Machine Learning", "SQL"],
    "location": "India",
    "work_mode": "Remote",
    "count": 3
  }
  ```
  Returns HTTP 202 with a `task_id`.
- `GET /api/tasks/{task_id}` — read task state and progress.
- `POST /api/tasks/{task_id}/resume` — resume a failed/incomplete task.
- `GET /api/files/{filename}` — download an output such as `mcp_internships.xlsx` or `application_email.txt`.

## Important behavior
- Webpage inspection is preliminary evidence only. It does not prove a vacancy is active, genuine, or suitable.
- Eligibility is never marked verified by the current automated checks.
- Emails are drafted locally and never sent.
- The API is intended for a local hackathon prototype. It has no authentication and should not be exposed publicly without security hardening.
- For resume behavior, saved research and completed outputs are reused when their stored data/files pass basic checks. An interrupted step is retried.
