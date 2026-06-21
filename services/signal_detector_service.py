"""
Signal Detection Service
Generates signals/alerts based on:
1. Data-driven rules (low scores, attendance, etc.)
2. LLM analysis of student conversations
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from models.signal import Signal, SignalType, Severity, Urgency
from services.student_service import (
    get_student_profile,
    get_student_scores,
    get_student_attendance,
    get_student_exams,
)
from services.llm_service import call_llm


# ----------------------------------
# DATA-DRIVEN SIGNAL DETECTION
# ----------------------------------

def check_exam_risk_signals(student_id: str) -> List[Signal]:
    """
    Generate signals for students at risk based on exam scores
    
    Rules:
    - Score < 50%: CRITICAL severity, TODAY urgency
    - Score < 70%: HIGH severity, TODAY urgency
    - Score < 85%: MEDIUM severity, CAN_WAIT urgency
    """
    signals = []
    scores = get_student_scores(student_id)
    profile = get_student_profile(student_id)
    student_name = profile.get('name', student_id) if profile else student_id
    
    if not scores:
        return signals
    
    for score_record in scores:
        try:
            score_value = float(score_record.get('score', 0))
            exam_name = score_record.get('exam_name', 'Unknown Exam')
            
            if score_value < 50:
                signal = Signal(
                    signal_id=str(uuid.uuid4()),
                    student_id=student_id,
                    timestamp=datetime.now(),
                    signal_type=SignalType.EXAM_RISK,
                    description=f"Critical: {exam_name} score is {score_value}% (below 50%)",
                    severity=Severity.CRITICAL,
                    urgency=Urgency.URGENT,
                    recommended_action=f"Schedule immediate exam prep session for {exam_name}. Review difficult topics.",
                )
                signals.append(signal)
            
            elif score_value < 70:
                signal = Signal(
                    signal_id=str(uuid.uuid4()),
                    student_id=student_id,
                    timestamp=datetime.now(),
                    signal_type=SignalType.EXAM_RISK,
                    description=f"High: {exam_name} score is {score_value}% (below 70%)",
                    severity=Severity.HIGH,
                    urgency=Urgency.TODAY,
                    recommended_action=f"Schedule exam prep session for {exam_name}. Focus on weak areas.",
                )
                signals.append(signal)
            
            elif score_value < 85:
                signal = Signal(
                    signal_id=str(uuid.uuid4()),
                    student_id=student_id,
                    timestamp=datetime.now(),
                    signal_type=SignalType.PERFORMANCE,
                    description=f"Medium: {exam_name} score is {score_value}% (below 85%)",
                    severity=Severity.MEDIUM,
                    urgency=Urgency.CAN_WAIT,
                    recommended_action=f"Check-in about {exam_name} performance. Discuss improvement strategy.",
                )
                signals.append(signal)
        
        except (ValueError, TypeError):
            continue
    
    return signals


def check_attendance_signals(student_id: str) -> List[Signal]:
    """
    Generate signals for attendance issues
    
    Rules:
    - Attendance < 70%: HIGH severity, TODAY urgency
    - Attendance < 80%: MEDIUM severity, TODAY urgency
    - No session in 7 days: MEDIUM severity, TODAY urgency
    """
    signals = []
    attendance_records = get_student_attendance(student_id)
    profile = get_student_profile(student_id)
    student_name = profile.get('name', student_id) if profile else student_id
    
    if not attendance_records:
        return signals
    
    try:
        # Calculate attendance percentage
        total_sessions = len(attendance_records)
        attended = sum(1 for r in attendance_records if str(r.get('status', '')).lower() == 'present')
        attendance_percent = (attended / total_sessions * 100) if total_sessions > 0 else 0
        
        if attendance_percent < 70:
            signal = Signal(
                signal_id=str(uuid.uuid4()),
                student_id=student_id,
                timestamp=datetime.now(),
                signal_type=SignalType.ATTENDANCE,
                description=f"Critical attendance: {attendance_percent:.1f}% (below 70%)",
                severity=Severity.HIGH,
                urgency=Urgency.TODAY,
                recommended_action="Discuss attendance barriers. Create action plan to improve attendance.",
            )
            signals.append(signal)
        
        elif attendance_percent < 80:
            signal = Signal(
                signal_id=str(uuid.uuid4()),
                student_id=student_id,
                timestamp=datetime.now(),
                signal_type=SignalType.ATTENDANCE,
                description=f"Low attendance: {attendance_percent:.1f}% (below 80%)",
                severity=Severity.MEDIUM,
                urgency=Urgency.TODAY,
                recommended_action="Check in about attendance. Understand any challenges.",
            )
            signals.append(signal)
    
    except (ValueError, TypeError, ZeroDivisionError):
        pass
    
    return signals


def check_engagement_signals(student_id: str, days_since_last_session: int = 7) -> List[Signal]:
    """
    Generate signals for low engagement
    
    Rules:
    - No session in 7+ days: MEDIUM severity, TODAY urgency
    """
    signals = []
    
    # Note: This would ideally query session history from memory service
    # For now, we'll skip this check if days_since_last_session is not available
    if days_since_last_session >= 7:
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            student_id=student_id,
            timestamp=datetime.now(),
            signal_type=SignalType.ENGAGEMENT,
            description=f"Low engagement: No session in {days_since_last_session} days",
            severity=Severity.MEDIUM,
            urgency=Urgency.TODAY,
            recommended_action="Schedule check-in session to re-engage student.",
        )
        signals.append(signal)
    
    return signals


def get_data_driven_signals(student_id: str) -> List[Signal]:
    """
    Generate all data-driven signals for a student
    Combines signals from multiple data sources
    """
    all_signals = []
    
    # Exam risk signals
    all_signals.extend(check_exam_risk_signals(student_id))
    
    # Attendance signals
    all_signals.extend(check_attendance_signals(student_id))
    
    # Engagement signals (can be extended with real data)
    # all_signals.extend(check_engagement_signals(student_id))
    
    return all_signals


# ----------------------------------
# LLM-BASED SIGNAL DETECTION
# ----------------------------------

def generate_session_signal(
    student_id: str,
    chat_history: List[Dict[str, str]],
    student_context: str,
) -> Optional[Signal]:
    """
    Use LLM to analyze student conversation and generate a signal
    
    Looks for:
    - Student confusion or lack of understanding
    - Avoidance of certain topics
    - Frustration or disengagement
    - Repeated mistakes or misconceptions
    
    Args:
        student_id: Student ID
        chat_history: List of {"role": "user"/"assistant", "content": "..."}
        student_context: Student profile and data context
    
    Returns:
        Signal object if concerning pattern detected, None otherwise
    """
    
    profile = get_student_profile(student_id)
    student_name = profile.get('name', student_id) if profile else student_id
    
    # Build conversation summary for LLM
    conversation = "\n".join([
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in chat_history[-6:]  # Last 3 exchanges
    ])
    
    prompt = f"""You are an expert coach analyzing student conversations for concerns.

Student: {student_name} (ID: {student_id})

Recent Conversation:
{conversation}

---

Analyze the conversation and identify the SINGLE most important concern if any exists.

Priority order (pick highest that applies):
1. Mental health crisis (anxiety, depression, overwhelm)
2. Exam anxiety or panic
3. Academic confusion or struggle
4. Low engagement or avoidance

IMPORTANT RULES:
- Return ONLY ONE signal — the highest priority concern
- If multiple concerns exist, pick the most urgent one
- If no genuine concern exists, set has_signal to false
- Do not flag normal study questions as concerns

Respond ONLY with this exact JSON format (no extra text):
{{
    "has_signal": true or false,
    "signal_type": "confusion|engagement|exam_risk|mental_health",
    "severity": "critical|high|medium|low",
    "urgency": "urgent|today|can_wait",
    "description": "clear description of the specific concern",
    "recommended_action": "specific action for coach"
}}
"""
    try:
        response_text = call_llm(prompt)
        
        # Parse JSON response
        import json
        import re
        
        # Extract JSON from response (in case there's extra text)
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            return None
        
        data = json.loads(json_match.group())
        
        if not data.get('has_signal', False):
            return None
        
        # Map signal type
        signal_type_map = {
            'confusion': SignalType.CONFUSION,
            'engagement': SignalType.ENGAGEMENT,
            'performance': SignalType.PERFORMANCE,
            'attendance': SignalType.ATTENDANCE,
            'exam_risk': SignalType.EXAM_RISK,
        }
        
        signal_type = signal_type_map.get(
            data.get('signal_type', 'confusion'),
            SignalType.CONFUSION
        )
        
        # Map severity
        severity_map = {
            'low': Severity.LOW,
            'medium': Severity.MEDIUM,
            'high': Severity.HIGH,
            'critical': Severity.CRITICAL,
        }
        
        severity = severity_map.get(
            data.get('severity', 'medium'),
            Severity.MEDIUM
        )
        
        # Map urgency
        urgency_map = {
            'can_wait': Urgency.CAN_WAIT,
            'today': Urgency.TODAY,
            'urgent': Urgency.URGENT,
        }
        
        urgency = urgency_map.get(
            data.get('urgency', 'today'),
            Urgency.TODAY
        )
        
        # Create signal
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            student_id=student_id,
            timestamp=datetime.now(),
            signal_type=signal_type,
            description=data.get('description', 'Session analysis detected a concern'),
            severity=severity,
            urgency=urgency,
            recommended_action=data.get('recommended_action', 'Follow up in next session'),
        )
        
        return signal
    
    except Exception as e:
        print(f"Error generating session signal: {e}")
        return None
