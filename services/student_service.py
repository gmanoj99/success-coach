from services.sheets_service import get_worksheet
from datetime import datetime

import os
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID = os.getenv(
    "GOOGLE_SPREADSHEET_ID"
)
roster = get_worksheet(
    SPREADSHEET_ID,
    "roster"
)

sheet = get_worksheet(
    SPREADSHEET_ID,
    "exam_scores"
)

sheet = get_worksheet(
    SPREADSHEET_ID,
    "attendance"
)

sheet = get_worksheet(
    SPREADSHEET_ID,
    "exam_schedule"
)
def get_student_profile(student_id):

    roster = get_worksheet("roster")

    rows = roster.get_all_records()

    for row in rows:
        if row["student_id"] == student_id:
            return row

    return None

def get_student_scores(student_id):

    sheet = get_worksheet("exam_scores")

    rows = sheet.get_all_records()

    return [
        row
        for row in rows
        if row["student_id"] == student_id
    ]

def get_student_attendance(student_id):

    sheet = get_worksheet("attendance")

    rows = sheet.get_all_records()

    records = [
        row
        for row in rows
        if row["student_id"] == student_id
    ]

    return records

def get_student_exams(student_id):

    sheet = get_worksheet("exam_schedule")

    rows = sheet.get_all_records()

    exams = [
        row
        for row in rows
        if row["student_id"] == student_id
    ]

    return exams



def build_student_context(student_id):

    profile = get_student_profile(student_id)

    if not profile:
        return "No student data found."

    scores = get_student_scores(student_id)
    attendance_records = get_student_attendance(student_id)
    exams = get_student_exams(student_id)

    context = []

    alerts = []

    # Student Details

    context.append(
        f"Student Name: {profile['name']}"
    )

    context.append(
        f"Program: {profile['program']}"
    )

    context.append(
        f"Cohort: {profile['cohort']}"
    )

    # Attendance

    if attendance_records:

        latest = attendance_records[-1]

        attendance_pct = latest["attendance_pct"]

        context.append(
            f"Attendance Percentage: {attendance_pct}%"
        )

        if attendance_pct < 75:
            alerts.append(
                f"Low attendance ({attendance_pct}%)."
            )

    # Scores

    context.append("\nSubject Scores:")

    for score in scores:

        percentage = (
            score["score"] /
            score["max_score"]
        ) * 100

        context.append(
            f"{score['subject']} : "
            f"{score['score']}/{score['max_score']} "
            f"({percentage:.0f}%)"
        )

        if percentage < 50:
            alerts.append(
                f"Low score in {score['subject']} "
                f"({percentage:.0f}%)."
            )

    # Upcoming Exams

    context.append("\nUpcoming Exams:")

    today = datetime.today()

    for exam in exams:

        context.append(
            f"{exam['subject']} - "
            f"{exam['exam_date']} "
            f"({exam['exam_type']})"
        )

        try:

            exam_date = datetime.strptime(
                exam["exam_date"],
                "%Y-%m-%d"
            )

            days_left = (
                exam_date - today
            ).days

            if days_left <= 7:
                alerts.append(
                    f"{exam['subject']} exam is in "
                    f"{days_left} days."
                )

        except Exception:
            pass

    # Alerts

    context.append("\nAlerts:")

    if alerts:

        for alert in alerts:
            context.append(
                f"- {alert}"
            )

    else:

        context.append(
            "- No alerts."
        )

    return "\n".join(context)