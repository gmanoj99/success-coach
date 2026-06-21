from typing import Optional
import streamlit as st
from services.load_mem_service import load_full_student_memory
from services.student_service import build_student_context
from services.llm_service import call_llm

try:
    from services import sheets_service
except Exception:
    sheets_service = None


def _resolve_trigger_info(scheduled_session) -> dict:
    trigger = {
        "type": getattr(scheduled_session, "trigger_signal_type", None),
        "description": getattr(scheduled_session, "trigger_signal_description", None),
        "recommended_action": getattr(scheduled_session, "trigger_signal_action", None),
    }

    # Best-effort: enrich from Sheets if description missing and spreadsheet config exists
    try:
        if not trigger["description"] and sheets_service and st.secrets.get("GOOGLE_SPREADSHEET_ID"):
            ids = getattr(scheduled_session, "source_signal_ids", None) or []
            rows = sheets_service.get_signals_for_date(st.secrets.get("GOOGLE_SPREADSHEET_ID"))
            for r in rows:
                if str(r.get("signal_id")) in [str(i) for i in ids]:
                    trigger["type"] = trigger["type"] or r.get("type") or r.get("signal_type")
                    trigger["description"] = trigger["description"] or r.get("description")
                    trigger["recommended_action"] = trigger["recommended_action"] or r.get("recommended_action")
                    break
    except Exception:
        # best-effort only; silence failures
        pass

    return trigger


def generate_pre_meeting_brief(scheduled_session, concise: bool = True) -> str:
    """
    Build a concise pre-meeting brief for a scheduled coaching session.

    Returns a short, actionable text produced by the LLM.
    """
    student_id = getattr(scheduled_session, "student_id", None)
    if not student_id:
        return "No student_id provided for scheduled session."

    memory = load_full_student_memory(student_id, "pre-meeting brief")
    student_context = build_student_context(student_id)

    trigger = _resolve_trigger_info(scheduled_session)
    is_triggered = bool(trigger.get("description") or trigger.get("type"))

    if is_triggered:
        prompt = f"""
You are preparing a concise pre-meeting brief for a student success coach.

Meeting trigger:
Type: {trigger.get('type') or 'N/A'}
Issue: {trigger.get('description') or 'N/A'}
Recommended action: {trigger.get('recommended_action') or 'N/A'}

Student context:
{student_context}

Relevant factual memory:
{memory.get('factual_memory','')}

Recent session history:
{memory.get('session_history','')}

Create a short, actionable brief covering:
1) One-line summary of current academic situation.
2) What changed since the last session (evidence or indicators).
3) Open concerns the coach must check.
4) Two suggested opening questions tailored to this trigger.
5) 2–3 concrete follow-up items and desired outcomes.

Keep it concise and coach-ready.
"""
    else:
        prompt = f"""
You are preparing a concise pre-meeting brief for a routine student check-in.

Student context:
{student_context}

Relevant factual memory:
{memory.get('factual_memory','')}

Recent session history:
{memory.get('session_history','')}

Create a short, actionable brief covering:
1) One-line summary of current academic situation.
2) Key discussion topics and any recent changes.
3) Open concerns to surface.
4) Two suggested opening questions.
5) 2–3 follow-up items and desired outcomes.

Keep it concise and coach-ready.
"""

    return call_llm(prompt, temperature=0.2)
