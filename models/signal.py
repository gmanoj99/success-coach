from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Optional


class SignalType(str, Enum):
    """Types of signals that can be generated"""
    PERFORMANCE = "performance"
    ENGAGEMENT = "engagement"
    CONFUSION = "confusion"
    ATTENDANCE = "attendance"
    EXAM_RISK = "exam_risk"


class Severity(str, Enum):
    """Severity levels for signals"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Urgency(str, Enum):
    """Urgency levels - when coach should act"""
    CAN_WAIT = "can_wait"
    TODAY = "today"
    URGENT = "urgent"


@dataclass
class Signal:
    """
    Represents a signal/alert about a student
    
    Attributes:
        signal_id: Unique identifier for the signal
        student_id: Student who the signal is about
        timestamp: When the signal was generated
        signal_type: Type of signal (performance, engagement, etc.)
        description: Human-readable explanation of the signal
        severity: How serious the issue is (low, medium, high, critical)
        urgency: When coach needs to act (can_wait, today, urgent)
        session_id: Optional - which session generated this signal
        recommended_action: What the coach should do about this signal
        is_resolved: Whether the coach has already acted on this signal
        resolved_at: When the signal was resolved
    """
    signal_id: str
    student_id: str
    timestamp: datetime
    signal_type: SignalType
    description: str
    severity: Severity
    urgency: Urgency
    recommended_action: str
    session_id: Optional[str] = None
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None

    def to_dict(self):
        """Convert signal to dictionary for storage"""
        data = asdict(self)
        # Convert enums to strings
        data['signal_type'] = self.signal_type.value
        data['severity'] = self.severity.value
        data['urgency'] = self.urgency.value
        # Convert datetime to ISO format string
        data['timestamp'] = self.timestamp.isoformat()
        data['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at else None
        return data

    @classmethod
    def from_dict(cls, data: dict):
        """Create signal from dictionary (reverse of to_dict)"""
        data = data.copy()
        # Convert string enums back
        data['signal_type'] = SignalType(data['signal_type'])
        data['severity'] = Severity(data['severity'])
        data['urgency'] = Urgency(data['urgency'])
        # Convert ISO format strings back to datetime
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['resolved_at'] = datetime.fromisoformat(data['resolved_at']) if data['resolved_at'] else None
        return cls(**data)

    @classmethod
    def from_sheet_row(cls, row: dict):
        """Create signal from a Google Sheets row (uses 'type' column, not 'signal_type')"""
        timestamp_str = row.get('timestamp', '')
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(str(timestamp_str))
            except ValueError:
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()

        resolved_at_str = row.get('resolved_at', '')
        resolved_at = None
        if resolved_at_str:
            try:
                resolved_at = datetime.fromisoformat(str(resolved_at_str))
            except ValueError:
                pass

        signal_type_raw = row.get('type') or row.get('signal_type') or 'performance'
        severity_raw = str(row.get('severity', 'medium')).lower()
        urgency_raw = str(row.get('urgency', 'can_wait')).lower()

        return cls(
            signal_id=str(row.get('signal_id', '')),
            student_id=str(row.get('student_id', '')),
            timestamp=timestamp,
            signal_type=SignalType(signal_type_raw),
            description=str(row.get('description', '')),
            severity=Severity(severity_raw),
            urgency=Urgency(urgency_raw),
            recommended_action=str(row.get('recommended_action', '')),
            session_id=row.get('session_id') or None,
            is_resolved=str(row.get('is_resolved', 'FALSE')).lower() == 'true',
            resolved_at=resolved_at,
        )

    def severity_color(self) -> str:
        """Return color for severity level (for UI display)"""
        color_map = {
            Severity.LOW: "🔵",
            Severity.MEDIUM: "🟡",
            Severity.HIGH: "🟠",
            Severity.CRITICAL: "🔴",
        }
        return color_map.get(self.severity, "⚪")

    def urgency_badge(self) -> str:
        """Return badge text for urgency level"""
        badge_map = {
            Urgency.CAN_WAIT: "⏸️ CAN_WAIT",
            Urgency.TODAY: "📅 TODAY",
            Urgency.URGENT: "⚡ URGENT",
        }
        return badge_map.get(self.urgency, "❓ UNKNOWN")
