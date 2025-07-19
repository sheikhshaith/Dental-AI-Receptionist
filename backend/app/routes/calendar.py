# app/routes/calendar.py
"""
Calendar and appointment management endpoints
"""
import logging
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from app.services.calendar_service import CalendarService
from app.utils.validators import InputValidator
from app.utils.exceptions import ValidationError, CalendarServiceError

logger = logging.getLogger(__name__)
calendar_bp = Blueprint('calendar', __name__)

# Global calendar service instance
calendar_service = CalendarService()

@calendar_bp.route('/calendar/availability/<date>', methods=['GET'])
def get_availability(date):
    """Get available appointment slots for a specific date"""
    try:
        # Validate date format
        date_obj = InputValidator.validate_date_string(date)
        
        # Get duration parameter
        duration = request.args.get('duration', 60, type=int)
        if not (15 <= duration <= 240):  # 15 minutes to 4 hours
            return jsonify({'error': 'Duration must be between 15 and 240 minutes'}), 400
        
        # Get available slots
        available_slots = calendar_service.get_available_slots(date_obj, duration)
        
        logger.info(f"Retrieved {len(available_slots)} available slots for {date}")
        
        return jsonify({
            'date': date,
            'available_slots': [slot.to_dict() for slot in available_slots],
            'business_hours': {
                'start': f"{calendar_service.config.BUSINESS_HOURS_START}:00",
                'end': f"{calendar_service.config.BUSINESS_HOURS_END}:00"
            }
        })
        
    except ValidationError as e:
        logger.warning(f"Validation error in availability check: {e}")
        return jsonify({'error': str(e)}), 400
        
    except CalendarServiceError as e:
        logger.error(f"Calendar service error: {e}")
        return jsonify({'error': 'Calendar service temporarily unavailable'}), 503
        
    except Exception as e:
        logger.error(f"Unexpected error in availability check: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@calendar_bp.route('/calendar/upcoming', methods=['GET'])
def get_upcoming_appointments():
    """Get upcoming appointments"""
    try:
        # Get query parameters
        days_ahead = request.args.get('days', 7, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        # Validate parameters
        if not (1 <= days_ahead <= 365):
            return jsonify({'error': 'Days ahead must be between 1 and 365'}), 400
        
        if not (1 <= limit <= 100):
            return jsonify({'error': 'Limit must be between 1 and 100'}), 400
        
        # Get appointments
        appointments = calendar_service.get_upcoming_appointments(days_ahead, limit)
        
        logger.info(f"Retrieved {len(appointments)} upcoming appointments")
        
        return jsonify({
            'appointments': appointments,
            'count': len(appointments),
            'days_ahead': days_ahead
        })
        
    except CalendarServiceError as e:
        logger.error(f"Calendar service error: {e}")
        return jsonify({'error': 'Calendar service temporarily unavailable'}), 503
        
    except Exception as e:
        logger.error(f"Unexpected error getting upcoming appointments: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@calendar_bp.route('/calendar/book', methods=['POST'])
def book_appointment():
    """Book an appointment directly via API"""
    try:
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Validate required fields
        patient_name = InputValidator.validate_patient_name(data.get('patient_name', ''))
        date_str = data.get('date', '')
        time_str = data.get('time', '')
        
        date_obj = InputValidator.validate_date_string(date_str)
        hour, minute = InputValidator.validate_time_string(time_str)
        
        # Optional fields
        appointment_type = InputValidator.validate_appointment_type(
            data.get('appointment_type', 'checkup')
        )
        phone = InputValidator.validate_phone_number(data.get('phone'))
        email = InputValidator.validate_email(data.get('email'))
        notes = data.get('notes', '').strip()[:500]  # Limit notes length
        
        # Create appointment request
        from app.models.appointment import AppointmentRequest
        appointment_request = AppointmentRequest(
            patient_name=patient_name,
            date=date_str,
            time=f"{hour:02d}:{minute:02d}",
            appointment_type=appointment_type,
            phone=phone,
            email=email,
            notes=notes if notes else None
        )
        
        # Book the appointment
        result = calendar_service.book_appointment(appointment_request)
        
        if result['success']:
            logger.info(f"Appointment booked successfully: {patient_name} on {date_str} at {time_str}")
            return jsonify({
                'success': True,
                'message': result['message'],
                'event_id': result['event_id'],
                'event_link': result.get('event_link'),
                'appointment_details': {
                    'patient_name': patient_name,
                    'date': date_str,
                    'time': time_str,
                    'type': appointment_type
                }
            })
        else:
            logger.warning(f"Appointment booking failed: {result['message']}")
            return jsonify({
                'success': False,
                'message': result['message']
            }), 409  # Conflict
            
    except ValidationError as e:
        logger.warning(f"Validation error in appointment booking: {e}")
        return jsonify({'error': str(e)}), 400
        
    except CalendarServiceError as e:
        logger.error(f"Calendar service error in booking: {e}")
        return jsonify({'error': 'Booking service temporarily unavailable'}), 503
        
    except Exception as e:
        logger.error(f"Unexpected error in appointment booking: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@calendar_bp.route('/calendar/business-hours', methods=['GET'])
def get_business_hours():
    """Get business hours and schedule information"""
    try:
        from app.config import Config
        
        return jsonify({
            'business_hours': {
                'start': Config.BUSINESS_HOURS_START,
                'end': Config.BUSINESS_HOURS_END,
                'start_formatted': f"{Config.BUSINESS_HOURS_START}:00",
                'end_formatted': f"{Config.BUSINESS_HOURS_END}:00"
            },
            'lunch_break': {
                'start': Config.LUNCH_BREAK_START,
                'end': Config.LUNCH_BREAK_END,
                'start_formatted': f"{Config.LUNCH_BREAK_START}:00",
                'end_formatted': f"{Config.LUNCH_BREAK_END}:00"
            },
            'appointment_settings': {
                'duration_minutes': Config.APPOINTMENT_DURATION_MINUTES,
                'buffer_time_minutes': Config.BUFFER_TIME_MINUTES
            },
            'business_info': {
                'name': Config.BUSINESS_NAME,
                'phone': Config.BUSINESS_PHONE,
                'email': Config.BUSINESS_EMAIL,
                'address': Config.BUSINESS_ADDRESS
            },
            'timezone': Config.TIMEZONE,
            'appointment_types': Config.APPOINTMENT_TYPES
        })
        
    except Exception as e:
        logger.error(f"Error getting business hours: {e}")
        return jsonify({'error': 'Internal server error'}), 500