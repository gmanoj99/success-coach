import json
import streamlit as st
import gspread

from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]


def get_client():

    service_account_info = dict(
        st.secrets["[gcp_service_account]"]
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