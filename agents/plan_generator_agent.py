"""
Plan Generator Agent
Generates daily coaching plans based on signals and student priorities
"""

import uuid
from datetime import datetime, date
from typing import List, Dict, Tuple, Optional

from models.signal import Signal, Severity, Urgency
from models.plan import DailyPlan, ScheduledSession, DeferredStudent, SessionType
from services.signal_detector_service import get_data_driven_signals
from services.calendar_service import get_available_slots, create_calendar_event, check_time_slot_free
from services.student_service import get_student_profile
from services.llm_service import call_llm
import json
import re


# ----------------------------------
# SESSION TYPE DURATION MAPPING
# ----------------------------------

SESSION_DURATIONS = {
    SessionType.CHECK_IN: 15,
    SessionType.DEEP_DIVE: 45,
    SessionType.CATCH_UP: 30,
    SessionType.EXAM_PREP: 45,
    SessionType.GENERAL: 30,
}

DEFAULT_TIME_SLOTS = [
    ("09:00", "09:30"), ("09:30", "10:00"), ("10:00", "10:30"), ("10:30", "11:00"),
    ("11:00", "11:30"), ("11:30", "12:00"), ("14:00", "14:30"), ("14:30", "15:00"),
    ("15:00", "15:30"), ("15:30", "16:00"), ("16:00", "16:30"), ("16:30", "17:00"),
]

WORKDAY_START = "09:00"
WORKDAY_END = "18:00"


def _get_scheduling_slots(target_date: date) -> List[Tuple[str, str]]:
    """Use calendar slots when available; fall back to default working hours."""
    slots = get_available_slots(target_date)
    if slots:
        return slots
    print("⚠️  Calendar unavailable — using default time slots")
    return DEFAULT_TIME_SLOTS


# ----------------------------------
# SIGNAL PRIORITY SCORING
# ----------------------------------

def calculate_priority_score(signal: Signal) -> int:
    """
    Calculate priority score for a signal (higher = more urgent)
    
    Factors:
    - Urgency: URGENT=300, TODAY=200, CAN_WAIT=100
    - Severity: CRITICAL=300, HIGH=200, MEDIUM=100, LOW=50
    """
    urgency_scores = {
        Urgency.URGENT: 300,
        Urgency.TODAY: 200,
        Urgency.CAN_WAIT: 100,
    }
    
    severity_scores = {
        Severity.CRITICAL: 300,
        Severity.HIGH: 200,
        Severity.MEDIUM: 100,
        Severity.LOW: 50,
    }
    
    urgency_score = urgency_scores.get(signal.urgency, 0)
    severity_score = severity_scores.get(signal.severity, 0)
    
    return urgency_score + severity_score


def rank_signals(signals: List[Signal]) -> List[Signal]:
    """
    Rank signals by priority (highest first)
    """
    return sorted(
        signals,
        key=lambda s: calculate_priority_score(s),
        reverse=True
    )


# ----------------------------------
# SESSION TYPE DETERMINATION
# ----------------------------------

def determine_session_type(signal: Signal) -> SessionType:
    """
    Determine appropriate session type based on signal
    """
    type_map = {
        "performance": SessionType.CHECK_IN,
        "confusion": SessionType.DEEP_DIVE,
        "exam_risk": SessionType.EXAM_PREP,
        "engagement": SessionType.CHECK_IN,
        "attendance": SessionType.CHECK_IN,
    }
    
    session_type = type_map.get(signal.signal_type.value, SessionType.GENERAL)
    
    # Escalate for critical signals
    if signal.severity.value == "critical":
        if session_type == SessionType.CHECK_IN:
            session_type = SessionType.CATCH_UP
    
    return session_type


# ----------------------------------
# PLAN GENERATION ENGINE
# ----------------------------------

def generate_daily_plan(
    target_date: date = None,
    signals: List[Signal] = None,
    max_slots_available: int = 8,  # 8 hours = 480 minutes
) -> DailyPlan:
    """
    Generate a daily coaching plan
    
    Args:
        target_date: Date to plan for (defaults to today)
        signals: List of signals to schedule (defaults to fetch from sheets)
        max_slots_available: Total coaching hours available (in 1-hour units)
    
    Returns:
        DailyPlan object with scheduled and deferred students
    """
    
    if target_date is None:
        target_date = date.today()
    
    # If no signals provided, this would normally fetch from Sheets
    # For now, we'll work with provided signals
    if signals is None:
        signals = []
    
    # Rank signals by priority
    ranked_signals = rank_signals(signals)
    
    # Initialize plan
    plan = DailyPlan(
        plan_id=str(uuid.uuid4()),
        date=target_date,
        generated_at=datetime.now(),
        total_slots_available=max_slots_available * 60,  # Convert to minutes
    )
    
    # Get available time slots
    available_slots = _get_scheduling_slots(target_date)
    print(f"📅 Available slots for {target_date}: {len(available_slots)} slots")
    
    used_slots = set()
    scheduled_signals = {}
    tradeoff_warnings = []
    critical_unassigned = []
    
    # Schedule signals in priority order
    for idx, signal in enumerate(ranked_signals, 1):
        # Skip if already resolved
        if signal.is_resolved:
            continue
        
        # Determine session details
        session_type = determine_session_type(signal)
        duration = SESSION_DURATIONS.get(session_type, 30)
        
        # Get student info
        profile = get_student_profile(signal.student_id)
        student_name = profile.get('name', signal.student_id) if profile else signal.student_id
        
        # Find available slot
        slot_found = False
        for slot_start, slot_end in available_slots:
            # Check if slot is locally used AND check if it's free on calendar
            if slot_start not in used_slots and check_time_slot_free(target_date, slot_start, duration):
                # Schedule this session
                session = ScheduledSession(
                    session_id=str(uuid.uuid4()),
                    student_id=signal.student_id,
                    student_name=student_name,
                    session_type=session_type,
                    reason=signal.description,
                    duration_minutes=duration,
                    priority_rank=len(plan.scheduled_sessions) + 1,
                    time_slot=f"{slot_start}-{slot_end}",
                    is_booked=False,
                    source_signal_ids=[signal.signal_id],
                )
                
                plan.scheduled_sessions.append(session)
                used_slots.add(slot_start)
                scheduled_signals[signal.signal_id] = session
                slot_found = True
                
                print(f"   ✅ {student_name}: {session_type.value} at {slot_start}")
                break
        
        if not slot_found:
            if signal.severity == Severity.CRITICAL:
                critical_unassigned.append(signal)

            # Defer student to tomorrow
            deferred = DeferredStudent(
                student_id=signal.student_id,
                student_name=student_name,
                reason=signal.description,
                severity_level=signal.severity.value,
                deferred_to=date.today()  # TODO: Calculate next available date
            )
            plan.deferred_students.append(deferred)
            print(f"   ⏸️  {student_name}: DEFERRED (no slots)")

    if critical_unassigned:
        plan.metadata['tradeoff_required'] = True
        plan.metadata['tradeoff_message'] = (
            f"{len(critical_unassigned)} critical concern(s) could not be scheduled in today's capacity. "
            "Coach review required before choosing which critical case to prioritize."
        )
        plan.metadata['tradeoff_candidates'] = [
            {
                'signal_id': signal.signal_id,
                'student_id': signal.student_id,
                'description': signal.description,
                'severity': signal.severity.value,
                'urgency': signal.urgency.value,
            }
            for signal in critical_unassigned
        ]
    
    # Update metadata
    plan.update_metadata()
    if tradeoff_warnings:
        plan.metadata['warnings'] = tradeoff_warnings
    
    return plan


def auto_book_calendar_events(plan: DailyPlan) -> DailyPlan:
    """
    Automatically create Google Calendar events for scheduled sessions
    
    Args:
        plan: DailyPlan object with sessions
    
    Returns:
        Updated plan with calendar_event_ids and is_booked flags
    """
    sessions_to_remove = []
    
    for idx, session in enumerate(plan.scheduled_sessions):
        # Parse time slot
        if session.time_slot and '-' in session.time_slot:
            start_time = session.time_slot.split('-')[0]
            
            # Double-check slot is still free before booking
            if not check_time_slot_free(plan.date, start_time, session.duration_minutes):
                print(f"⚠️  Slot {start_time} is no longer available for {session.student_name}")
                sessions_to_remove.append(idx)
                continue
            
            # Create calendar event
            event_id = create_calendar_event(
                student_name=session.student_name,
                session_type=session.session_type.value,
                date_obj=plan.date,
                start_time=start_time,
                duration_minutes=session.duration_minutes,
                description=f"Coaching session: {session.reason}"
            )
            
            if event_id:
                session.calendar_event_id = event_id
                session.is_booked = True
                print(f"✅ Calendar event created for {session.student_name} at {start_time}")
            else:
                print(f"⚠️  Failed to create calendar event for {session.student_name} at {start_time}")
                sessions_to_remove.append(idx)
    
    # Remove sessions that couldn't be booked and defer them
    for idx in sorted(sessions_to_remove, reverse=True):
        session = plan.scheduled_sessions.pop(idx)
        plan.deferred_students.append(
            DeferredStudent(
                student_id=session.student_id,
                student_name=session.student_name,
                severity_level=f"{session.session_type.value}",
                reason=f"Booking conflict: {session.reason}",
                deferred_to="Next available slot"
            )
        )
        print(f"⏸️  Deferred {session.student_name} due to booking conflict")
    
    return plan


def merge_plan_with_new_signals(
    existing_plan: Optional[DailyPlan],
    incoming_signals: List[Signal],
    target_date: date = None,
    max_slots_available: int = 8,
) -> tuple[DailyPlan, dict]:
    """
    Rebuild the plan when a serious concern arrives.

    If there is enough room, the updated plan is returned directly.
    If multiple critical signals compete for limited capacity, the plan
    includes a tradeoff summary and leaves the final call to the coach.
    """
    if target_date is None:
        target_date = date.today()

    current_signals = incoming_signals[:]
    if existing_plan:
        # Preserve the context of the current plan by carrying forward the
        # reasons already scheduled, so the coach sees what changed.
        current_signals.extend([])

    rebuilt_plan = generate_daily_plan(
        target_date=target_date,
        signals=current_signals,
        max_slots_available=max_slots_available,
    )

    critical_count = sum(1 for signal in current_signals if signal.severity == Severity.CRITICAL)
    available_capacity = len(_get_scheduling_slots(target_date))
    tradeoff_needed = critical_count > 1 and available_capacity <= 1

    summary = {
        'tradeoff_required': tradeoff_needed,
        'changed': len(rebuilt_plan.scheduled_sessions),
        'scheduled': [
            {
                'student_id': session.student_id,
                'student_name': session.student_name,
                'time_slot': session.time_slot,
                'reason': session.reason,
                'source_signal_ids': session.source_signal_ids,
            }
            for session in rebuilt_plan.scheduled_sessions
        ],
        'deferred': [
            {
                'student_id': deferred.student_id,
                'student_name': deferred.student_name,
                'reason': deferred.reason,
                'severity_level': deferred.severity_level,
                'deferred_to': str(deferred.deferred_to),
            }
            for deferred in rebuilt_plan.deferred_students
        ],
        'message': rebuilt_plan.metadata.get('tradeoff_message', 'Daily plan updated.'),
    }

    return rebuilt_plan, summary


def revise_plan_for_urgent_signal(
    existing_plan: DailyPlan,
    urgent_signal: Signal
) -> DailyPlan:
    """
    Revise existing plan to accommodate a newly urgent signal
    
    Strategy:
    1. Check if urgent signal's student is already scheduled
    2. If yes, move them to priority position
    3. If no, try to fit them by rearranging lower-priority sessions
    4. Defer lower-priority items if necessary
    
    Args:
        existing_plan: Current DailyPlan
        urgent_signal: New urgent signal to prioritize
    
    Returns:
        Revised DailyPlan
    """
    
    print(f"\n🔄 REVISING PLAN FOR URGENT SIGNAL: {urgent_signal.description}")
    
    # Check if student already scheduled
    scheduled_idx = None
    for idx, session in enumerate(existing_plan.scheduled_sessions):
        if session.student_id == urgent_signal.student_id:
            scheduled_idx = idx
            break
    
    if scheduled_idx is not None:
        # Move to front (highest priority)
        session = existing_plan.scheduled_sessions.pop(scheduled_idx)
        existing_plan.scheduled_sessions.insert(0, session)
        print(f"   ✅ Moved {session.student_name} to priority position")
    else:
        # Try to schedule this new urgent signal
        # For now, just add to beginning
        available_slots = get_available_slots(existing_plan.date)
        
        if available_slots:
            slot_start, slot_end = available_slots[0]
            profile = get_student_profile(urgent_signal.student_id)
            student_name = profile.get('name', urgent_signal.student_id) if profile else urgent_signal.student_id
            
            session_type = determine_session_type(urgent_signal)
            duration = SESSION_DURATIONS.get(session_type, 30)
            
            session = ScheduledSession(
                session_id=str(uuid.uuid4()),
                student_id=urgent_signal.student_id,
                student_name=student_name,
                session_type=session_type,
                reason=urgent_signal.description,
                duration_minutes=duration,
                priority_rank=1,
                time_slot=f"{slot_start}-{slot_end}",
                is_booked=False,
            )
            
            existing_plan.scheduled_sessions.insert(0, session)
            print(f"   ✅ Added {student_name} to plan (priority)")
    
    # Recalculate ranks
    for idx, session in enumerate(existing_plan.scheduled_sessions, 1):
        session.priority_rank = idx
    
    existing_plan.update_metadata()
    return existing_plan


def build_plan_summary(plan: DailyPlan) -> str:
    """
    Generate a human-readable summary of the plan
    """
    summary = f"""
📅 **Daily Plan for {plan.date.strftime('%A, %B %d, %Y')}**

**Scheduled Sessions ({len(plan.scheduled_sessions)}):**
"""
    for session in plan.scheduled_sessions:
        summary += f"\n{session.priority_rank}. {session.student_name} ({session.session_type.value})"
        summary += f"\n   Time: {session.time_slot} | Duration: {session.duration_minutes}m"
        summary += f"\n   Reason: {session.reason}"
        if session.is_booked:
            summary += " ✅ Booked"
        summary += "\n"
    
    if plan.deferred_students:
        summary += f"\n**Deferred ({len(plan.deferred_students)}):**\n"
        for deferred in plan.deferred_students:
            summary += f"\n• {deferred.student_name}"
            summary += f"\n   Reason: {deferred.reason}"
            summary += f"\n   Deferred to: {deferred.deferred_to}\n"
    
    summary += f"\n**Summary:**\n"
    summary += f"• Total sessions: {plan.metadata.get('total_sessions_scheduled', 0)}\n"
    summary += f"• Time utilization: {plan.metadata.get('utilization_percent', 0)}%\n"
    summary += f"• Time remaining: {plan.metadata.get('total_time_remaining_minutes', 0)} min\n"
    
    return summary
