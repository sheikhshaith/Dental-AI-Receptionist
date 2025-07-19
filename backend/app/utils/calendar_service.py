# app/utils/calender_service.py
import os
from datetime import datetime, timedelta
import pytz
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds = Credentials.from_authorized_user_file(
        os.getenv("GOOGLE_CALENDAR_TOKEN_PATH"), SCOPES
    )
    return build('calendar', 'v3', credentials=creds)

def create_dummy_event():
    service = get_calendar_service()

    # Set current time in Lahore
    lahore_tz = pytz.timezone('Asia/Karachi')
    start_time = datetime.now(lahore_tz) + timedelta(hours=1)
    end_time = start_time + timedelta(hours=1)

    event = {
        'summary': '🦷 Dummy Dental Appointment',
        'location': '123 Dental Street',
        'description': 'Routine check-up.',
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Asia/Karachi',
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'Asia/Karachi',
        },
    }

    event = service.events().insert(calendarId=os.getenv("CALENDAR_ID"), body=event).execute()
    return event

def list_upcoming_events():
    service = get_calendar_service()
    events_result = service.events().list(
        calendarId=os.getenv("CALENDAR_ID"),
        maxResults=5,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])
