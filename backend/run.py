
# backend/run.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, date, time
import os
import logging
import pytz

# Import your existing calendar service functions
import sys
sys.path.append('app/services')
from calendar_service import book_appointment, get_available_slots_for_date, check_today_availability, get_next_few_days_availability

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# FIXED: Get timezone from environment
LAHORE_TZ = pytz.timezone(os.getenv('TIMEZONE', 'Asia/Karachi'))

@app.route('/api/book-appointment', methods=['POST'])
def api_book_appointment():
    """Handle appointment booking from chatbot"""
    try:
        data = request.json
        logger.info(f"📅 Booking request received: {data}")
        
        # Validate required fields
        required_fields = ['patient_name', 'patient_phone', 'appointment_date', 'appointment_time', 'appointment_type']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            logger.error(f"❌ Missing required fields: {missing_fields}")
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # FIXED: Parse the date and time with better error handling
        try:
            appointment_date = datetime.strptime(data['appointment_date'], '%Y-%m-%d').date()
            
            # FIXED: Handle both HH:MM and HH:MM:SS formats
            time_str = data['appointment_time']
            if len(time_str.split(':')) == 2:
                appointment_time = datetime.strptime(time_str, '%H:%M').time()
            else:
                appointment_time = datetime.strptime(time_str, '%H:%M:%S').time()
                
            logger.info(f"📅 Parsed date: {appointment_date}, time: {appointment_time}")
        except ValueError as e:
            logger.error(f"❌ Date/time parsing error: {e}")
            return jsonify({
                'success': False,
                'message': f'Invalid date or time format. Expected YYYY-MM-DD for date and HH:MM for time. Error: {str(e)}'
            }), 400
        
        # FIXED: Validate appointment is not in the past with same timezone
        now = datetime.now(LAHORE_TZ)
        appointment_datetime = datetime.combine(appointment_date, appointment_time).replace(tzinfo=LAHORE_TZ)
        
        logger.info(f"🕐 Time comparison: appointment={appointment_datetime.strftime('%Y-%m-%d %H:%M %Z')}, now={now.strftime('%Y-%m-%d %H:%M %Z')}")
        
        if appointment_datetime <= now:
            logger.error(f"❌ Appointment in the past: {appointment_datetime} <= {now}")
            return jsonify({
                'success': False,
                'message': 'Cannot book appointments in the past. Please select a future date and time.'
            }), 400
        
        # FIXED: Validate business hours (9 AM to 7 PM)
        if appointment_time.hour < 9 or appointment_time.hour >= 19:
            logger.error(f"❌ Outside business hours: {appointment_time}")
            return jsonify({
                'success': False,
                'message': 'Appointments can only be booked between 9:00 AM and 7:00 PM.'
            }), 400
        
        # FIXED: Validate not Sunday (weekday 6)
        if appointment_date.weekday() == 6:  # Sunday
            logger.error(f"❌ Appointment on Sunday: {appointment_date}")
            return jsonify({
                'success': False,
                'message': 'We are closed on Sundays. Please choose Monday through Saturday.'
            }), 400
        
        # Call your existing calendar service
        logger.info("🔄 Calling calendar service...")
        result = book_appointment(
            patient_name=data['patient_name'],
            patient_phone=data['patient_phone'],
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            duration_minutes=int(data.get('duration_minutes', 60)),  # Default 1 hour
            appointment_type=data['appointment_type']
        )
        
        logger.info(f"✅ Booking result: {result}")
        
        # FIXED: Add debugging info to response
        if not result.get('success'):
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
    """Get available time slots for a specific date"""
    try:
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({
                'success': False,
                'message': 'Date parameter is required'
            }), 400
            
        logger.info(f"🔍 Checking slots for date: {date_str}")
        
        # FIXED: Parse date with better error handling
        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError as e:
            logger.error(f"❌ Invalid date format: {date_str}")
            return jsonify({
                'success': False,
                'message': f'Invalid date format. Expected YYYY-MM-DD, got: {date_str}'
            }), 400
        
        # FIXED: Validate date is not in the past
        today = datetime.now(LAHORE_TZ).date()
        
        if appointment_date < today:
            logger.warning(f"⚠️ Past date requested: {appointment_date}")
            return jsonify({
                'success': False,
                'message': 'Cannot show slots for past dates.',
                'available_slots': []
            })
        
        # FIXED: Validate not Sunday
        if appointment_date.weekday() == 6:  # Sunday
            logger.warning(f"⚠️ Sunday requested: {appointment_date}")
            return jsonify({
                'success': False,
                'message': 'We are closed on Sundays. Please choose Monday through Saturday.',
                'available_slots': []
            })
        
        # Call your existing calendar service
        result = get_available_slots_for_date(appointment_date)
        
        logger.info(f"📅 Available slots result: {len(result.get('available_slots', []))} slots found")
        
        # FIXED: Add debugging info
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
        # Import here to avoid circular imports
        from calendar_service import check_today_availability
        
        result = check_today_availability()
        logger.info(f"📅 Today's availability: {result['available']} ({len(result['slots'])} slots)")
        
        return jsonify({
            'success': True,
            'available': result['available'],
            'message': result['message'],
            'available_slots': result['slots'],
            'date': datetime.now(LAHORE_TZ).date().strftime('%Y-%m-%d'),
            'current_time': datetime.now(LAHORE_TZ).strftime('%H:%M')
        })
        
    except Exception as e:
        logger.error(f"❌ Error checking today's availability: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error checking today\'s availability: {str(e)}'
        }), 500

@app.route('/api/next-days-availability', methods=['GET'])
def api_next_days_availability():
    """Get availability for the next few days"""
    try:
        days = request.args.get('days', 3, type=int)
        if days < 1 or days > 7:
            days = 3
            
        result = get_next_few_days_availability(days)
        logger.info(f"📅 Next {days} days availability: {len(result)} days with slots")
        
        return jsonify({
            'success': True,
            'availability': result,
            'days_checked': days
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting next days availability: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting availability: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Dental Office AI Receptionist API is running',
        'calendar_integration': 'Active',
        'timezone': 'Asia/Karachi',
        'business_hours': '9:00 AM - 7:00 PM (Mon-Fri), 9:00 AM - 3:00 PM (Sat), Closed (Sun)',
        'current_time': datetime.now(LAHORE_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')
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

@app.route('/', methods=['GET'])
def index():
    """API info endpoint"""
    return jsonify({
        'service': 'Dental Office AI Receptionist',
        'version': '1.0',
        'timezone': 'Asia/Karachi (PKT)',
        'current_time': datetime.now(LAHORE_TZ).strftime('%Y-%m-%d %H:%M:%S %Z'),
        'business_hours': {
            'weekdays': 'Monday-Friday: 9:00 AM - 7:00 PM',
            'saturday': 'Saturday: 9:00 AM - 3:00 PM', 
            'sunday': 'Sunday: Closed'
        },
        'endpoints': [
            'POST /api/book-appointment',
            'GET /api/available-slots?date=YYYY-MM-DD',
            'GET /api/today-availability',
            'GET /api/next-days-availability?days=3',
            'GET /api/health',
            'GET /api/test-weekend?date=YYYY-MM-DD'
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
            'GET /api/health'
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
    print("🦷 Starting Dental Office AI Receptionist Backend...")
    print("📅 Calendar Integration: Active")
    print("🕒 Business Hours: Mon-Fri 9AM-7PM, Sat 9AM-3PM, Sun Closed")
    print("🌍 Timezone: Asia/Karachi (PKT)")
    print(f"🕐 Current Time: {datetime.now(LAHORE_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("🤖 Chatbot API: Ready")
    print("🌐 Server: http://localhost:5000")
    print("🔗 Frontend should connect to: http://localhost:3000")
    print("\n🧪 Test endpoints:")
    print("  Health: http://localhost:5000/api/health")
    print("  Today: http://localhost:5000/api/today-availability")
    print("  Weekend test: http://localhost:5000/api/test-weekend?date=2025-07-27")
    print("  Slots test: http://localhost:5000/api/available-slots?date=2025-07-28")
    
    app.run(host='0.0.0.0', port=5000, debug=True)