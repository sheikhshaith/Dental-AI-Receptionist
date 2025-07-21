

# calendar_service.py
import os
import os
from datetime import datetime, timedelta, time, date
import pytz
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import logging
import re
from dateutil import parser

# Add this at the top of your calendar_service.py after the imports

import os
from datetime import datetime, timedelta, time, date
import pytz
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import logging
import re
from dateutil import parser
import locale

# IMPORT EMAIL SERVICE
from email_service import send_appointment_confirmation

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']

# Clinic Configuration - Use environment variables
CLINIC_OPEN_HOUR = int(os.getenv('BUSINESS_HOURS_START', 9))    # 9 AM
CLINIC_CLOSE_HOUR = int(os.getenv('BUSINESS_HOURS_END', 19))   # 7 PM
APPOINTMENT_DURATION = int(os.getenv('APPOINTMENT_DURATION_MINUTES', 60))  # 60 minutes default
BUFFER_TIME = int(os.getenv('BUFFER_TIME_MINUTES', 15))  # 15 minutes buffer between appointments

# CRITICAL FIX: Custom timezone with correct offset
class FixedPakistanTZ(pytz.tzinfo.BaseTzInfo):
    """
    Custom timezone class to fix the 32-minute offset issue
    Forces correct +05:00 offset for Pakistan Standard Time
    """
    def __init__(self):
        self.zone = 'Asia/Karachi_Fixed'
        
    def utcoffset(self, dt):
        return timedelta(hours=5)  # Always +05:00, never +04:28
    
    def dst(self, dt):
        return timedelta(0)  # Pakistan doesn't observe DST
    
    def tzname(self, dt):
        return 'PKT'
    
    def localize(self, dt, is_dst=None):
        """Localize a naive datetime to this timezone"""
        if dt.tzinfo is not None:
            raise ValueError("Not naive datetime (tzinfo is already set)")
        return dt.replace(tzinfo=self)
    
    def normalize(self, dt):
        """Normalize the datetime (no-op for fixed offset)"""
        return dt

# Use the fixed timezone instead of pytz
LAHORE_TZ_ORIGINAL = pytz.timezone(os.getenv('TIMEZONE', 'Asia/Karachi'))
LAHORE_TZ = FixedPakistanTZ()  # Use our fixed timezone

def fix_timezone_offset(dt_with_wrong_offset):
    """
    Convert a datetime with wrong offset (+04:28) to correct offset (+05:00)
    """
    if dt_with_wrong_offset.tzinfo is None:
        # If naive, localize with correct timezone
        return LAHORE_TZ.localize(dt_with_wrong_offset)
    
    # Convert to UTC first, then to correct PKT
    utc_dt = dt_with_wrong_offset.astimezone(pytz.UTC)
    # Add 32 minutes to compensate for the wrong offset
    corrected_utc = utc_dt + timedelta(minutes=32)
    # Convert back to our fixed PKT
    return corrected_utc.astimezone(pytz.timezone('UTC')).replace(tzinfo=LAHORE_TZ) + timedelta(hours=5)

def parse_natural_date(date_input):
    """
    Parse natural language dates like 'monday', 'tomorrow', etc.
    Always returns future dates for booking context
    """
    today = datetime.now(LAHORE_TZ).date()
    date_input = date_input.lower().strip()
    
    logger.info(f"🔍 Parsing natural date: '{date_input}' (today is {today})")
    
    # Handle 'today' - but only if it's not past business hours
    if 'today' in date_input:
        current_hour = datetime.now(LAHORE_TZ).hour
        if current_hour < CLINIC_CLOSE_HOUR and not is_weekend(today):
            return today
        else:
            # If today is past business hours or weekend, suggest tomorrow
            tomorrow = today + timedelta(days=1)
            while is_weekend(tomorrow):
                tomorrow += timedelta(days=1)
            logger.info(f"⚠️ Today is past business hours or weekend, suggesting {tomorrow}")
            return tomorrow
    
    # Handle 'tomorrow'
    if 'tomorrow' in date_input:
        tomorrow = today + timedelta(days=1)
        if is_weekend(tomorrow):
            # Skip to next business day
            while is_weekend(tomorrow):
                tomorrow += timedelta(days=1)
        return tomorrow
    
    # Handle day names (monday, tuesday, etc.)
    days_of_week = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    for day_name, day_num in days_of_week.items():
        if day_name in date_input:
            # Find the next occurrence of this day
            current_weekday = today.weekday()
            days_ahead = (day_num - current_weekday) % 7
            
            # If it's the same day but past business hours, get next week
            if days_ahead == 0:
                current_hour = datetime.now(LAHORE_TZ).hour
                if current_hour >= CLINIC_CLOSE_HOUR:
                    days_ahead = 7
            
            # If days_ahead is 0, it means today - but we want future dates
            if days_ahead == 0:
                days_ahead = 7
                
            target_date = today + timedelta(days=days_ahead)
            
            # Skip Sunday (we're closed)
            if target_date.weekday() == 6:  # Sunday
                target_date += timedelta(days=1)  # Move to Monday
                
            logger.info(f"✅ '{day_name}' parsed as {target_date}")
            return target_date
    
    # Handle 'next week' 
    if 'next week' in date_input:
        target_date = today + timedelta(days=7)
        while is_weekend(target_date):
            target_date += timedelta(days=1)
        return target_date
    
    # Try to parse as regular date
    try:
        # Handle various date formats
        parsed_date = parser.parse(date_input, default=datetime.now()).date()
        
        # Ensure it's in the future
        if parsed_date <= today:
            # If someone says "July 21" and it's past, assume next year
            if parsed_date.month <= today.month and parsed_date.day <= today.day:
                parsed_date = parsed_date.replace(year=today.year + 1)
            else:
                parsed_date = parsed_date.replace(year=today.year)
        
        # Skip Sunday if needed
        if is_weekend(parsed_date):
            parsed_date += timedelta(days=1)
            
        logger.info(f"✅ Date parsed as {parsed_date}")
        return parsed_date
        
    except Exception as e:
        logger.error(f"❌ Could not parse date '{date_input}': {e}")
        # Return tomorrow as fallback
        tomorrow = today + timedelta(days=1)
        while is_weekend(tomorrow):
            tomorrow += timedelta(days=1)
        return tomorrow

def validate_phone_number(phone):
    """
    Validate phone number format for Pakistan
    """
    if not phone:
        return False
    
    # Remove spaces, dashes, and parentheses
    clean_phone = re.sub(r'[\s\-\(\)]+', '', phone)
    
    # Pakistan phone number patterns
    patterns = [
        r'^\+92[0-9]{10}$',          # +92xxxxxxxxxx
        r'^92[0-9]{10}$',            # 92xxxxxxxxxx  
        r'^0[0-9]{10}$',             # 0xxxxxxxxxx
        r'^[0-9]{11}$',              # xxxxxxxxxxx
        r'^\+92\-[0-9]{3}\-[0-9]{7}$', # +92-xxx-xxxxxxx
    ]
    
    for pattern in patterns:
        if re.match(pattern, clean_phone):
            return True
    
    # Also accept basic 10+ digit numbers
    if len(clean_phone) >= 10 and clean_phone.isdigit():
        return True
        
    return False

def validate_email(email):
    """
    Validate email format
    """
    if not email:
        return True  # Email is optional
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    return re.match(pattern, email) is not None

def get_calendar_service():
    """Initialize Google Calendar service with proper error handling"""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        token_path = os.getenv("GOOGLE_CALENDAR_TOKEN_PATH")
        
        if not token_path:
            raise ValueError("GOOGLE_CALENDAR_TOKEN_PATH not set in environment")
            
        if not os.path.isabs(token_path):
            token_path = os.path.join(base_dir, token_path)
            
        if not os.path.exists(token_path):
            raise FileNotFoundError(f"Token file not found at: {token_path}")
            
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        if creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials...")
            creds.refresh(Request())
            
        if not creds.valid:
            raise Exception("Invalid credentials")
            
        service = build('calendar', 'v3', credentials=creds)
        logger.info("Google Calendar service initialized successfully")
        return service
        
    except Exception as e:
        logger.error(f"Failed to initialize calendar service: {e}")
        raise

def is_within_clinic_hours(appointment_time):
    """Check if appointment time is within clinic operating hours"""
    hour = appointment_time.hour
    return CLINIC_OPEN_HOUR <= hour < CLINIC_CLOSE_HOUR

def is_weekend(appointment_date):
    """Check if the date falls on weekend - Only Sunday is closed"""
    # Monday=0, Tuesday=1, ..., Saturday=5, Sunday=6
    day_of_week = appointment_date.weekday()
    
    logger.info(f"Checking weekend for {appointment_date}: weekday={day_of_week} ({'Sunday' if day_of_week == 6 else 'Saturday' if day_of_week == 5 else 'Weekday'})")
    
    # Only Sunday (6) is closed, Saturday (5) is open
    return day_of_week == 6  # Only Sunday

def get_existing_appointments(date):
    """Get all appointments for a specific date"""
    try:
        service = get_calendar_service()
        calendar_id = os.getenv("CALENDAR_ID", 'primary')
        
        # Set time range for the day with proper timezone
        start_of_day = datetime.combine(date, time.min).replace(tzinfo=LAHORE_TZ)
        end_of_day = datetime.combine(date, time.max).replace(tzinfo=LAHORE_TZ)
        
        logger.info(f"Fetching appointments for {date} from {start_of_day} to {end_of_day}")
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        logger.info(f"Found {len(events)} existing appointments for {date}")
        return events
        
    except Exception as e:
        logger.error(f"Error fetching appointments for {date}: {e}")
        return []

def check_time_conflict(requested_start, requested_end, existing_events):
    """Check if requested time conflicts with existing appointments"""
    
    logger.info(f"🔍 CONFLICT CHECK START")
    logger.info(f"  Requested slot: {requested_start.strftime('%H:%M')} - {requested_end.strftime('%H:%M')} ({requested_start.tzinfo})")
    logger.info(f"  Checking against {len(existing_events)} existing events")
    
    for i, event in enumerate(existing_events):
        if 'dateTime' not in event.get('start', {}):
            logger.info(f"  Event {i+1}: Skipping all-day event")
            continue  # Skip all-day events
            
        try:
            existing_start_str = event['start']['dateTime']
            existing_end_str = event['end']['dateTime']
            
            # Better timezone handling
            if existing_start_str.endswith('Z'):
                existing_start = datetime.fromisoformat(existing_start_str.replace('Z', '+00:00'))
                existing_end = datetime.fromisoformat(existing_end_str.replace('Z', '+00:00'))
            else:
                existing_start = datetime.fromisoformat(existing_start_str)
                existing_end = datetime.fromisoformat(existing_end_str)
            
            # Convert to Lahore timezone if needed
            if existing_start.tzinfo != LAHORE_TZ:
                existing_start = existing_start.astimezone(LAHORE_TZ)
                existing_end = existing_end.astimezone(LAHORE_TZ)
            
            logger.info(f"  Event {i+1}: {existing_start.strftime('%H:%M')} - {existing_end.strftime('%H:%M')} ({event.get('summary', 'No title')})")
            
            # ULTRA STRICT OVERLAP CHECK
            buffer_delta = timedelta(minutes=BUFFER_TIME)
            
            # Direct overlap check
            direct_overlap = (requested_start < existing_end and requested_end > existing_start)
            
            # Buffer-enhanced check  
            requested_start_buffered = requested_start - buffer_delta
            requested_end_buffered = requested_end + buffer_delta
            buffer_overlap = (requested_start_buffered < existing_end and requested_end_buffered > existing_start)
            
            logger.info(f"    Direct overlap: {direct_overlap}")
            logger.info(f"    Buffer overlap: {buffer_overlap}")
            
            # If ANY method detects conflict, block it
            if direct_overlap or buffer_overlap:
                logger.error(f"🚨 CONFLICT DETECTED WITH EVENT {i+1}!")
                logger.error(f"    Requested: {requested_start.strftime('%H:%M')} - {requested_end.strftime('%H:%M')}")
                logger.error(f"    Existing: {existing_start.strftime('%H:%M')} - {existing_end.strftime('%H:%M')}")
                logger.error(f"    Event: {event.get('summary', 'No title')}")
                return True, event
                
        except Exception as e:
            logger.error(f"Error parsing event {i+1} datetime: {e}")
            continue
    
    logger.info("✅ No conflicts found - slot is available")
    return False, None

def generate_alternative_slots(requested_date, duration_minutes=APPOINTMENT_DURATION):
    """
    Generate alternative available time slots with proper business hours validation
    Only return slots that actually have availability AND end before clinic closing time
    """
    try:
        # Don't generate slots for dates with no availability
        if is_weekend(requested_date):
            logger.info(f"❌ {requested_date} is Sunday (closed) - no slots generated")
            return []
        
        # Check if date is in the past
        today = datetime.now(LAHORE_TZ).date()
        if requested_date < today:
            logger.info(f"❌ {requested_date} is in the past - no slots generated")
            return []
        
        # Get existing appointments
        existing_events = get_existing_appointments(requested_date)
        
        logger.info(f"Found {len(existing_events)} existing appointments for {requested_date}")
        
        # Generate possible time slots (every 30 minutes)
        slots = []
        current_time = datetime.combine(requested_date, time(CLINIC_OPEN_HOUR, 0)).replace(tzinfo=LAHORE_TZ)
        end_time = datetime.combine(requested_date, time(CLINIC_CLOSE_HOUR, 0)).replace(tzinfo=LAHORE_TZ)
        
        # If checking today, start from current time + 1 hour
        if requested_date == today:
            now = datetime.now(LAHORE_TZ)
            earliest_time = now + timedelta(hours=1)  # At least 1 hour notice
            if earliest_time > current_time:
                current_time = earliest_time.replace(minute=0 if earliest_time.minute < 30 else 30, second=0, microsecond=0)
        
        logger.info(f"🕐 SLOT GENERATION:")
        logger.info(f"  Start time: {current_time.strftime('%H:%M')}")
        logger.info(f"  End time (clinic closes): {end_time.strftime('%H:%M')}")
        logger.info(f"  Appointment duration: {duration_minutes} minutes")
        
        # Ensure appointment can complete BEFORE clinic closing time
        while current_time + timedelta(minutes=duration_minutes) <= end_time:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            
            # Check that appointment ends before clinic closes
            if slot_end > end_time:
                logger.info(f"  ❌ Slot {current_time.strftime('%H:%M')} would end at {slot_end.strftime('%H:%M')} (past closing time {end_time.strftime('%H:%M')})")
                break
            
            # Check if this slot conflicts with existing appointments
            has_conflict, conflicting_event = check_time_conflict(current_time, slot_end, existing_events)
            
            if not has_conflict:
                # Store timezone-aware ISO strings for exact timing preservation
                slots.append({
                    'start_time': current_time.isoformat(),  # ISO string with timezone
                    'end_time': slot_end.isoformat(),
                    'formatted_time': current_time.strftime('%I:%M %p'),  # Display format
                    'time_24h': current_time.strftime('%H:%M'),  # 24-hour format for backend
                    'timezone': 'Asia/Karachi',  # Explicit timezone reference
                    'utc_start': current_time.astimezone(pytz.UTC).isoformat(),  # UTC for debugging
                    'utc_end': slot_end.astimezone(pytz.UTC).isoformat()
                })
                logger.info(f"  ✓ Available slot: {current_time.strftime('%I:%M %p')} - {slot_end.strftime('%I:%M %p')} (ends before {end_time.strftime('%H:%M')})")
            else:
                conflicting_summary = conflicting_event.get('summary', 'Unknown appointment') if conflicting_event else 'Unknown conflict'
                logger.info(f"  ✗ Conflict with: {conflicting_summary}")
            
            # Move to next 30-minute slot
            current_time += timedelta(minutes=30)
        
        logger.info(f"Generated {len(slots)} available slots for {requested_date}")
        
        # Additional validation: Double-check all slots end before closing time
        valid_slots = []
        for slot in slots:
            slot_end_time = datetime.fromisoformat(slot['end_time'])
            if slot_end_time <= end_time:
                valid_slots.append(slot)
            else:
                logger.warning(f"⚠️ Removing invalid slot that ends past closing time: {slot['formatted_time']}")
        
        logger.info(f"Final valid slots: {len(valid_slots)}")
        return valid_slots
        
    except Exception as e:
        logger.error(f"Error generating alternative slots: {e}")
        return []

def book_appointment(patient_name, patient_phone, appointment_date, appointment_time, duration_minutes=APPOINTMENT_DURATION, appointment_type="General Checkup", patient_email=None):
    """
    ENHANCED: Book an appointment with email confirmation support
    """
    try:
        # Input validation first
        if not patient_name or not patient_phone:
            return {
                'success': False,
                'message': 'Patient name and phone number are required.'
            }
        
        # Validate phone number format
        if not validate_phone_number(patient_phone):
            return {
                'success': False,
                'message': 'Please provide a valid phone number (e.g., +92-321-1234567 or 0321-1234567).'
            }
        
        # CRITICAL FIX: Create timezone-naive datetime and format it properly
        logger.info(f"🔍 APPOINTMENT BOOKING - INPUT ANALYSIS:")
        logger.info(f"  Input appointment_date: {appointment_date} (type: {type(appointment_date)})")
        logger.info(f"  Input appointment_time: {appointment_time} (type: {type(appointment_time)})")
        logger.info(f"  Patient email: {patient_email}")
        
        if isinstance(appointment_time, time):
            # Standard time object - combine with date (NO timezone conversion)
            naive_datetime = datetime.combine(appointment_date, appointment_time)
        elif isinstance(appointment_time, str):
            # String time - parse and combine
            try:
                if ':' in appointment_time:
                    hour, minute = appointment_time.split(':')
                    time_obj = time(int(hour), int(minute))
                    naive_datetime = datetime.combine(appointment_date, time_obj)
                else:
                    raise ValueError(f"Invalid time string format: {appointment_time}")
            except Exception as e:
                logger.error(f"Error parsing time string: {e}")
                return {
                    'success': False,
                    'message': f'Invalid time format: {appointment_time}'
                }
        elif isinstance(appointment_time, datetime):
            # Already a datetime object - use as is but remove timezone
            naive_datetime = appointment_time.replace(tzinfo=None)
        else:
            logger.error(f"Unsupported appointment_time type: {type(appointment_time)}")
            return {
                'success': False,
                'message': f'Unsupported time format: {type(appointment_time)}'
            }
        
        naive_end_datetime = naive_datetime + timedelta(minutes=duration_minutes)
        
        # For validation purposes, create timezone-aware versions
        appointment_datetime_tz = LAHORE_TZ.localize(naive_datetime)
        appointment_end_tz = LAHORE_TZ.localize(naive_end_datetime)
        
        # Enhanced logging for debugging
        logger.info(f"🔍 FINAL APPOINTMENT TIMING:")
        logger.info(f"  Patient: {patient_name}")
        logger.info(f"  Phone: {patient_phone}")
        logger.info(f"  Email: {patient_email or 'Not provided'}")
        logger.info(f"  Naive Start: {naive_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"  Naive End: {naive_end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"  For validation (PKT): {appointment_datetime_tz.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"  Duration: {duration_minutes} minutes")
        
        # Validation checks using timezone-aware versions
        validation_result = validate_appointment_request(appointment_datetime_tz, appointment_end_tz)
        if not validation_result['valid']:
            return validation_result
        
        # Conflict checking using timezone-aware versions
        existing_events = get_existing_appointments(appointment_date)
        logger.info(f"🔍 BOOKING VALIDATION: Checking {appointment_datetime_tz.strftime('%H:%M')} - {appointment_end_tz.strftime('%H:%M')}")
        logger.info(f"Found {len(existing_events)} existing appointments to check against")
        
        has_conflict, conflicting_event = check_time_conflict(appointment_datetime_tz, appointment_end_tz, existing_events)
        
        if has_conflict:
            conflicting_start = conflicting_event['start']['dateTime'] if conflicting_event else 'Unknown'
            conflicting_summary = conflicting_event.get('summary', 'Unknown appointment') if conflicting_event else 'Unknown'
            
            logger.error(f"🚨 APPOINTMENT BOOKING BLOCKED!")
            logger.error(f"  ❌ Requested: {appointment_datetime_tz.strftime('%H:%M')} - {appointment_end_tz.strftime('%H:%M')}")
            logger.error(f"  ⚠️  Conflicts with: {conflicting_summary}")
            
            # Generate alternatives
            alternatives = generate_alternative_slots(appointment_date, duration_minutes)
            
            return {
                'success': False,
                'message': f'🚫 BOOKING DENIED: Time slot {appointment_datetime_tz.strftime("%I:%M %p")} conflicts with existing appointment "{conflicting_summary}". Please choose a different time.',
                'conflict_details': {
                    'existing_appointment': conflicting_summary,
                    'existing_time': conflicting_start,
                    'requested_time': appointment_datetime_tz.strftime('%I:%M %p'),
                    'reason': 'Time slot overlap detected'
                },
                'alternatives': alternatives[:5],
                'has_alternatives': len(alternatives) > 0,
                'alternative_message': f"📋 Available time slots for {appointment_date.strftime('%B %d, %Y')}:"
            }
        
        logger.info("✅ No conflicts detected - proceeding with appointment creation...")
        
        # CRITICAL FIX: Create calendar event with timezone-naive datetime strings
        service = get_calendar_service()
        calendar_id = os.getenv("CALENDAR_ID", 'primary')
        
        # Format datetime without timezone info - let Google handle it with explicit timezone
        start_datetime_str = naive_datetime.strftime('%Y-%m-%dT%H:%M:%S')
        end_datetime_str = naive_end_datetime.strftime('%Y-%m-%dT%H:%M:%S')
        
        # Create the event structure
        event = {
            'summary': f'🦷 {appointment_type} - {patient_name}',
            'location': os.getenv('BUSINESS_ADDRESS', 'Bright Smile Dental Office'),
            'description': f'''
Patient: {patient_name}
Phone: {patient_phone}
{f"Email: {patient_email}" if patient_email else "Email: Not provided"}
Type: {appointment_type}
Duration: {duration_minutes} minutes

Booked via AI Receptionist

TIMING VERIFICATION:
- User Selected: {naive_datetime.strftime('%I:%M %p')}
- Local Time: {start_datetime_str}
- Timezone: Asia/Karachi
            '''.strip(),
            'start': {
                'dateTime': start_datetime_str,  # NO timezone in the datetime string
                'timeZone': 'Asia/Karachi'       # Explicit timezone specification
            },
            'end': {
                'dateTime': end_datetime_str,    # NO timezone in the datetime string
                'timeZone': 'Asia/Karachi'       # Explicit timezone specification
            },
            'attendees': [
                {'email': os.getenv('BUSINESS_EMAIL', 'contact@brightsmile.com')}
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 15}
                ]
            }
        }
        
        # Add patient email to attendees if provided
        if patient_email and validate_email(patient_email):
            event['attendees'].append({'email': patient_email})
        
        # Comprehensive logging before creating the event
        logger.info(f"📅 GOOGLE CALENDAR EVENT CREATION:")
        logger.info(f"  Summary: {event['summary']}")
        logger.info(f"  Start DateTime: {event['start']['dateTime']}")
        logger.info(f"  End DateTime: {event['end']['dateTime']}")
        logger.info(f"  TimeZone: {event['start']['timeZone']}")
        logger.info(f"  Expected Calendar Display: {naive_datetime.strftime('%I:%M %p')} - {naive_end_datetime.strftime('%I:%M %p')} PKT")
        
        # Create the calendar event
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        
        # Success logging
        logger.info(f"✅ APPOINTMENT CREATED SUCCESSFULLY!")
        logger.info(f"  Google Calendar Event ID: {created_event.get('id')}")
        logger.info(f"  Event URL: {created_event.get('htmlLink')}")
        logger.info(f"  User expects to see: {naive_datetime.strftime('%I:%M %p')} - {naive_end_datetime.strftime('%I:%M %p')}")
        
        # 🆕 SEND EMAIL CONFIRMATION IF EMAIL PROVIDED
        email_result = None
        if patient_email and validate_email(patient_email):
            logger.info(f"📧 SENDING CONFIRMATION EMAIL to {patient_email}")
            
            appointment_details = {
                'type': appointment_type,
                'date': appointment_date.strftime('%B %d, %Y'),
                'time': naive_datetime.strftime('%I:%M %p'),
                'duration': f'{duration_minutes} minutes',
                'event_id': created_event.get('id'),
                'event_url': created_event.get('htmlLink')
            }
            
            email_result = send_appointment_confirmation(
                patient_name=patient_name,
                patient_email=patient_email,
                appointment_details=appointment_details
            )
            
            if email_result.get('success'):
                logger.info(f"✅ Confirmation email sent successfully to {patient_email}")
            else:
                logger.warning(f"⚠️ Failed to send confirmation email: {email_result.get('message')}")
        
        return {
            'success': True,
            'message': f'Appointment successfully booked for {patient_name}',
            'appointment_details': {
                'patient_name': patient_name,
                'date': appointment_date.strftime('%B %d, %Y'),
                'time': naive_datetime.strftime('%I:%M %p'),
                'type': appointment_type,
                'duration': f'{duration_minutes} minutes',
                'event_id': created_event.get('id'),
                'event_url': created_event.get('htmlLink'),
                'timezone': 'Asia/Karachi'
            },
            'email_confirmation': {
                'sent': email_result.get('success', False) if email_result else False,
                'recipient': patient_email if patient_email else None,
                'message': email_result.get('message', 'No email provided') if email_result else 'No email provided'
            },
            'debug_info': {
                'naive_datetime': naive_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'start_datetime_str': start_datetime_str,
                'end_datetime_str': end_datetime_str,
                'timezone': 'Asia/Karachi',
                'input_validation': {
                    'original_date': str(appointment_date),
                    'original_time': str(appointment_time),
                    'original_time_type': str(type(appointment_time))
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error booking appointment: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': 'Failed to book appointment due to system error. Please try again.',
            'error': str(e)
        }

def validate_appointment_request(start_datetime, end_datetime):
    """Validate appointment request against business rules"""
    
    # Check if it's in the past
    now = datetime.now(LAHORE_TZ)
    if start_datetime <= now:
        return {
            'valid': False,
            'success': False,
            'message': 'Cannot book appointments in the past. Please select a future date and time.'
        }
    
    # Check if it's within clinic hours
    if not is_within_clinic_hours(start_datetime) or not is_within_clinic_hours(end_datetime - timedelta(minutes=1)):
        return {
            'valid': False,
            'success': False,
            'message': f'Appointments can only be booked between {CLINIC_OPEN_HOUR}:00 AM and {CLINIC_CLOSE_HOUR}:00 PM.'
        }
    
    # Check if it's on weekend (Sunday only)
    if is_weekend(start_datetime.date()):
        return {
            'valid': False,
            'success': False,
            'message': 'We are closed on Sundays. Please choose Monday through Saturday for your appointment.'
        }
    
    # Check if appointment end time exceeds clinic hours
    clinic_close_time = datetime.combine(start_datetime.date(), time(CLINIC_CLOSE_HOUR, 0)).replace(tzinfo=LAHORE_TZ)
    if end_datetime > clinic_close_time:
        return {
            'valid': False,
            'success': False,
            'message': f'Appointment would extend beyond clinic hours ({CLINIC_CLOSE_HOUR}:00 PM). Please choose an earlier time.'
        }
    
    return {'valid': True}

def get_available_slots_for_date(requested_date, duration_minutes=APPOINTMENT_DURATION):
    """
    Get all available slots for a specific date - only return if slots exist
    """
    
    # Validate the date first with correct weekend logic
    if is_weekend(requested_date):
        return {
            'success': False,
            'message': 'We are closed on Sundays. Please choose Monday through Saturday.',
            'available_slots': []
        }
    
    # Check if date is in the past
    today = datetime.now(LAHORE_TZ).date()
    if requested_date < today:
        return {
            'success': False,
            'message': 'Cannot show slots for past dates.',
            'available_slots': []
        }
    
    slots = generate_alternative_slots(requested_date, duration_minutes)
    
    # Only return success if slots actually exist
    if len(slots) == 0:
        return {
            'success': False,
            'message': f'No available slots for {requested_date.strftime("%B %d, %Y")}. Please choose a different date.',
            'available_slots': []
        }
    
    return {
        'success': True,
        'message': f'Found {len(slots)} available slots for {requested_date.strftime("%B %d, %Y")}',
        'available_slots': slots,
        'date': requested_date.strftime('%B %d, %Y')
    }

def check_today_availability():
    """Check if appointments are available today"""
    today = datetime.now(LAHORE_TZ).date()
    
    # Don't offer today if it's Sunday
    if is_weekend(today):
        return {
            'available': False,
            'message': 'We are closed on Sundays.',
            'slots': []
        }
    
    # Don't offer today if it's past business hours
    now = datetime.now(LAHORE_TZ)
    if now.hour >= CLINIC_CLOSE_HOUR:
        return {
            'available': False,
            'message': 'Business hours are over for today.',
            'slots': []
        }
    
    # Check for available slots today
    slots = generate_alternative_slots(today)
    
    # Filter out slots that are in the past
    available_slots = []
    for slot in slots:
        slot_time = datetime.fromisoformat(slot['start_time'])
        if slot_time > now + timedelta(hours=1):  # At least 1 hour from now
            available_slots.append(slot)
    
    return {
        'available': len(available_slots) > 0,
        'message': f'Found {len(available_slots)} available slots for today.',
        'slots': available_slots
    }

def get_next_few_days_availability(days=3):
    """
    Get availability for the next few days - only include days with actual slots
    """
    today = datetime.now(LAHORE_TZ).date()
    availability = {}
    
    for i in range(1, days + 8):  # Check more days to find available ones
        check_date = today + timedelta(days=i)
        
        if not is_weekend(check_date):  # Skip Sundays
            slots = generate_alternative_slots(check_date)
            if slots:  # Only include if slots are available
                availability[check_date.strftime('%Y-%m-%d')] = {
                    'date': check_date.strftime('%B %d, %Y'),
                    'day': check_date.strftime('%A'),
                    'slots': slots[:5]  # First 5 slots
                }
                
                # Stop once we have enough days with availability
                if len(availability) >= days:
                    break
    
    return availability

def debug_timezone_handling(date_str, time_str):
    """Debug function to test timezone handling"""
    try:
        # Parse inputs
        test_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        test_time = datetime.strptime(time_str, '%H:%M').time()
        
        # Create timezone-aware datetime
        naive_dt = datetime.combine(test_date, test_time)
        pkt_dt = LAHORE_TZ.localize(naive_dt)
        utc_dt = pkt_dt.astimezone(pytz.UTC)
        
        return {
            'input_date': date_str,
            'input_time': time_str,
            'naive_datetime': naive_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'pkt_datetime': pkt_dt.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'utc_datetime': utc_dt.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'pkt_iso': pkt_dt.isoformat(),
            'utc_iso': utc_dt.isoformat(),
            'calendar_event_format': {
                'dateTime': pkt_dt.isoformat(),
                'timeZone': 'Asia/Karachi'
            }
        }
        
    except Exception as e:
        return {'error': str(e)}

# Test function with enhanced timezone validation
def test_calendar_connection():
    """Test calendar connection and timezone handling with comprehensive validation"""
    print("🔍 TESTING CALENDAR CONNECTION WITH TIMEZONE VALIDATION")
    print("="*60)
    
    try:
        service = get_calendar_service()
        print("✅ Calendar service initialized")
        
        # Test calendar access
        calendar_list = service.calendarList().list().execute()
        print(f"✅ Found {len(calendar_list.get('items', []))} calendars")
        
        # Test timezone handling
        now = datetime.now(LAHORE_TZ)
        print(f"✅ Current time in PKT: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"✅ Current time in UTC: {now.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Test today's availability
        today_avail = check_today_availability()
        print(f"✅ Today's availability: {today_avail['available']} ({len(today_avail['slots'])} slots)")
        
        # Test natural date parsing
        test_dates = ['monday', 'tomorrow', 'next week', 'friday']
        for test_date in test_dates:
            parsed = parse_natural_date(test_date)
            print(f"✅ '{test_date}' -> {parsed}")
        
        # Test slot generation with timezone info
        today = now.date()
        tomorrow = today + timedelta(days=1)
        
        if not is_weekend(tomorrow):
            slots = generate_alternative_slots(tomorrow)
            print(f"✅ Tomorrow's slots: {len(slots)} available")
            
            if slots:
                first_slot = slots[0]
                print(f"   First slot example:")
                print(f"     Display time: {first_slot['formatted_time']}")
                print(f"     ISO start: {first_slot['start_time']}")
                print(f"     24h format: {first_slot['time_24h']}")
                print(f"     Timezone: {first_slot['timezone']}")
                
                # Test timezone debugging
                slot_dt = datetime.fromisoformat(first_slot['start_time'])
                print(f"     Parsed PKT: {slot_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                print(f"     Converted UTC: {slot_dt.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Test appointment booking with sample data
        print("\n🧪 Testing timezone handling...")
        test_result = debug_timezone_handling(tomorrow.strftime('%Y-%m-%d'), '13:30')
        if 'error' not in test_result:
            print(f"   Input: {test_result['input_date']} {test_result['input_time']}")
            print(f"   PKT: {test_result['pkt_datetime']}")
            print(f"   UTC: {test_result['utc_datetime']}")
            print(f"   Calendar format: {test_result['calendar_event_format']}")
        
        # Test weekend logic
        print("\n🗓️ Testing weekend logic...")
        test_sunday = today + timedelta(days=(6 - today.weekday()) % 7)
        if test_sunday.weekday() != 6:
            test_sunday += timedelta(days=7 - test_sunday.weekday() + 6)
        
        print(f"   Sunday test date: {test_sunday} (weekday: {test_sunday.weekday()})")
        print(f"   Is weekend: {is_weekend(test_sunday)}")
        
        sunday_slots = generate_alternative_slots(test_sunday)
        print(f"   Sunday slots generated: {len(sunday_slots)} (should be 0)")
        
        # 🆕 TEST EMAIL CONFIGURATION
        print("\n📧 Testing email configuration...")
        try:
            from email_service import test_email_configuration
            email_test_result = test_email_configuration()
            if email_test_result['success']:
                print("✅ Email service configured correctly")
                print(f"   SMTP Server: {email_test_result['details']['smtp_server']}")
                print(f"   From Email: {email_test_result['details']['from_email']}")
            else:
                print(f"⚠️ Email service not configured: {email_test_result['message']}")
        except ImportError:
            print("⚠️ Email service module not found")
        except Exception as e:
            print(f"⚠️ Email service test error: {e}")
        
        print("\n✅ All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Calendar test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# Additional utility functions for enhanced functionality

def get_appointment_by_id(event_id):
    """Get a specific appointment by Google Calendar event ID"""
    try:
        service = get_calendar_service()
        calendar_id = os.getenv("CALENDAR_ID", 'primary')
        
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        return {
            'success': True,
            'event': event,
            'summary': event.get('summary', 'No title'),
            'start': event.get('start', {}).get('dateTime', 'No start time'),
            'end': event.get('end', {}).get('dateTime', 'No end time'),
            'description': event.get('description', 'No description')
        }
        
    except Exception as e:
        logger.error(f"Error fetching appointment {event_id}: {e}")
        return {
            'success': False,
            'message': f'Could not retrieve appointment: {str(e)}'
        }

def cancel_appointment(event_id, reason="Cancelled by patient"):
    """Cancel an existing appointment"""
    try:
        service = get_calendar_service()
        calendar_id = os.getenv("CALENDAR_ID", 'primary')
        
        # Get the event first
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        # Update the event to mark as cancelled
        event['summary'] = f"[CANCELLED] {event.get('summary', '')}"
        event['description'] = f"{event.get('description', '')}\n\nCancellation Reason: {reason}\nCancelled at: {datetime.now(LAHORE_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}"
        
        # Update the event
        updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
        
        logger.info(f"✅ Appointment {event_id} cancelled successfully")
        
        return {
            'success': True,
            'message': 'Appointment cancelled successfully',
            'event_id': event_id,
            'updated_event': updated_event
        }
        
    except Exception as e:
        logger.error(f"Error cancelling appointment {event_id}: {e}")
        return {
            'success': False,
            'message': f'Could not cancel appointment: {str(e)}'
        }

def reschedule_appointment(event_id, new_date, new_time, duration_minutes=APPOINTMENT_DURATION):
    """Reschedule an existing appointment to a new date and time"""
    try:
        service = get_calendar_service()
        calendar_id = os.getenv("CALENDAR_ID", 'primary')
        
        # Get the existing event
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        # Create new datetime with proper timezone handling
        if isinstance(new_time, time):
            naive_datetime = datetime.combine(new_date, new_time)
            new_datetime = LAHORE_TZ.localize(naive_datetime)
        else:
            if new_time.tzinfo is None:
                new_datetime = LAHORE_TZ.localize(new_time)
            else:
                new_datetime = new_time.astimezone(LAHORE_TZ)
        
        new_end_datetime = new_datetime + timedelta(minutes=duration_minutes)
        
        # Check for conflicts at the new time
        existing_events = get_existing_appointments(new_date)
        has_conflict, conflicting_event = check_time_conflict(new_datetime, new_end_datetime, existing_events)
        
        if has_conflict:
            return {
                'success': False,
                'message': f'Cannot reschedule to {new_datetime.strftime("%I:%M %p")} - conflicts with existing appointment',
                'conflict_event': conflicting_event.get('summary', 'Unknown') if conflicting_event else 'Unknown'
            }
        
        # Update the event with new timing
        event['start'] = {
            'dateTime': new_datetime.isoformat(),
            'timeZone': 'Asia/Karachi'
        }
        event['end'] = {
            'dateTime': new_end_datetime.isoformat(),
            'timeZone': 'Asia/Karachi'
        }
        
        # Add rescheduling note to description
        original_description = event.get('description', '')
        event['description'] = f"{original_description}\n\nRescheduled at: {datetime.now(LAHORE_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}\nNew time: {new_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        
        # Update the event
        updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
        
        logger.info(f"✅ Appointment {event_id} rescheduled successfully to {new_datetime.strftime('%Y-%m-%d %H:%M %Z')}")
        
        return {
            'success': True,
            'message': 'Appointment rescheduled successfully',
            'event_id': event_id,
            'new_datetime': new_datetime.strftime('%Y-%m-%d %H:%M %Z'),
            'updated_event': updated_event
        }
        
    except Exception as e:
        logger.error(f"Error rescheduling appointment {event_id}: {e}")
        return {
            'success': False,
            'message': f'Could not reschedule appointment: {str(e)}'
        }

def get_appointments_for_date_range(start_date, end_date):
    """Get all appointments within a date range"""
    try:
        service = get_calendar_service()
        calendar_id = os.getenv("CALENDAR_ID", 'primary')
        
        # Convert dates to timezone-aware datetimes
        start_datetime = datetime.combine(start_date, time.min).replace(tzinfo=LAHORE_TZ)
        end_datetime = datetime.combine(end_date, time.max).replace(tzinfo=LAHORE_TZ)
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_datetime.isoformat(),
            timeMax=end_datetime.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Process events to extract relevant information
        appointments = []
        for event in events:
            if 'dateTime' in event.get('start', {}):
                start_dt = datetime.fromisoformat(event['start']['dateTime'])
                if start_dt.tzinfo != LAHORE_TZ:
                    start_dt = start_dt.astimezone(LAHORE_TZ)
                
                appointments.append({
                    'id': event.get('id'),
                    'summary': event.get('summary', 'No title'),
                    'start_datetime': start_dt.strftime('%Y-%m-%d %H:%M:%S %Z'),
                    'start_time': start_dt.strftime('%I:%M %p'),
                    'date': start_dt.strftime('%B %d, %Y'),
                    'description': event.get('description', ''),
                    'status': event.get('status', 'confirmed')
                })
        
        logger.info(f"Found {len(appointments)} appointments between {start_date} and {end_date}")
        
        return {
            'success': True,
            'appointments': appointments,
            'count': len(appointments),
            'date_range': f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"
        }
        
    except Exception as e:
        logger.error(f"Error fetching appointments for date range: {e}")
        return {
            'success': False,
            'message': f'Could not retrieve appointments: {str(e)}'
        }

if __name__ == "__main__":
    test_calendar_connection()


