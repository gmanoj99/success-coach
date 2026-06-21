import json
import streamlit as st
import gspread

from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import List, Dict, Any

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]


def get_client():

    service_account_info = dict(
    st.secrets["gcp_service_account"]
)

    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES
    )

    return gspread.authorize(creds)


def get_worksheet(
    spreadsheet_id,
    worksheet_name
):
    client = get_client()

    spreadsheet = client.open_by_key(
        spreadsheet_id
    )

    return spreadsheet.worksheet(
        worksheet_name
    )


# ----------------------------------
# SIGNAL PERSISTENCE
# ----------------------------------

def append_signal(
    spreadsheet_id: str,
    signal_dict: Dict[str, Any]
) -> bool:
    """
    Append a signal to the 'Signals' sheet in Google Sheets
    
    Creates the sheet if it doesn't exist.
    
    Args:
        spreadsheet_id: Google Sheets ID
        signal_dict: Signal object converted to dict
    
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Try to get existing Signals sheet
        try:
            worksheet = spreadsheet.worksheet("Signals")
        except gspread.exceptions.WorksheetNotFound:
            # Create new Signals sheet if it doesn't exist
            worksheet = spreadsheet.add_worksheet(
                title="Signals",
                rows=1000,
                cols=12
            )
            
            # Add header row
            headers = [
                "signal_id", "student_id", "timestamp", "type",
                "description", "severity", "urgency", "session_id",
                "recommended_action", "is_resolved", "resolved_at", "date"
            ]
            worksheet.append_row(headers)
        
        # Prepare row data
        row = [
            signal_dict.get('signal_id', ''),
            signal_dict.get('student_id', ''),
            signal_dict.get('timestamp', ''),
            signal_dict.get('signal_type', ''),
            signal_dict.get('description', ''),
            signal_dict.get('severity', ''),
            signal_dict.get('urgency', ''),
            signal_dict.get('session_id', ''),
            signal_dict.get('recommended_action', ''),
            str(signal_dict.get('is_resolved', False)),
            signal_dict.get('resolved_at', ''),
            datetime.now().strftime('%Y-%m-%d'),  # date column for filtering
        ]
        
        worksheet.append_row(row)
        return True
    
    except Exception as e:
        print(f"Error appending signal to Sheets: {e}")
        return False


def get_signals_for_date(
    spreadsheet_id: str,
    target_date: str = None
) -> List[Dict[str, Any]]:
    """
    Get all signals for a specific date from Google Sheets
    
    Args:
        spreadsheet_id: Google Sheets ID
        target_date: Date string (YYYY-MM-DD), defaults to today
    
    Returns:
        List of signal dictionaries
    """
    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        client = get_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Try to get existing Signals sheet
        try:
            worksheet = spreadsheet.worksheet("Signals")
        except gspread.exceptions.WorksheetNotFound:
            print("ℹ️ Signals sheet does not exist yet")
            return []
        
        all_rows = worksheet.get_all_records()
        
        # Filter by date
        signals = [
            row for row in all_rows
            if row.get('date', '') == target_date
        ]
        
        return signals
    
    except Exception as e:
        print(f"Error fetching signals from Sheets: {e}")
        return []


def get_unresolved_signals(
    spreadsheet_id: str,
) -> List[Dict[str, Any]]:
    """
    Get all unresolved signals from Google Sheets
    
    Args:
        spreadsheet_id: Google Sheets ID
    
    Returns:
        List of unresolved signal dictionaries
    """
    try:
        client = get_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Try to get existing Signals sheet
        try:
            worksheet = spreadsheet.worksheet("Signals")
        except gspread.exceptions.WorksheetNotFound:
            print("ℹ️ Signals sheet does not exist yet, returning empty list")
            return []
        
        all_rows = worksheet.get_all_records()
        
        # Filter unresolved signals
        signals = [
            row for row in all_rows
            if str(row.get('is_resolved', 'FALSE')).lower() != 'true'
        ]
        
        return signals
    
    except Exception as e:
        print(f"Error fetching unresolved signals: {e}")
        return []


# ----------------------------------
# PLAN PERSISTENCE
# ----------------------------------

def append_plan_session(
    spreadsheet_id: str,
    plan_dict: Dict[str, Any]
) -> bool:
    """
    Append plan sessions to the 'Plans' sheet in Google Sheets
    
    Creates the sheet if it doesn't exist.
    
    Args:
        spreadsheet_id: Google Sheets ID
        plan_dict: Plan object converted to dict (contains scheduled_sessions list)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Try to get existing Plans sheet
        try:
            worksheet = spreadsheet.worksheet("Plans")
        except gspread.exceptions.WorksheetNotFound:
            # Create new Plans sheet if it doesn't exist
            worksheet = spreadsheet.add_worksheet(
                title="Plans",
                rows=1000,
                cols=12
            )
            
            # Add header row
            headers = [
                "plan_id", "date", "student_id", "student_name", "session_type",
                "reason", "duration_minutes", "time_slot", "priority_rank",
                "is_booked", "calendar_event_id", "created_at"
            ]
            worksheet.append_row(headers)
        
        # Append each scheduled session
        for session in plan_dict.get('scheduled_sessions', []):
            row = [
                plan_dict.get('plan_id', ''),
                plan_dict.get('date', ''),
                session.get('student_id', ''),
                session.get('student_name', ''),
                session.get('session_type', ''),
                session.get('reason', ''),
                str(session.get('duration_minutes', 0)),
                session.get('time_slot', ''),
                str(session.get('priority_rank', 0)),
                str(session.get('is_booked', False)),
                session.get('calendar_event_id', ''),
                datetime.now().isoformat(),
            ]
            worksheet.append_row(row)
        
        # Append deferred students
        for deferred in plan_dict.get('deferred_students', []):
            row = [
                plan_dict.get('plan_id', ''),
                plan_dict.get('date', ''),
                deferred.get('student_id', ''),
                deferred.get('student_name', ''),
                'deferred',
                deferred.get('reason', ''),
                '0',
                '',
                '',
                'False',
                '',
                datetime.now().isoformat(),
            ]
            worksheet.append_row(row)
        
        return True
    
    except Exception as e:
        print(f"Error appending plan to Sheets: {e}")
        return False


def get_plan_for_date(
    spreadsheet_id: str,
    target_date: str = None
) -> List[Dict[str, Any]]:
    """
    Get plan entries for a specific date
    
    Args:
        spreadsheet_id: Google Sheets ID
        target_date: Date string (YYYY-MM-DD), defaults to today
    
    Returns:
        List of plan row dictionaries
    """
    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        worksheet = get_worksheet(spreadsheet_id, "Plans")
        all_rows = worksheet.get_all_records()
        
        # Filter by date
        plans = [
            row for row in all_rows
            if row.get('date', '') == target_date
        ]
        
        return plans
    
    except Exception as e:
        print(f"Error fetching plan from Sheets: {e}")
        return []
    
def update_signal_resolved(
    spreadsheet_id: str,
    signal_id: str
) -> bool:
    """Mark a signal as resolved"""
    try:
        client = get_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("Signals")
        
        all_rows = worksheet.get_all_records()
        for idx, row in enumerate(all_rows, start=2):  # +2 for header and 1-indexing
            if row.get('signal_id') == signal_id:
                worksheet.update_cell(idx, 10, 'TRUE')  # is_resolved column
                worksheet.update_cell(idx, 11, datetime.now().isoformat())  # resolved_at
                return True
        return False
    except Exception as e:
        print(f"Error updating signal: {e}")
        return False