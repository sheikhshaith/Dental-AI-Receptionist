
import os
from datetime import datetime, timedelta, time, date
import pytz
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import logging

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']

# Clinic Configuration - FIXED: Use environment variables
CLINIC_OPEN_HOUR = int(os.getenv('BUSINESS_HOURS_START', 9))    # 9 AM
CLINIC_CLOSE_HOUR = int(os.getenv('BUSINESS_HOURS_END', 19))   # 7 PM
APPOINTMENT_DURATION = int(os.getenv('APPOINTMENT_DURATION_MINUTES', 60))  # 60 minutes default
BUFFER_TIME = int(os.getenv('BUFFER_TIME_MINUTES', 15))  # 15 minutes buffer between appointments
# Using 'Asia/Karachi' which is the standard IANA timezone for Pakistan
LAHORE_TZ = pytz.timezone(os.getenv('TIMEZONE', 'Asia/Karachi'))

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
    """Check if the date falls on weekend - FIXED: Only Sunday is closed"""
    # Monday=0, Tuesday=1, ..., Saturday=5, Sunday=6
    day_of_week = appointment_date.weekday()
    
    logger.info(f"Checking weekend for {appointment_date}: weekday={day_of_week} ({'Sunday' if day_of_week == 6 else 'Saturday' if day_of_week == 5 else 'Weekday'})")
    
    # FIXED: Only Sunday (6) is closed, Saturday (5) is open
    return day_of_week == 6  # Only Sunday

def get_existing_appointments(date):
    """Get all appointments for a specific date"""
    try:
        service = get_calendar_service()
        calendar_id = os.getenv("CALENDAR_ID", 'primary')
        
        # FIXED: Set time range for the day with proper timezone
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
            
            # FIXED: Better timezone handling
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
    """Generate alternative available time slots for the requested date"""
    try:
        # Get existing appointments
        existing_events = get_existing_appointments(requested_date)
        
        logger.info(f"Found {len(existing_events)} existing appointments for {requested_date}")
        
        # Generate possible time slots (every 30 minutes)
        slots = []
        current_time = datetime.combine(requested_date, time(CLINIC_OPEN_HOUR, 0)).replace(tzinfo=LAHORE_TZ)
        end_time = datetime.combine(requested_date, time(CLINIC_CLOSE_HOUR, 0)).replace(tzinfo=LAHORE_TZ)
        
        while current_time + timedelta(minutes=duration_minutes) <= end_time:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            
            # Check if this slot conflicts with existing appointments
            has_conflict, conflicting_event = check_time_conflict(current_time, slot_end, existing_events)
            
            if not has_conflict:
                slots.append({
                    'start_time': current_time.isoformat(),  # Store as ISO string with timezone
                    'end_time': slot_end.isoformat(),
                    'formatted_time': current_time.strftime('%I:%M %p')
                })
                logger.info(f"  ✓ Available slot: {current_time.strftime('%I:%M %p')}")
            else:
                conflicting_summary = conflicting_event.get('summary', 'Unknown appointment') if conflicting_event else 'Unknown conflict'
                logger.info(f"  ✗ Conflict with: {conflicting_summary}")
            
            # Move to next 30-minute slot
            current_time += timedelta(minutes=30)
        
        logger.info(f"Generated {len(slots)} available slots")
        return slots
        
    except Exception as e:
        logger.error(f"Error generating alternative slots: {e}")
        return []

def book_appointment(patient_name, patient_phone, appointment_date, appointment_time, duration_minutes=APPOINTMENT_DURATION, appointment_type="General Checkup"):
    """
    Book an appointment with conflict checking and validation
    """
    try:
        # Combine date and time with proper timezone
        # First create a naive datetime in local time
        naive_datetime = datetime.combine(appointment_date, appointment_time)
        # Localize to LAHORE_TZ
        appointment_datetime = LAHORE_TZ.localize(naive_datetime)
        appointment_end = appointment_datetime + timedelta(minutes=duration_minutes)
        
        # Log the time in both local and UTC for debugging
        logger.info(f"🔍 BOOKING REQUEST (Local): {appointment_datetime.strftime('%Y-%m-%d %H:%M %Z')} - {appointment_end.strftime('%H:%M %Z')}")
        logger.info(f"🔍 BOOKING REQUEST (UTC): {appointment_datetime.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M %Z')} - {appointment_end.astimezone(pytz.UTC).strftime('%H:%M %Z')}")
        
        # Validation checks
        validation_result = validate_appointment_request(appointment_datetime, appointment_end)
        if not validation_result['valid']:
            return validation_result
        
        # ULTRA STRICT CONFLICT CHECKING
        existing_events = get_existing_appointments(appointment_date)
        logger.info(f"🔍 BOOKING VALIDATION: Checking {appointment_datetime.strftime('%H:%M')} - {appointment_end.strftime('%H:%M')}")
        logger.info(f"Found {len(existing_events)} existing appointments to check against")
        
        has_conflict, conflicting_event = check_time_conflict(appointment_datetime, appointment_end, existing_events)
        
        if has_conflict:
            conflicting_start = conflicting_event['start']['dateTime'] if conflicting_event else 'Unknown'
            conflicting_summary = conflicting_event.get('summary', 'Unknown appointment') if conflicting_event else 'Unknown'
            
            logger.error(f"🚨 APPOINTMENT BOOKING BLOCKED!")
            logger.error(f"  ❌ Requested: {appointment_datetime.strftime('%H:%M')} - {appointment_end.strftime('%H:%M')}")
            logger.error(f"  ⚠️  Conflicts with: {conflicting_summary}")
            
            # Generate alternatives
            alternatives = generate_alternative_slots(appointment_date, duration_minutes)
            
            return {
                'success': False,
                'message': f'🚫 BOOKING DENIED: Time slot {appointment_time.strftime("%I:%M %p")} conflicts with existing appointment "{conflicting_summary}". Please choose a different time.',
                'conflict_details': {
                    'existing_appointment': conflicting_summary,
                    'existing_time': conflicting_start,
                    'requested_time': appointment_time.strftime('%I:%M %p'),
                    'reason': 'Time slot overlap detected'
                },
                'alternatives': alternatives[:5],
                'has_alternatives': len(alternatives) > 0,
                'alternative_message': f"📋 Available time slots for {appointment_date.strftime('%B %d, %Y')}:"
            }
        
        logger.info("✅ No conflicts detected - proceeding with appointment creation...")
        
        # Create the appointment - FIXED: Proper timezone specification
        service = get_calendar_service()
        calendar_id = os.getenv("CALENDAR_ID", 'primary')
        
        event = {
            'summary': f'🦷 {appointment_type} - {patient_name}',
            'location': os.getenv('BUSINESS_ADDRESS', 'Bright Smile Dental Office'),
            'description': f'''
Patient: {patient_name}
Phone: {patient_phone}
Type: {appointment_type}
Duration: {duration_minutes} minutes

Booked via AI Receptionist
            '''.strip(),
            'start': {
                'dateTime': appointment_datetime.isoformat(),
                'timeZone': 'Asia/Karachi',  # Use standard IANA timezone name
            },
            'end': {
                'dateTime': appointment_end.isoformat(),
                'timeZone': 'Asia/Karachi',  # Use standard IANA timezone name
            },
            'attendees': [
                {'email': os.getenv('BUSINESS_EMAIL', 'contact@brightsmile.com')}
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 15}  # 15 minutes before
                ]
            }
        }
        
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        
        logger.info(f"✅ Appointment booked successfully for {patient_name} at {appointment_datetime.strftime('%Y-%m-%d %H:%M %Z')}")
        
        return {
            'success': True,
            'message': f'Appointment successfully booked for {patient_name}',
            'appointment_details': {
                'patient_name': patient_name,
                'date': appointment_date.strftime('%B %d, %Y'),
                'time': appointment_time.strftime('%I:%M %p'),
                'type': appointment_type,
                'duration': f'{duration_minutes} minutes',
                'event_id': created_event.get('id'),
                'event_url': created_event.get('htmlLink')
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
    """Validate appointment request against business rules - FIXED"""
    
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
    
    # FIXED: Check if it's on weekend (Sunday only)
    if is_weekend(start_datetime.date()):
        return {
            'valid': False,
            'success': False,
            'message': 'We are closed on Sundays. Please choose Monday through Saturday for your appointment.'
        }
    
    # Check if appointment end time exceeds clinic hours
    if end_datetime.hour >= CLINIC_CLOSE_HOUR:
        return {
            'valid': False,
            'success': False,
            'message': f'Appointment would extend beyond clinic hours ({CLINIC_CLOSE_HOUR}:00 PM). Please choose an earlier time.'
        }
    
    return {'valid': True}

def get_available_slots_for_date(requested_date, duration_minutes=APPOINTMENT_DURATION):
    """Get all available slots for a specific date - FIXED"""
    
    # FIXED: Validate the date first with correct weekend logic
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
    """Get availability for the next few days"""
    today = datetime.now(LAHORE_TZ).date()
    availability = {}
    
    for i in range(1, days + 1):  # Start from tomorrow
        check_date = today + timedelta(days=i)
        
        if not is_weekend(check_date):  # Skip Sundays
            slots = generate_alternative_slots(check_date)
            if slots:
                availability[check_date.strftime('%Y-%m-%d')] = {
                    'date': check_date.strftime('%B %d, %Y'),
                    'day': check_date.strftime('%A'),
                    'slots': slots[:5]  # First 5 slots
                }
    
    return availability

# Test function
def test_calendar_connection():
    """Test calendar connection and permissions"""
    print("🔍 TESTING CALENDAR CONNECTION")
    print("="*50)
    
    try:
        service = get_calendar_service()
        print("✅ Calendar service initialized")
        
        # Test calendar access
        calendar_list = service.calendarList().list().execute()
        print(f"✅ Found {len(calendar_list.get('items', []))} calendars")
        
        # Test timezone handling
        now = datetime.now(LAHORE_TZ)
        print(f"✅ Current time in PKT: {now.strftime('%Y-%m-%d %H:%M %Z')}")
        
        # Test today's availability
        today_avail = check_today_availability()
        print(f"✅ Today's availability: {today_avail['available']} ({len(today_avail['slots'])} slots)")
        
        return True
        
    except Exception as e:
        print(f"❌ Calendar test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_calendar_connection()