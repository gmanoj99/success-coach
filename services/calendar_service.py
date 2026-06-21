import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import pytz
from dotenv import load_dotenv
from os import getenv
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Your shared calendar ID
COACH_CALENDAR_ID = "235f02d5741773b036a5114a413832ea15993ddffdfd6a895084de616a7a005a@group.calendar.google.com"
# ← this should be the shared calendar ID, not coach email
print(f"Using shared calendar ID: {COACH_CALENDAR_ID}")
def get_calendar_service():
    try:
        service_account_info = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=CALENDAR_SCOPES
        )
        # No .with_subject() needed — service account directly accesses shared calendar
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error initializing calendar service: {e}")
        return None


def get_coach_calendar_id() -> str:
    return COACH_CALENDAR_ID  # ← shared calendar, not coach email


def get_available_slots(
    date_obj,
    duration_minutes: int = 30,
    coach_timezone: str = "Asia/Kolkata"
) -> List[Tuple[str, str]]:
    try:
        service = get_calendar_service()
        if not service:
            return []

        tz = pytz.timezone(coach_timezone)
        start_of_day = datetime.combine(date_obj, datetime.min.time()).replace(hour=9)
        end_of_day = datetime.combine(date_obj, datetime.min.time()).replace(hour=17)
        start_of_day = tz.localize(start_of_day)
        end_of_day = tz.localize(end_of_day)

        body = {
            "items": [{"id": COACH_CALENDAR_ID}],
            "timeMin": start_of_day.isoformat(),
            "timeMax": end_of_day.isoformat(),
            "intervalMinutes": duration_minutes
        }

        result = service.freebusy().query(body=body).execute()
        busy_times = result.get('calendars', {}).get(COACH_CALENDAR_ID, {}).get('busy', [])

        available_slots = []
        current = start_of_day.replace(minute=0, second=0)
        while current < end_of_day:
            slot_start_dt = current
            slot_end_dt = current + timedelta(minutes=duration_minutes)

            overlaps_busy = False
            for busy_period in busy_times:
                busy_start = datetime.fromisoformat(busy_period['start'])
                busy_end = datetime.fromisoformat(busy_period['end'])

                # Treat any overlap as unavailable so longer sessions do not collide.
                if slot_start_dt < busy_end and slot_end_dt > busy_start:
                    overlaps_busy = True
                    break

            slot_start = current.strftime("%H:%M")
            slot_end = slot_end_dt.strftime("%H:%M")
            if not overlaps_busy:
                available_slots.append((slot_start, slot_end))
            current += timedelta(minutes=30)

        return available_slots

    except Exception as e:
        print(f"Error getting available slots: {e}")
        return []


def create_calendar_event(
    student_name: str,
    session_type: str,
    date_obj,
    start_time: str,
    duration_minutes: int = 30,
    coach_timezone: str = "Asia/Kolkata",
    description: str = ""
) -> Optional[str]:
    try:
        service = get_calendar_service()
        if not service:
            return None

        tz = pytz.timezone(coach_timezone)
        hour, minute = map(int, start_time.split(':'))
        start_dt = datetime.combine(date_obj, datetime.min.time().replace(hour=hour, minute=minute))
        start_dt = tz.localize(start_dt)
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event = {
            'summary': f"Session: {student_name} - {session_type.replace('_', ' ').title()}",
            'description': description or f"Coach session with {student_name}",
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': coach_timezone,
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': coach_timezone,
            },
        }

        result = service.events().insert(
            calendarId=COACH_CALENDAR_ID,  # ← shared calendar
            body=event
        ).execute()

        event_id = result.get('id')
        print(f"✅ Calendar event created: {event_id}")
        return event_id

    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return None


def check_time_slot_free(
    date_obj,
    start_time: str,
    duration_minutes: int = 30,
    coach_timezone: str = "Asia/Kolkata"
) -> bool:
    try:
        available = get_available_slots(date_obj, duration_minutes, coach_timezone)
        return any(slot[0] == start_time for slot in available)
    except Exception as e:
        print(f"Error checking time slot: {e}")
        return False