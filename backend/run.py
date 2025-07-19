
# backend/run.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, date, time
import os
import logging
import pytz
import re

# Import your existing calendar service functions
import sys
sys.path.append('app/services')
from calendar_service import (
    book_appointment, get_available_slots_for_date, check_today_availability, 
    get_next_few_days_availability, parse_natural_date, validate_phone_number, validate_email
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Get timezone from environment
LAHORE_TZ = pytz.timezone(os.getenv('TIMEZONE', 'Asia/Karachi'))

@app.route('/api/book-appointment', methods=['POST'])
def api_book_appointment():
    """Handle appointment booking from chatbot with enhanced validation and timezone fixes"""
    try:
        data = request.json
        logger.info(f"📅 Booking request received: {data}")
        
        # Enhanced validation with proper error messages
        required_fields = ['patient_name', 'patient_phone', 'appointment_date', 'appointment_time', 'appointment_type']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            logger.error(f"❌ Missing required fields: {missing_fields}")
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}',
                'error_type': 'validation_error'
            }), 400
        
        # Validate phone number format
        if not validate_phone_number(data['patient_phone']):
            return jsonify({
                'success': False,
                'message': 'Please provide a valid phone number (e.g., +92-321-1234567 or 0321-1234567)',
                'error_type': 'phone_validation_error'
            }), 400
        
        # Validate email if provided
        if data.get('patient_email') and not validate_email(data['patient_email']):
            return jsonify({
                'success': False,
                'message': 'Please provide a valid email address',
                'error_type': 'email_validation_error'
            }), 400
        
        # CRITICAL FIX: Enhanced date and time parsing with timezone preservation
        try:
            # Handle natural language dates
            date_input = data['appointment_date']
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_input):
                # Natural language date - parse it
                appointment_date = parse_natural_date(date_input)
                logger.info(f"🔄 Natural date '{date_input}' parsed as {appointment_date}")
            else:
                appointment_date = datetime.strptime(date_input, '%Y-%m-%d').date()
            
            # CRITICAL FIX: Handle time parsing more precisely
            time_str = data['appointment_time'].strip()
            logger.info(f"🕐 PARSING TIME: '{time_str}'")
            
            # Handle different time formats
            if ':' in time_str:
                time_parts = time_str.split(':')
                if len(time_parts) == 2:
                    # HH:MM format
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    appointment_time = time(hour, minute)
                elif len(time_parts) == 3:
                    # HH:MM:SS format
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    # Ignore seconds for appointment booking
                    appointment_time = time(hour, minute)
                else:
                    raise ValueError(f"Invalid time format: {time_str}")
            else:
                raise ValueError(f"Time must contain ':' separator: {time_str}")
                
            logger.info(f"📅 Parsed date: {appointment_date}, time: {appointment_time}")
            
        except ValueError as e:
            logger.error(f"❌ Date/time parsing error: {e}")
            return jsonify({
                'success': False,
                'message': f'Invalid date or time format. Expected YYYY-MM-DD for date and HH:MM for time. Error: {str(e)}',
                'error_type': 'date_time_parsing_error'
            }), 400
        
        # CRITICAL FIX: Timezone-aware validation
        now_local = datetime.now(LAHORE_TZ)
        appointment_datetime_local = LAHORE_TZ.localize(datetime.combine(appointment_date, appointment_time))
        
        logger.info(f"🕐 TIMEZONE COMPARISON:")
        logger.info(f"  Current time (PKT): {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"  Appointment time (PKT): {appointment_datetime_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"  Current time (UTC): {now_local.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"  Appointment time (UTC): {appointment_datetime_local.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        if appointment_datetime_local <= now_local:
            logger.error(f"❌ Appointment in the past: {appointment_datetime_local} <= {now_local}")
            return jsonify({
                'success': False,
                'message': 'Cannot book appointments in the past. Please select a future date and time.',
                'error_type': 'past_appointment_error',
                'debug_info': {
                    'current_time_pkt': now_local.strftime('%Y-%m-%d %H:%M:%S %Z'),
                    'appointment_time_pkt': appointment_datetime_local.strftime('%Y-%m-%d %H:%M:%S %Z')
                }
            }), 400
        
        # Validate business hours (9 AM to 7 PM)
        if appointment_time.hour < 9 or appointment_time.hour >= 19:
            logger.error(f"❌ Outside business hours: {appointment_time}")
            return jsonify({
                'success': False,
                'message': 'Appointments can only be booked between 9:00 AM and 7:00 PM.',
                'error_type': 'business_hours_error'
            }), 400
        
        # Validate not Sunday (weekday 6)
        if appointment_date.weekday() == 6:  # Sunday
            logger.error(f"❌ Appointment on Sunday: {appointment_date}")
            return jsonify({
                'success': False,
                'message': 'We are closed on Sundays. Please choose Monday through Saturday.',
                'error_type': 'weekend_error'
            }), 400
        
        # CRITICAL FIX: Call calendar service with proper logging
        logger.info("🔄 Calling calendar service with exact parameters...")
        logger.info(f"  patient_name: {data['patient_name']}")
        logger.info(f"  patient_phone: {data['patient_phone']}")
        logger.info(f"  appointment_date: {appointment_date} (type: {type(appointment_date)})")
        logger.info(f"  appointment_time: {appointment_time} (type: {type(appointment_time)})")
        logger.info(f"  appointment_type: {data['appointment_type']}")
        
        result = book_appointment(
            patient_name=data['patient_name'],
            patient_phone=data['patient_phone'],
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            duration_minutes=int(data.get('duration_minutes', 60)),  # Default 1 hour
            appointment_type=data['appointment_type']
        )
        
        logger.info(f"✅ Booking result: {result}")
        
        # Add debugging info to response for successful bookings
        if result.get('success'):
            result['debug_info'] = {
                'parsed_date': appointment_date.strftime('%Y-%m-%d'),
                'parsed_time': appointment_time.strftime('%H:%M'),
                'timezone': 'Asia/Karachi',
                'appointment_datetime_pkt': appointment_datetime_local.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'appointment_datetime_utc': appointment_datetime_local.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S %Z')
            }
        else:
            logger.warning(f"🚨 Booking failed: {result.get('message')}")
            
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in booking: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}',
            'error_type': 'server_error'
        }), 500

@app.route('/api/available-slots', methods=['GET'])
def api_available_slots():
    """Get available time slots for a specific date with natural language support and enhanced timezone handling"""
    try:
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({
                'success': False,
                'message': 'Date parameter is required',
                'error_type': 'missing_parameter'
            }), 400
            
        logger.info(f"🔍 Checking slots for date: '{date_str}'")
        
        # Handle natural language dates
        try:
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                logger.info(f"📅 Standard date format parsed: {appointment_date}")
            else:
                # Natural language date
                appointment_date = parse_natural_date(date_str)
                logger.info(f"🔄 Natural date '{date_str}' parsed as {appointment_date}")
        except ValueError as e:
            logger.error(f"❌ Invalid date format: {date_str}")
            return jsonify({
                'success': False,
                'message': f'Invalid date format. Expected YYYY-MM-DD or natural language like "monday", "tomorrow". Got: {date_str}',
                'error_type': 'date_format_error'
            }), 400
        
        # Validate date is not in the past
        today = datetime.now(LAHORE_TZ).date()
        
        if appointment_date < today:
            logger.warning(f"⚠️ Past date requested: {appointment_date}")
            return jsonify({
                'success': False,
                'message': 'Cannot show slots for past dates.',
                'available_slots': [],
                'error_type': 'past_date_error'
            })
        
        # Validate not Sunday
        if appointment_date.weekday() == 6:  # Sunday
            logger.warning(f"⚠️ Sunday requested: {appointment_date}")
            return jsonify({
                'success': False,
                'message': 'We are closed on Sundays. Please choose Monday through Saturday.',
                'available_slots': [],
                'error_type': 'weekend_error'
            })
        
        # Call your existing calendar service
        result = get_available_slots_for_date(appointment_date)
        
        # CRITICAL FIX: Add the parsed date to the response for frontend consistency
        if result.get('success'):
            result['date'] = appointment_date.strftime('%B %d, %Y')  # Add human-readable date
            result['date_iso'] = appointment_date.strftime('%Y-%m-%d')  # Add ISO format
            
        logger.info(f"📅 Available slots result: {len(result.get('available_slots', []))} slots found")
        
        # Enhanced debugging info
        if result.get('success'):
            slots = result.get('available_slots', [])
            logger.info(f"✅ Found {len(slots)} available slots")
            for i, slot in enumerate(slots[:3]):  # Log first 3 slots
                logger.info(f"  Slot {i+1}: {slot.get('formatted_time', 'No time')} ({slot.get('start_time', 'No start')})")
        else:
            logger.warning(f"⚠️ No slots available: {result.get('message')}")
            
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Error fetching available slots: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error fetching available slots: {str(e)}',
            'error_type': 'server_error'
        }), 500

@app.route('/api/today-availability', methods=['GET'])
def api_today_availability():
    """Check today's availability with proper timezone handling"""
    try:
        result = check_today_availability()
        logger.info(f"📅 Today's availability: {result['available']} ({len(result['slots'])} slots)")
        
        now_local = datetime.now(LAHORE_TZ)
        
        return jsonify({
            'success': True,
            'available': result['available'],
            'message': result['message'],
            'available_slots': result['slots'],
            'date': now_local.date().strftime('%Y-%m-%d'),
            'current_time': now_local.strftime('%H:%M'),
            'current_time_formatted': now_local.strftime('%Y-%m-%d %H:%M:%S %Z')
        })
        
    except Exception as e:
        logger.error(f"❌ Error checking today's availability: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error checking today\'s availability: {str(e)}',
            'error_type': 'server_error'
        }), 500

@app.route('/api/next-days-availability', methods=['GET'])
def api_next_days_availability():
    """Get availability for the next few days - only days with actual availability"""
    try:
        days = request.args.get('days', 3, type=int)
        if days < 1 or days > 7:
            days = 3
            
        result = get_next_few_days_availability(days)
        logger.info(f"📅 Next {days} days availability: {len(result)} days with slots")
        
        return jsonify({
            'success': True,
            'availability': result,
            'days_checked': days,
            'message': f'Found {len(result)} days with available appointments',
            'timezone': 'Asia/Karachi'
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting next days availability: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting availability: {str(e)}',
            'error_type': 'server_error'
        }), 500

@app.route('/api/parse-date', methods=['POST'])
def api_parse_date():
    """Parse natural language dates for testing"""
    try:
        data = request.json
        date_input = data.get('date_input', '')
        
        if not date_input:
            return jsonify({
                'success': False,
                'message': 'date_input is required'
            }), 400
        
        parsed_date = parse_natural_date(date_input)
        
        return jsonify({
            'success': True,
            'input': date_input,
            'parsed_date': parsed_date.strftime('%Y-%m-%d'),
            'formatted_date': parsed_date.strftime('%B %d, %Y'),
            'day_of_week': parsed_date.strftime('%A'),
            'is_weekend': parsed_date.weekday() == 6
        })
        
    except Exception as e:
        logger.error(f"❌ Error parsing date: {e}")
        return jsonify({
            'success': False,
            'message': f'Error parsing date: {str(e)}',
            'error_type': 'parsing_error'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint with timezone debugging"""
    now_local = datetime.now(LAHORE_TZ)
    now_utc = datetime.now(pytz.UTC)
    
    return jsonify({
        'status': 'healthy',
        'message': 'Dental Office AI Receptionist API is running',
        'calendar_integration': 'Active',
        'timezone_info': {
            'server_timezone': 'Asia/Karachi',
            'current_time_pkt': now_local.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'current_time_utc': now_utc.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'timezone_offset': now_local.strftime('%z')
        },
        'business_hours': '9:00 AM - 7:00 PM (Mon-Sat), Closed (Sun)',
        'features': {
            'natural_language_dates': True,
            'phone_validation': True,
            'email_validation': True,
            'time_conflict_checking': True,
            'availability_filtering': True,
            'timezone_preservation': True
        }
    })

@app.route('/api/test-weekend', methods=['GET'])
def test_weekend_logic():
    """Test weekend detection logic"""
    try:
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({
                'error': 'Date parameter required (YYYY-MM-DD format)'
            }), 400
        
        test_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        weekday_num = test_date.weekday()  # 0=Monday, 6=Sunday
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        is_sunday = weekday_num == 6
        is_weekend_result = is_sunday
        
        # Test the slots API
        slots_result = get_available_slots_for_date(test_date)
        
        return jsonify({
            'date': date_str,
            'weekday_number': weekday_num,
            'day_name': day_names[weekday_num],
            'is_sunday': is_sunday,
            'is_weekend': is_weekend_result,
            'should_be_closed': is_weekend_result,
            'slots_api_result': {
                'success': slots_result.get('success'),
                'message': slots_result.get('message'),
                'slots_count': len(slots_result.get('available_slots', []))
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/test-timezone', methods=['GET'])
def test_timezone():
    """Test timezone handling for debugging appointment times"""
    try:
        # Test data
        test_time_str = request.args.get('time', '10:30')
        test_date_str = request.args.get('date', datetime.now(LAHORE_TZ).date().strftime('%Y-%m-%d'))
        
        # Parse the test data
        test_date = datetime.strptime(test_date_str, '%Y-%m-%d').date()
        test_time_parts = test_time_str.split(':')
        test_time = time(int(test_time_parts[0]), int(test_time_parts[1]))
        
        # Create timezone-aware datetime
        naive_datetime = datetime.combine(test_date, test_time)
        pkt_datetime = LAHORE_TZ.localize(naive_datetime)
        utc_datetime = pkt_datetime.astimezone(pytz.UTC)
        
        # Current time for comparison
        now_pkt = datetime.now(LAHORE_TZ)
        now_utc = datetime.now(pytz.UTC)
        
        return jsonify({
            'test_input': {
                'date': test_date_str,
                'time': test_time_str
            },
            'parsed_values': {
                'date_object': test_date.strftime('%Y-%m-%d'),
                'time_object': test_time.strftime('%H:%M:%S'),
                'naive_datetime': naive_datetime.strftime('%Y-%m-%d %H:%M:%S')
            },
            'timezone_conversions': {
                'pkt_datetime': pkt_datetime.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'utc_datetime': utc_datetime.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'pkt_iso': pkt_datetime.isoformat(),
                'utc_iso': utc_datetime.isoformat()
            },
            'current_time': {
                'now_pkt': now_pkt.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'now_utc': now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')
            },
            'validation': {
                'is_future': pkt_datetime > now_pkt,
                'time_difference_minutes': int((pkt_datetime - now_pkt).total_seconds() / 60),
                'is_business_hours': 9 <= test_time.hour < 19,
                'is_weekend': test_date.weekday() == 6
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'error_type': 'timezone_test_error'
        }), 500

@app.route('/', methods=['GET'])
def index():
    """API info endpoint"""
    now_local = datetime.now(LAHORE_TZ)
    
    return jsonify({
        'service': 'Dental Office AI Receptionist',
        'version': '2.1',
        'timezone': 'Asia/Karachi (PKT)',
        'current_time': now_local.strftime('%Y-%m-%d %H:%M:%S %Z'),
        'business_hours': {
            'weekdays': 'Monday-Friday: 9:00 AM - 7:00 PM',
            'saturday': 'Saturday: 9:00 AM - 7:00 PM', 
            'sunday': 'Sunday: Closed'
        },
        'endpoints': [
            'POST /api/book-appointment',
            'GET /api/available-slots?date=YYYY-MM-DD',
            'GET /api/today-availability',
            'GET /api/next-days-availability?days=3',
            'POST /api/parse-date',
            'GET /api/health',
            'GET /api/test-weekend?date=YYYY-MM-DD',
            'GET /api/test-timezone?date=YYYY-MM-DD&time=HH:MM'
        ],
        'features': {
            'natural_language_dates': 'Supports "monday", "tomorrow", "next week"',
            'validation': 'Phone numbers and email addresses',
            'smart_availability': 'Only shows days with actual slots',
            'conflict_detection': 'Prevents double bookings',
            'timezone_preservation': 'Maintains exact appointment times',
            'enhanced_debugging': 'Comprehensive logging and testing endpoints'
        },
        'fixes_applied': [
            'Fixed name collection flow with proper button timing',
            'Fixed timezone handling to prevent time mismatches',
            'Preserved exact slot timing from frontend to calendar',
            'Enhanced validation and error handling',
            'Added comprehensive debugging endpoints'
        ]
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'message': 'Endpoint not found',
        'available_endpoints': [
            'POST /api/book-appointment',
            'GET /api/available-slots',
            'GET /api/today-availability',
            'GET /api/next-days-availability',
            'POST /api/parse-date',
            'GET /api/health',
            'GET /api/test-timezone'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'message': 'Internal server error',
        'error_type': 'server_error'
    }), 500

if __name__ == "__main__":
    print("🦷 Starting Dental Office AI Receptionist Backend v2.1...")
    print("📅 Calendar Integration: Active")
    print("🕒 Business Hours: Mon-Sat 9AM-7PM, Sun Closed")
    print("🌍 Timezone: Asia/Karachi (PKT)")
    
    now_local = datetime.now(LAHORE_TZ)
    print(f"🕐 Current Time: {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("🤖 Chatbot API: Ready")
    print("🌐 Server: http://localhost:5000")
    print("🔗 Frontend should connect to: http://localhost:3000")
    
    print("\n🧪 Test endpoints:")
    print("  Health: http://localhost:5000/api/health")
    print("  Today: http://localhost:5000/api/today-availability")
    print("  Weekend test: http://localhost:5000/api/test-weekend?date=2025-07-27")
    print("  Slots test: http://localhost:5000/api/available-slots?date=2025-07-28")
    print("  Timezone test: http://localhost:5000/api/test-timezone?date=2025-07-23&time=10:30")
    print("  Natural date: curl -X POST http://localhost:5000/api/parse-date -H 'Content-Type: application/json' -d '{\"date_input\": \"monday\"}'")
    
    print("\n🚀 CRITICAL FIXES APPLIED:")
    print("  ✅ Name Collection: Fixed flow to show personalized greeting before buttons")
    print("  ✅ Timezone Handling: Preserved exact appointment times from slot selection")
    print("  ✅ Calendar Sync: User sees 10:30 AM, calendar gets exactly 10:30 AM PKT")
    print("  ✅ Button UX: Improved timing and user experience")
    print("  ✅ Validation: Enhanced phone/email validation")
    print("  ✅ Debugging: Added comprehensive test endpoints")
    
    print("\n🔧 DEBUGGING NOTES:")
    print("  • Use /api/test-timezone to verify time handling")
    print("  • Check logs for detailed timezone conversion info")
    print("  • All times are preserved in PKT (Asia/Karachi)")
    print("  • Frontend slot data includes exact ISO timestamps")
    
    app.run(host='0.0.0.0', port=5000, debug=True)