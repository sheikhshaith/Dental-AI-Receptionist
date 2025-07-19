# app/routes/chat.py
"""
Chat and conversation endpoints
"""
import logging
from flask import Blueprint, request, jsonify
from app.services.intent_processor import IntentProcessor
from app.models.conversation import SessionManager, Message
from app.utils.validators import InputValidator
from app.utils.exceptions import ValidationError, DentalReceptionistError
from datetime import datetime

logger = logging.getLogger(__name__)
chat_bp = Blueprint('chat', __name__)

# Global instances
intent_processor = IntentProcessor()
session_manager = SessionManager()

@chat_bp.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages from users"""
    try:
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Validate inputs
        user_message = InputValidator.validate_message_content(
            data.get('message', '')
        )
        session_id = InputValidator.validate_session_id(
            data.get('session_id', 'default')
        )
        
        # Clean up expired sessions periodically
        session_manager.cleanup_expired_sessions()
        
        # Get session
        session = session_manager.get_session(session_id)
        
        # Add user message to session
        user_msg = Message(content=user_message, sender='user')
        session_manager.add_message(session_id, user_msg)
        
        # Process message
        response_data = intent_processor.process_message(
            user_message, 
            session_id,
            session['state']
        )
        
        # Add assistant response to session
        assistant_msg = Message(
            content=response_data['response'],
            sender='assistant',
            message_type=response_data.get('type', 'text'),
            metadata={
                'intent': response_data.get('intent'),
                'confidence': response_data.get('confidence')
            }
        )
        session_manager.add_message(session_id, assistant_msg)
        
        logger.info(f"Chat processed for session {session_id}: {response_data.get('type', 'unknown')}")
        
        return jsonify({
            'response': response_data['response'],
            'type': response_data['type'],
            'data': response_data.get('data', {}),
            'available_slots': response_data.get('available_slots', []),
            'session_id': session_id
        })
        
    except ValidationError as e:
        logger.warning(f"Validation error in chat: {e}")
        return jsonify({'error': str(e)}), 400
        
    except DentalReceptionistError as e:
        logger.error(f"Service error in chat: {e}")
        return jsonify({'error': 'Service temporarily unavailable'}), 503
        
    except Exception as e:
        logger.error(f"Unexpected error in chat: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@chat_bp.route('/chat/confirm-booking', methods=['POST'])
def confirm_booking():
    """Confirm and finalize appointment booking"""
    try:
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Validate inputs
        session_id = InputValidator.validate_session_id(
            data.get('session_id', '')
        )
        selected_time = data.get('selected_time', '')
        
        if not selected_time:
            return jsonify({'error': 'Selected time is required'}), 400
        
        # Get session
        session = session_manager.get_session(session_id)
        booking_data = session['state'].booking_data
        
        # Validate booking data
        if not booking_data.get('patient_name') or not booking_data.get('date'):
            return jsonify({'error': 'Incomplete booking information'}), 400
        
        # Validate selected time
        InputValidator.validate_time_string(selected_time)
        
        # Process booking confirmation
        result = intent_processor.confirm_appointment_booking(
            session_id,
            session['state'],
            selected_time
        )
        
        if result['success']:
            # Clear booking data after successful booking
            session['state'].clear_booking_data()
            
            logger.info(f"Appointment booked successfully for session {session_id}")
            
            return jsonify({
                'success': True,
                'message': result['message'],
                'booking_details': result.get('booking_details', {}),
                'event_id': result.get('event_id')
            })
        else:
            logger.warning(f"Booking failed for session {session_id}: {result.get('message')}")
            return jsonify({
                'success': False,
                'message': result['message']
            })
            
    except ValidationError as e:
        logger.warning(f"Validation error in booking confirmation: {e}")
        return jsonify({'error': str(e)}), 400
        
    except DentalReceptionistError as e:
        logger.error(f"Service error in booking confirmation: {e}")
        return jsonify({'error': 'Booking service temporarily unavailable'}), 503
        
    except Exception as e:
        logger.error(f"Unexpected error in booking confirmation: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@chat_bp.route('/chat/session/<session_id>', methods=['GET'])
def get_session_info(session_id):
    """Get session information and conversation history"""
    try:
        session_id = InputValidator.validate_session_id(session_id)
        session = session_manager.get_session(session_id)
        
        return jsonify({
            'session_id': session_id,
            'created_at': session['created_at'].isoformat(),
            'last_activity': session['last_activity'].isoformat(),
            'message_count': len(session['messages']),
            'current_stage': session['state'].stage,
            'booking_progress': {
                'has_name': bool(session['state'].booking_data.get('patient_name')),
                'has_date': bool(session['state'].booking_data.get('date')),
                'has_time': bool(session['state'].booking_data.get('time')),
                'is_complete': session['state'].is_booking_complete()
            }
        })
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@chat_bp.route('/chat/sessions/stats', methods=['GET'])
def get_session_stats():
    """Get system-wide session statistics"""
    try:
        session_manager.cleanup_expired_sessions()
        
        return jsonify({
            'active_sessions': session_manager.get_session_count(),
            'max_sessions': session_manager.sessions.__class__.__dict__.get('MAX_SESSIONS', 1000),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting session stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500