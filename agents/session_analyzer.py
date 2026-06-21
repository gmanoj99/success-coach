"""
Session Analysis Agent
Analyzes entire student sessions for signals/alerts
Used when "End Session" is clicked
"""

import uuid
from datetime import datetime
from typing import List, Dict, Optional
import json
import re

from models.signal import Signal, SignalType, Severity, Urgency
from services.llm_service import call_llm
from services.student_service import get_student_profile


def analyze_full_session(
    student_id: str,
    chat_history: List[Dict[str, str]],
) -> List[Signal]:
    """
    Analyze an entire session conversation for multiple signals
    Called when student clicks "End Session"
    """
    
    signals = []
    
    if not chat_history or len(chat_history) < 2:
        return signals
    
    profile = get_student_profile(student_id)
    student_name = profile.get('name', student_id) if profile else student_id
    
    print(f"\n{'='*70}")
    print(f"🔍 ANALYZING SESSION FOR SIGNALS")
    print(f"   Student: {student_name} ({student_id})")
    print(f"   Messages: {len(chat_history)}")
    print(f"{'='*70}\n")
    
    # Detect multiple concern types
    detected_signals = [
        _detect_mental_health_concerns(student_id, student_name, chat_history),
        _detect_exam_anxiety(student_id, student_name, chat_history),
        _detect_academic_struggle(student_id, student_name, chat_history),
        _detect_engagement_issues(student_id, student_name, chat_history),
    ]
    
    # Filter out None values
    for signal in detected_signals:
        if signal:
            signals.append(signal)
            print(f"✅ Signal detected: {signal.signal_type.value} - {signal.description}")
    
    if not signals:
        print(f"ℹ️  No concerning signals detected in this session")
    
    print(f"\n{'='*70}\n")
    
    return signals


def _detect_mental_health_concerns(student_id: str, student_name: str, chat_history: List[Dict[str, str]]) -> Optional[Signal]:
    """Detect: depression, anxiety, stress, hopelessness"""
    
    conversation = "\n".join([
        f"{msg['role']}: {msg['content'][:200]}"
        for msg in chat_history[-8:]
    ])
    
    prompt = f"""You are a mental health screening expert. Analyze this conversation for mental health concerns.

Student: {student_name}

Conversation:
{conversation}

---

CRITICAL: Detect if student mentions:
- Depression: sad, hopeless, worthless, can't enjoy anything
- Anxiety: worried, nervous, panic attacks, can't sleep
- Severe Stress: overwhelmed, breaking down
- Self-harm: wanting to die, hurting self

Respond ONLY with JSON:
{{
    "detected": true or false,
    "severity": "critical|high|medium|none",
    "description": "what was detected"
}}
"""
    
    try:
        response = call_llm(prompt, temperature=0.2)
        data = _parse_json(response)
        
        if data and data.get('detected', False):
            severity_map = {
                'critical': Severity.CRITICAL,
                'high': Severity.HIGH,
                'medium': Severity.MEDIUM,
            }
            
            return Signal(
                signal_id=str(uuid.uuid4()),
                student_id=student_id,
                timestamp=datetime.now(),
                signal_type=SignalType.ENGAGEMENT,
                description=f"🚨 Mental Health Concern: {data.get('description', 'Student showing distress')}",
                severity=severity_map.get(data.get('severity', 'high'), Severity.HIGH),
                urgency=Urgency.URGENT,
                recommended_action="Refer to counseling. Assess immediate safety. Have private supportive conversation.",
            )
    except Exception as e:
        print(f"Error in mental health detection: {e}")
    
    return None


def _detect_exam_anxiety(student_id: str, student_name: str, chat_history: List[Dict[str, str]]) -> Optional[Signal]:
    """Detect exam anxiety and test fear"""
    
    conversation = "\n".join([
        f"{msg['role']}: {msg['content'][:200]}"
        for msg in chat_history[-8:]
    ])
    
    prompt = f"""Analyze if this student has exam anxiety.

Student: {student_name}

Conversation:
{conversation}

---

Detect if student mentions:
- Fear of exams: scared, terrified, panic
- Exam pressure: stressed about exam, can't handle
- Performance worry: worried about failing, grades
- Test anxiety: freeze during test, blank out

Respond ONLY with JSON:
{{
    "detected": true or false,
    "severity": "high|medium|low|none",
    "exam": "what exam causes anxiety",
    "description": "brief description"
}}
"""
    
    try:
        response = call_llm(prompt, temperature=0.2)
        data = _parse_json(response)
        
        if data and data.get('detected', False):
            severity_map = {'high': Severity.HIGH, 'medium': Severity.MEDIUM, 'low': Severity.LOW}
            
            return Signal(
                signal_id=str(uuid.uuid4()),
                student_id=student_id,
                timestamp=datetime.now(),
                signal_type=SignalType.EXAM_RISK,
                description=f"📚 Exam Anxiety: Student fearful about {data.get('exam', 'exams')}",
                severity=severity_map.get(data.get('severity', 'medium'), Severity.MEDIUM),
                urgency=Urgency.TODAY,
                recommended_action="Schedule exam prep. Build confidence. Teach relaxation techniques and test-taking strategies.",
            )
    except Exception as e:
        print(f"Error in exam anxiety detection: {e}")
    
    return None


def _detect_academic_struggle(student_id: str, student_name: str, chat_history: List[Dict[str, str]]) -> Optional[Signal]:
    """Detect academic confusion and struggles"""
    
    conversation = "\n".join([
        f"{msg['role']}: {msg['content'][:200]}"
        for msg in chat_history[-8:]
    ])
    
    prompt = f"""Analyze if student is struggling academically.

Student: {student_name}

Conversation:
{conversation}

---

Detect struggle if student mentions:
- Confusion: don't understand, confused about, don't get it
- Difficulty: too hard, can't do this, struggling
- Stuck: not improving, no progress, stuck

Respond ONLY with JSON:
{{
    "detected": true or false,
    "severity": "high|medium|low|none",
    "topics": "what topics are hard",
    "description": "what they struggle with"
}}
"""
    
    try:
        response = call_llm(prompt, temperature=0.2)
        data = _parse_json(response)
        
        if data and data.get('detected', False):
            severity_map = {'high': Severity.HIGH, 'medium': Severity.MEDIUM, 'low': Severity.LOW}
            
            return Signal(
                signal_id=str(uuid.uuid4()),
                student_id=student_id,
                timestamp=datetime.now(),
                signal_type=SignalType.CONFUSION,
                description=f"📖 Academic Struggle: Student struggling with {data.get('topics', 'concepts')}",
                severity=severity_map.get(data.get('severity', 'medium'), Severity.MEDIUM),
                urgency=Urgency.TODAY,
                recommended_action=f"Schedule deep-dive session on {data.get('topics', 'difficult topics')}. Break down concepts. Use practice problems.",
            )
    except Exception as e:
        print(f"Error in academic struggle detection: {e}")
    
    return None


def _detect_engagement_issues(student_id: str, student_name: str, chat_history: List[Dict[str, str]]) -> Optional[Signal]:
    """Detect motivation and engagement issues"""
    
    conversation = "\n".join([
        f"{msg['role']}: {msg['content'][:200]}"
        for msg in chat_history[-8:]
    ])
    
    prompt = f"""Analyze if student shows engagement/motivation issues.

Student: {student_name}

Conversation:
{conversation}

---

Detect if student mentions:
- Lack of motivation: don't care, don't want to, boring
- Avoidance: avoiding, postponing, procrastinating
- Giving up: quit, give up, not worth it

Respond ONLY with JSON:
{{
    "detected": true or false,
    "severity": "high|medium|low|none",
    "type": "motivation|avoidance|disengagement",
    "description": "what engagement issue"
}}
"""
    
    try:
        response = call_llm(prompt, temperature=0.2)
        data = _parse_json(response)
        
        if data and data.get('detected', False):
            severity_map = {'high': Severity.HIGH, 'medium': Severity.MEDIUM, 'low': Severity.LOW}
            
            return Signal(
                signal_id=str(uuid.uuid4()),
                student_id=student_id,
                timestamp=datetime.now(),
                signal_type=SignalType.ENGAGEMENT,
                description=f"💤 Engagement Issue: {data.get('description', 'Low engagement detected')}",
                severity=severity_map.get(data.get('severity', 'medium'), Severity.MEDIUM),
                urgency=Urgency.TODAY,
                recommended_action="Discuss goals and barriers. Connect learning to interests. Rebuild motivation.",
            )
    except Exception as e:
        print(f"Error in engagement detection: {e}")
    
    return None


def _parse_json(response_text: str) -> Optional[Dict]:
    """Safely parse JSON from LLM response"""
    try:
        return json.loads(response_text)
    except:
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                return None
    return None