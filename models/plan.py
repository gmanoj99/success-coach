from dataclasses import dataclass, asdict, field
from datetime import datetime, date
from enum import Enum
from typing import List, Optional


class SessionType(str, Enum):
    """Types of sessions that can be scheduled"""
    CHECK_IN = "check_in"
    DEEP_DIVE = "deep_dive"
    CATCH_UP = "catch_up"
    EXAM_PREP = "exam_prep"
    GENERAL = "general"


@dataclass
class ScheduledSession:
    """
    Represents a student session scheduled for a specific time
    
    Attributes:
        session_id: Unique identifier for this scheduled session
        student_id: Student ID
        student_name: Human-readable student name
        session_type: Type of session (check-in, deep-dive, etc.)
        reason: Why this student is being scheduled (explanation)
        duration_minutes: How long the session should be
        time_slot: Optional - specific time (e.g., "10:00-10:30")
        is_booked: Whether calendar event has been created
        calendar_event_id: Optional - ID of created Google Calendar event
        priority_rank: 1-based rank in today's schedule (lower = higher priority)
    """
    session_id: str
    student_id: str
    student_name: str
    session_type: SessionType
    reason: str
    duration_minutes: int
    priority_rank: int
    time_slot: Optional[str] = None
    is_booked: bool = False
    calendar_event_id: Optional[str] = None
    source_signal_ids: List[str] = field(default_factory=list)

    def to_dict(self):
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['session_type'] = self.session_type.value
        return data

    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        data = data.copy()
        data['session_type'] = SessionType(data['session_type'])
        data['source_signal_ids'] = data.get('source_signal_ids', []) or []
        return cls(**data)


@dataclass
class DeferredStudent:
    """
    Represents a student who couldn't fit into today's plan
    
    Attributes:
        student_id: Student ID
        student_name: Human-readable student name
        reason: Why they were deferred
        severity_level: How serious the issue is (low/medium/high/critical)
        deferred_to: Date when they should be scheduled
    """
    student_id: str
    student_name: str
    reason: str
    severity_level: str
    deferred_to: date

    def to_dict(self):
        """Convert to dictionary for storage"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(**data)


@dataclass
class DailyPlan:
    """
    Represents a coach's daily schedule plan
    
    Attributes:
        plan_id: Unique identifier for this plan
        date: Date this plan is for
        generated_at: When the plan was created
        scheduled_sessions: List of sessions scheduled for today (ordered by priority)
        deferred_students: List of students pushed to tomorrow/future
        total_slots_available: Total time available for sessions (in minutes)
        metadata: Dict with stats (sessions_scheduled, students_addressed, students_deferred, etc.)
    """
    plan_id: str
    date: date
    generated_at: datetime
    scheduled_sessions: List[ScheduledSession] = field(default_factory=list)
    deferred_students: List[DeferredStudent] = field(default_factory=list)
    total_slots_available: int = 480  # 8 hours default
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        """Convert to dictionary for storage"""
        return {
            'plan_id': self.plan_id,
            'date': self.date.isoformat(),
            'generated_at': self.generated_at.isoformat(),
            'scheduled_sessions': [s.to_dict() for s in self.scheduled_sessions],
            'deferred_students': [d.to_dict() for d in self.deferred_students],
            'total_slots_available': self.total_slots_available,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        data = data.copy()
        data['date'] = datetime.fromisoformat(data['date']).date()
        data['generated_at'] = datetime.fromisoformat(data['generated_at'])
        data['scheduled_sessions'] = [ScheduledSession.from_dict(s) for s in data.get('scheduled_sessions', [])]
        data['deferred_students'] = [DeferredStudent.from_dict(d) for d in data.get('deferred_students', [])]
        return cls(**data)

    def get_total_time_used(self) -> int:
        """Calculate total minutes used in scheduled sessions"""
        return sum(s.duration_minutes for s in self.scheduled_sessions)

    def get_total_time_remaining(self) -> int:
        """Calculate remaining available time"""
        return self.total_slots_available - self.get_total_time_used()

    def update_metadata(self):
        """Recalculate and update metadata"""
        self.metadata = {
            'total_sessions_scheduled': len(self.scheduled_sessions),
            'total_students_addressed': len(self.scheduled_sessions),
            'total_students_deferred': len(self.deferred_students),
            'total_time_used_minutes': self.get_total_time_used(),
            'total_time_remaining_minutes': self.get_total_time_remaining(),
            'utilization_percent': round((self.get_total_time_used() / self.total_slots_available * 100) if self.total_slots_available > 0 else 0, 1),
        }
        return self.metadata
