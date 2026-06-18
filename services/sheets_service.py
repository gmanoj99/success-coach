import os
import json
import gspread

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]

TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"


def get_credentials():

    creds = None

    # Load saved token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    # Login if needed
    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def get_client():

    creds = get_credentials()

    return gspread.authorize(creds)


def get_worksheet(spreadsheet_id, worksheet_name):

    client = get_client()

    spreadsheet = client.open_by_key(
        spreadsheet_id
    )

    return spreadsheet.worksheet(
        worksheet_name
    )