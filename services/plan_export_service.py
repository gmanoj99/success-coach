"""
Plan export helpers.

Saves daily plans and change summaries to local markdown files so the coach
can review what changed before opening the app.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from models.plan import DailyPlan


PLANS_DIR = Path("data/plans")
SUMMARIES_DIR = Path("data/plan_summaries")


def _ensure_dirs() -> None:
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)


def save_plan_as_markdown(plan: DailyPlan) -> str:
    """Write the current daily plan to a markdown file and return its path."""
    _ensure_dirs()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = PLANS_DIR / f"plan_{plan.date.isoformat()}_{stamp}.md"

    lines: List[str] = [
        f"# Daily Coaching Plan - {plan.date.strftime('%B %d, %Y')}",
        "",
        f"**Generated**: {plan.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Available**: {plan.total_slots_available} minutes",
        f"**Total Used**: {plan.get_total_time_used()} minutes",
        "",
        "## Scheduled Sessions",
    ]

    if plan.scheduled_sessions:
        for session in plan.scheduled_sessions:
            lines.extend([
                f"### {session.student_name}",
                f"- **Time**: {session.time_slot or 'Not scheduled'}",
                f"- **Type**: {session.session_type.value.title()}",
                f"- **Duration**: {session.duration_minutes} min",
                f"- **Reason**: {session.reason}",
                f"- **Signals**: {', '.join(session.source_signal_ids) if session.source_signal_ids else 'n/a'}",
                "",
            ])
    else:
        lines.extend(["No sessions scheduled.", ""])

    lines.append("## Deferred Students")
    if plan.deferred_students:
        for deferred in plan.deferred_students:
            lines.extend([
                f"- **{deferred.student_name}**",
                f"  - Reason: {deferred.reason}",
                f"  - Severity: {deferred.severity_level}",
                f"  - Deferred To: {deferred.deferred_to}",
            ])
    else:
        lines.append("No deferred students.")

    if plan.metadata.get("tradeoff_required"):
        lines.extend([
            "",
            "## Tradeoff Required",
            str(plan.metadata.get("tradeoff_message", "Coach review required.")),
        ])

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def save_plan_update_summary(
    summary: Dict,
    plan: DailyPlan,
) -> str:
    """Save a coach-facing summary of what changed and why."""
    _ensure_dirs()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SUMMARIES_DIR / f"plan_update_{plan.date.isoformat()}_{stamp}.md"

    lines = [
        f"# Plan Update Summary - {plan.date.strftime('%B %d, %Y')}",
        "",
        f"**Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"**Summary**: {summary.get('message', 'Daily plan updated.')}",
        "",
        "## Scheduled",
    ]

    for item in summary.get('scheduled', []):
        lines.extend([
            f"- **{item['student_name']}** at {item['time_slot']}",
            f"  - Reason: {item['reason']}",
        ])

    lines.append("")
    lines.append("## Deferred")
    for item in summary.get('deferred', []):
        lines.extend([
            f"- **{item['student_name']}**",
            f"  - Reason: {item['reason']}",
            f"  - Severity: {item['severity_level']}",
        ])

    if summary.get('tradeoff_required'):
        lines.extend([
            "",
            "## Tradeoff",
            str(summary.get('message', 'Coach needs to decide between competing critical cases.')),
        ])

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def load_latest_plan_update_summary() -> str:
    """Return the contents of the latest plan update summary if present."""
    _ensure_dirs()
    candidates = sorted(SUMMARIES_DIR.glob("plan_update_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return ""
    return candidates[0].read_text(encoding="utf-8")