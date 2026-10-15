import asyncio
import json
import sys
import traceback
from pathlib import Path

import pandas as pd
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from backend.recovery import execute_with_retry
from backend.state_manager import (
    create_task_state,
    load_task_state,
    save_task_state,
    update_step_status,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"


async def call_mcp_tool(tool_name, arguments):
    """Call one MCP tool using a fresh stdio session."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "backend.mcp_server"],
        cwd=str(PROJECT_ROOT),
    )
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                if result.isError:
                    details = "\\n".join(
                        item.text for item in result.content if hasattr(item, "text")
                    )
                    raise RuntimeError(
                        f"MCP tool '{tool_name}' failed: {details or 'No details'}"
                    )
                parts = [
                    item.text for item in result.content if hasattr(item, "text")
                ]
                if not parts:
                    raise RuntimeError(f"MCP tool '{tool_name}' returned no result.")
                try:
                    return json.loads(parts[0])
                except json.JSONDecodeError:
                    return parts[0]
    except Exception as error:
        print(f"MCP tool {tool_name!r} failed: {type(error).__name__}: {error}")
        if isinstance(error, BaseExceptionGroup):
            for nested in error.exceptions:
                print(f"Nested MCP error: {type(nested).__name__}: {nested}")
        raise


def call_mcp_with_retry(tool_name, arguments, max_attempts=3):
    """Retry a tool call with bounded attempts and a short delay."""
    outcome = execute_with_retry(
        lambda: asyncio.run(call_mcp_tool(tool_name, arguments)),
        action_name=f"MCP:{tool_name}",
        max_attempts=max_attempts,
        delay_seconds=1,
    )
    if outcome["status"] != "completed":
        raise RuntimeError(
            f"{tool_name} failed after {outcome['attempts']} attempts: {outcome['error']}"
        )
    return outcome["result"], outcome["attempts"]


def get_requested_count(user_request):
    raw = user_request.get("count", 3)
    if isinstance(raw, bool):
        raise ValueError("The number of opportunities must be a positive integer.")
    try:
        count = int(raw)
    except (TypeError, ValueError):
        raise ValueError("The number of opportunities must be a positive integer.")
    if isinstance(raw, float) and not raw.is_integer():
        raise ValueError("The number of opportunities must be a whole number.")
    if isinstance(raw, str) and raw.strip() != str(count):
        raise ValueError("Enter the number of opportunities as a whole number.")
    if not 1 <= count <= 20:
        raise ValueError("Choose between 1 and 20 opportunities.")
    return count


def _step_done(state, name):
    return state.get("steps", {}).get(name, {}).get("status") == "completed"


def _step_output(state, name):
    return state.get("steps", {}).get(name, {}).get("output") or {}


def _file_from_result(value):
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def run_agent(user_request):
    """Start a new Opportunity OS task."""
    state = create_task_state(user_request)
    return _run_task(state)


def resume_agent(task_id):
    """Resume a saved task, reusing completed steps with saved outputs."""
    state = load_task_state(task_id)
    if not state:
        return {"status": "failed", "task_id": str(task_id), "error": "Task ID was not found."}
    if state.get("status") == "completed":
        return _build_completed_response(state)
    state["status"] = "running"
    save_task_state(state)
    return _run_task(state)


def get_task_status(task_id):
    return load_task_state(task_id)


def _build_completed_response(state):
    ranked_output = _step_output(state, "verify_listings")
    opportunities = ranked_output.get("opportunities", [])
    sheet = _step_output(state, "save_spreadsheet")
    email = _step_output(state, "draft_email")
    verification = _step_output(state, "verify_results")
    return {
        "status": state.get("status", "unknown"),
        "task_id": state.get("task_id"),
        "requested_count": state.get("user_request", {}).get("count", 3),
        "opportunities": opportunities,
        "spreadsheet_path": sheet.get("file_path"),
        "email_draft": email,
        "verification": verification,
    }


def _run_task(task_state):
    task_id = task_state["task_id"]
    request = task_state.get("user_request", {})
    current_step = "research"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        requested_count = get_requested_count(request)
        profile = {
            "degree": request.get("degree", "Computer Science"),
            "year": int(request.get("year", 3)),
            "skills": request.get("skills", []),
            "location": request.get("location", "India"),
            "work_mode": request.get("work_mode", "Remote"),
        }
        print(f"\\nOPPORTUNITY OS | Task {task_id}")

        # 1. Research. Reuse a saved result when available.
        current_step = "research"
        research_output = _step_output(task_state, current_step)
        opportunities = research_output.get("opportunities", [])
        if not (_step_done(task_state, current_step) and opportunities):
            update_step_status(task_state, current_step, "running")
            result, attempts = call_mcp_with_retry("research_internships", profile)
            opportunities = result.get("opportunities", [])
            if not opportunities:
                raise RuntimeError("Research returned no usable internship leads.")
            update_step_status(task_state, current_step, "completed", {
                "count": len(opportunities),
                "data_type": result.get("data_type", "Live web search results"),
                "opportunities": opportunities,
                "attempts_used": attempts,
            })

        # 2. Rank.
        current_step = "filter_and_rank"
        ranking_output = _step_output(task_state, current_step)
        ranked = ranking_output.get("opportunities", [])
        if not (_step_done(task_state, current_step) and ranked):
            update_step_status(task_state, current_step, "running")
            result, attempts = call_mcp_with_retry(
                "rank_internships", {"opportunities": opportunities, **profile}
            )
            all_ranked = result.get("ranked_opportunities", [])
            if not all_ranked:
                raise RuntimeError("Ranking returned no opportunities.")
            ranked = all_ranked[:requested_count]
            update_step_status(task_state, current_step, "completed", {
                "requested_count": requested_count,
                "available_ranked_count": len(all_ranked),
                "selected_count": len(ranked),
                "opportunities": ranked,
                "attempts_used": attempts,
            })

        # 3. Inspect each selected listing. Inspection is preliminary evidence only.
        current_step = "verify_listings"
        verification_output = _step_output(task_state, current_step)
        checked = verification_output.get("opportunities", [])
        if not (_step_done(task_state, current_step) and checked):
            update_step_status(task_state, current_step, "running")
            checked = []
            for item in ranked:
                listing = dict(item)
                url = listing.get("application_url") or listing.get("url")
                if not url:
                    listing["listing_inspection"] = {
                        "verification_status": "missing_url",
                        "evidence": ["No listing URL was available to inspect."],
                    }
                    listing["verification_status"] = "missing_url"
                    checked.append(listing)
                    continue
                try:
                    inspection, attempts = call_mcp_with_retry(
                        "verify_internship_listing", {"url": url}, max_attempts=2
                    )
                    listing["listing_inspection"] = inspection
                    listing["verification_status"] = inspection.get(
                        "verification_status", "unverified"
                    )
                    listing["verification_attempts"] = attempts
                except Exception as error:
                    # One inaccessible listing should not destroy the whole search.
                    listing["listing_inspection"] = {
                        "verification_status": "inspection_failed",
                        "evidence": [f"Inspection could not be completed: {type(error).__name__}"],
                    }
                    listing["verification_status"] = "inspection_failed"
                # Never upgrade these fields from automated page-text inspection.
                listing["active_vacancy_confirmed"] = False
                listing["eligibility_verified"] = False
                checked.append(listing)
            update_step_status(task_state, current_step, "completed", {
                "opportunities": checked,
                "checked_count": len(checked),
                "note": "Page inspection is preliminary and does not confirm an active vacancy.",
            })

        # 4. Save spreadsheet. Re-create if saved file is missing or invalid.
        current_step = "save_spreadsheet"
        sheet_output = _step_output(task_state, current_step)
        sheet_path = _file_from_result(sheet_output["file_path"]) if sheet_output.get("file_path") else None
        sheet_valid = False
        if _step_done(task_state, current_step) and sheet_path and sheet_path.exists():
            try:
                sheet_valid = len(pd.read_excel(sheet_path)) == len(checked)
            except Exception:
                sheet_valid = False
        if not sheet_valid:
            update_step_status(task_state, current_step, "running")
            result, attempts = call_mcp_with_retry(
                "save_internships_to_spreadsheet", {"opportunities": checked}
            )
            sheet_path = _file_from_result(result["file_path"])
            if not result.get("file_exists") or not sheet_path.exists():
                raise RuntimeError("Spreadsheet tool did not create the expected file.")
            update_step_status(task_state, current_step, "completed", {
                "file_path": str(sheet_path),
                "expected_rows": len(checked),
                "attempts_used": attempts,
            })

        # 5. Draft email. Drafting only; never send.
        current_step = "draft_email"
        email_output = _step_output(task_state, current_step)
        email_path = _file_from_result(email_output["file_path"]) if email_output.get("file_path") else None
        email_valid = bool(
            _step_done(task_state, current_step)
            and email_path
            and email_path.exists()
            and email_path.read_text(encoding="utf-8").strip()
        )
        if not email_valid:
            update_step_status(task_state, current_step, "running")
            email_output, attempts = call_mcp_with_retry(
                "draft_application_email",
                {
                    "degree": profile["degree"],
                    "year": profile["year"],
                    "skills": profile["skills"],
                    "internship": checked[0],
                },
            )
            if email_output.get("email_sent") is not False:
                raise RuntimeError("Safety check failed: email must never be sent automatically.")
            email_path = _file_from_result(email_output["file_path"])
            if not email_path.exists() or not email_path.read_text(encoding="utf-8").strip():
                raise RuntimeError("The email draft was not saved or is empty.")
            email_output["attempts_used"] = attempts
            update_step_status(task_state, current_step, "completed", email_output)

        # 6. Verify real outputs and task consistency.
        current_step = "verify_results"
        verification_output = _step_output(task_state, current_step)
        if not (_step_done(task_state, current_step) and verification_output.get("spreadsheet_verified")):
            update_step_status(task_state, current_step, "running")
            if not sheet_path or not sheet_path.exists():
                raise RuntimeError("Final verification failed: spreadsheet is missing.")
            saved_df = pd.read_excel(sheet_path)
            if len(saved_df) != len(checked):
                raise RuntimeError(
                    f"Spreadsheet has {len(saved_df)} rows; expected {len(checked)}."
                )
            if not email_path or not email_path.exists() or not email_path.read_text(encoding="utf-8").strip():
                raise RuntimeError("Final verification failed: email draft is missing or empty.")
            verification_output = {
                "spreadsheet_verified": True,
                "spreadsheet_rows": len(saved_df),
                "expected_rows": len(checked),
                "email_draft_verified": True,
                "email_sent": False,
                "listing_pages_inspected": len(checked),
                "active_vacancies_confirmed": 0,
                "eligibility_verified": False,
                "notes": "Automated webpage inspection is preliminary; active vacancies and eligibility are not confirmed.",
            }
            update_step_status(task_state, current_step, "completed", verification_output)

        task_state["status"] = "completed"
        task_state["current_step"] = None
        save_task_state(task_state)
        response = _build_completed_response(task_state)
        print(f"\\nTask completed: {task_id}")
        print(f"Spreadsheet: {response.get('spreadsheet_path')}")
        print(f"Email draft: {email_path} (not sent)")
        return response

    except Exception as error:
        print(f"\\nTASK FAILED at {current_step}: {type(error).__name__}: {error}")
        task_state["status"] = "failed"
        task_state["current_step"] = current_step
        task_state.setdefault("errors", []).append({
            "step": current_step,
            "message": f"{type(error).__name__}: {error}",
        })
        # Mark the currently running step failed so resume knows where to continue.
        if current_step in task_state.get("steps", {}):
            step = task_state["steps"][current_step]
            if step.get("status") == "running":
                step["status"] = "failed"
                step["error"] = str(error)
        save_task_state(task_state)
        return {
            "status": "failed",
            "task_id": task_id,
            "current_step": current_step,
            "error": f"{type(error).__name__}: {error}",
        }
