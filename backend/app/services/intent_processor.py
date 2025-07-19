# app/services/intent_processor.py
"""
Intent processor for dental office receptionist system
Handles intent analysis and response generation using Gemini AI and Calendar integration
"""
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.services.gemini_service import GeminiService
from app.services.calendar_service import CalendarService
from app.models.appointment import AppointmentRequest
from app.utils.exceptions import GeminiServiceError, CalendarServiceError
from app.config import Config

logger = logging.getLogger(__name__)

class IntentProcessor:
    """Process user intents and manage conversation flow with calendar integration"""
    
    def __init__(self):
        """Initialize intent processor with services"""
        try:
            self.gemini_service = GeminiService()
            self.calendar_service = CalendarService()
            logger.info("Intent processor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize intent processor: {e}")
            raise GeminiServiceError(f"Intent processor initialization failed: {e}")
    
    def process_message(self, user_message: str, session_id: str, session_state: Any) -> Dict[str, Any]:
        """
        Main method to process user message and generate response
        
        Args:
            user_message: User's input message
            session_id: Session identifier
            session_state: Current session state object
            
        Returns:
            Dict containing response and updated data
        """
        try:
            # Build context from session state
            context = self._build_context_from_session(session_state)
            
            # Analyze user intent using Gemini
            intent_analysis = self.gemini_service.analyze_intent(user_message, context)
            
            # Update session state with extracted entities
            self._update_session_state(session_state, intent_analysis)
            
            # Process based on intent
            response_data = self._process_intent(
                intent_analysis, session_state, user_message
            )
            
            logger.info(f"Processed message with intent: {intent_analysis['intent']}")
            return response_data
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return self._get_error_response(str(e))
    
    def _build_context_from_session(self, session_state: Any) -> Dict[str, Any]:
        """Build context dictionary from session state"""
        return {
            'stage': getattr(session_state, 'stage', 'initial'),
            'booking_data': getattr(session_state, 'booking_data', {}),
            'last_intent': getattr(session_state, 'last_intent', None)
        }
    
    def _update_session_state(self, session_state: Any, intent_analysis: Dict[str, Any]):
        """Update session state with new intent analysis"""
        # Update last intent
        session_state.last_intent = intent_analysis['intent']
        
        # Extract and update booking data
        entities = intent_analysis.get('entities', {})
        booking_updates = {}
        
        if entities.get('patient_name'):
            booking_updates['patient_name'] = entities['patient_name']
        if entities.get('date'):
            booking_updates['date'] = entities['date']
        if entities.get('time'):
            booking_updates['time'] = entities['time']
        if entities.get('appointment_type'):
            booking_updates['appointment_type'] = entities['appointment_type']
        if entities.get('phone'):
            booking_updates['phone'] = entities['phone']
        if entities.get('email'):
            booking_updates['email'] = entities['email']
        
        if booking_updates:
            session_state.update_booking_data(**booking_updates)
        
        # Update conversation stage
        session_state.stage = self._determine_next_stage(session_state, intent_analysis)
    
    def _determine_next_stage(self, session_state: Any, intent_analysis: Dict[str, Any]) -> str:
        """Determine next conversation stage"""
        current_stage = getattr(session_state, 'stage', 'initial')
        intent = intent_analysis['intent']
        booking_data = getattr(session_state, 'booking_data', {})
        
        if intent == 'emergency':
            return 'emergency_response'
        
        elif intent == 'booking':
            if not booking_data.get('patient_name'):
                return 'collecting_name'
            elif not booking_data.get('date'):
                return 'collecting_date'
            elif not booking_data.get('time'):
                return 'showing_slots'
            else:
                return 'confirming_appointment'
        
        elif intent == 'availability_check':
            return 'showing_slots'
        
        elif intent == 'confirmation':
            if current_stage == 'confirming_appointment':
                return 'booking_complete'
            elif current_stage == 'showing_slots':
                return 'confirming_appointment'
            else:
                return current_stage
        
        elif intent in ['reschedule', 'cancel']:
            return 'handling_changes'
        
        return 'general_inquiry'
    
    def _process_intent(self, intent_analysis: Dict[str, Any], session_state: Any, 
                       user_message: str) -> Dict[str, Any]:
        """Process specific intent and generate appropriate response"""
        intent = intent_analysis['intent']
        
        if intent == 'booking':
            return self._handle_booking_intent(session_state, user_message, intent_analysis)
        
        elif intent == 'availability_check':
            return self._handle_availability_check(session_state, user_message, intent_analysis)
        
        elif intent == 'confirmation':
            return self._handle_confirmation_intent(session_state, user_message, intent_analysis)
        
        elif intent == 'emergency':
            return self._handle_emergency_intent(user_message, intent_analysis)
        
        elif intent in ['reschedule', 'cancel']:
            return self._handle_modification_intent(intent, user_message, intent_analysis)
        
        else:  # general_inquiry
            return self._handle_general_inquiry(user_message, intent_analysis)
    
    def _handle_booking_intent(self, session_state: Any, user_message: str, 
                              intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle booking appointment intent"""
        booking_data = getattr(session_state, 'booking_data', {})
        stage = getattr(session_state, 'stage', 'initial')
        
        # Check what information we still need
        missing_info = []
        if not booking_data.get('patient_name'):
            missing_info.append('name')
        if not booking_data.get('date'):
            missing_info.append('date')
        if not booking_data.get('time'):
            missing_info.append('time')
        
        if missing_info:
            # Generate response asking for missing information
            context = self._build_context_from_session(session_state)
            context.update({
                'intent': intent_analysis['intent'],
                'missing_info': missing_info,
                'stage': stage
            })
            
            response = self.gemini_service.generate_response(user_message, context)
            
            return {
                'response': response,
                'type': 'text',
                'intent': intent_analysis['intent'],
                'confidence': intent_analysis['confidence'],
                'data': {'missing_info': missing_info, 'booking_progress': booking_data}
            }
        
        # If we have date, show available slots
        if booking_data.get('date') and not booking_data.get('time'):
            return self._show_available_slots(booking_data['date'], user_message, intent_analysis)
        
        # If we have all info, proceed to confirmation
        if booking_data.get('patient_name') and booking_data.get('date') and booking_data.get('time'):
            context = self._build_context_from_session(session_state)
            context.update({
                'intent': intent_analysis['intent'],
                'ready_to_book': True
            })
            
            response = self.gemini_service.generate_response(user_message, context)
            
            return {
                'response': response,
                'type': 'confirmation',
                'intent': intent_analysis['intent'],
                'confidence': intent_analysis['confidence'],
                'data': {'booking_data': booking_data}
            }
        
        # Default response
        context = self._build_context_from_session(session_state)
        response = self.gemini_service.generate_response(user_message, context)
        
        return {
            'response': response,
            'type': 'text',
            'intent': intent_analysis['intent'],
            'confidence': intent_analysis['confidence']
        }
    
    def _handle_availability_check(self, session_state: Any, user_message: str, 
                                  intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle availability check intent"""
        from datetime import datetime, timedelta
        
        booking_data = getattr(session_state, 'booking_data', {})
        target_date = booking_data.get('date')
        
        # Try to extract date from user message if not in booking data
        if not target_date:
            # Look for common date patterns in the message
            date_patterns = [
                (r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s,]+(\d{1,2})\b', 1),  # Jul 21
                (r'\b(\d{1,2})[\s,]+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b', 0),  # 21 Jul
                (r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b', 0),  # MM/DD/YYYY or DD/MM/YYYY
                (r'\b(\d{1,2})\b', 0)  # Just a day number
            ]
            
            # Try to parse date from message
            for pattern, group in date_patterns:
                match = re.search(pattern, user_message.lower())
                if match:
                    try:
                        # If it's just a day number, assume current month and year
                        if pattern == r'\b(\d{1,2})\b':
                            day = int(match.group(1))
                            today = datetime.now()
                            # If the day is in the past, assume next month
                            if day < today.day:
                                month = today.month + 1 if today.month < 12 else 1
                                year = today.year if today.month < 12 else today.year + 1
                            else:
                                month, year = today.month, today.year
                            
                            target_date = datetime(year, month, day).strftime('%Y-%m-%d')
                            break
                            
                        # For other patterns, try to parse with dateutil
                        from dateutil import parser
                        parsed_date = parser.parse(match.group(0), fuzzy=True)
                        target_date = parsed_date.strftime('%Y-%m-%d')
                        break
                    except (ValueError, IndexError):
                        continue
        
        # If still no date, ask for it
        if not target_date:
            context = self._build_context_from_session(session_state)
            context.update({'intent': intent_analysis['intent'], 'need_date': True})
            
            response = self.gemini_service.generate_response(user_message, context)
            
            return {
                'response': response,
                'type': 'text',
                'intent': intent_analysis['intent'],
                'confidence': intent_analysis['confidence']
            }
        
        # Check availability for the requested date
        result = self._show_available_slots(target_date, user_message, intent_analysis)
        
        # If no slots available, suggest next available dates
        if not result.get('available_slots'):
            # Find next 3 available dates
            next_dates = []
            current_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            
            for i in range(1, 8):  # Check next 7 days
                check_date = current_date + timedelta(days=i)
                slots = self.calendar_service.get_available_slots(check_date)
                if slots:
                    next_dates.append({
                        'date': check_date.strftime('%Y-%m-%d'),
                        'formatted_date': check_date.strftime('%A, %b %d'),
                        'slots': [s.strftime('%I:%M %p') for s in slots[:3]]  # First 3 slots
                    })
                    if len(next_dates) >= 3:  # Show max 3 alternative dates
                        break
            
            if next_dates:
                # Format the response to show next available dates
                response = (
                    f"I'm sorry, but there are no available appointments on {datetime.strptime(target_date, '%Y-%m-%d').strftime('%B %d, %Y')}.\n\n"
                    f"Here are the next available dates:\n"
                )
                
                for i, date_info in enumerate(next_dates, 1):
                    response += f"{i}. {date_info['formatted_date']}\n"
                
                response += "\nPlease select a date or let me know if you'd like to try another date."
                
                return {
                    'response': response,
                    'type': 'text',
                    'intent': intent_analysis['intent'],
                    'confidence': intent_analysis['confidence'],
                    'next_available_dates': next_dates
                }
        
        return result
    
    def _show_available_slots(self, date_str: str, user_message: str, 
                             intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Show available appointment slots for a date"""
        try:
            # Parse date
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Get available slots from calendar
            available_slots = self.calendar_service.get_available_slots(target_date)
            
            if not available_slots:
                response = f"I'm sorry, but there are no available appointments on {date_str}. Would you like to check a different date?"
                return {
                    'response': response,
                    'type': 'text',
                    'intent': intent_analysis['intent'],
                    'confidence': intent_analysis['confidence'],
                    'available_slots': []
                }
            
            # Format slots for response
            slots_data = [slot.to_dict() for slot in available_slots]
            
            # Generate contextual response
            context = {
                'intent': intent_analysis['intent'],
                'date': date_str,
                'available_slots': slots_data[:5],  # Show first 5 slots
                'total_slots': len(slots_data)
            }
            
            response = self.gemini_service.generate_response(user_message, context)
            
            return {
                'response': response,
                'type': 'slots',
                'intent': intent_analysis['intent'],
                'confidence': intent_analysis['confidence'],
                'available_slots': slots_data,
                'data': {'date': date_str, 'slot_count': len(slots_data)}
            }
            
        except CalendarServiceError as e:
            logger.error(f"Calendar error getting slots: {e}")
            return {
                'response': "I'm having trouble accessing the calendar right now. Please try again in a moment.",
                'type': 'error',
                'intent': intent_analysis['intent'],
                'confidence': intent_analysis['confidence']
            }
        except Exception as e:
            logger.error(f"Error showing available slots: {e}")
            return {
                'response': "I encountered an error while checking availability. Please try again.",
                'type': 'error',
                'intent': intent_analysis['intent'],
                'confidence': intent_analysis['confidence']
            }
    
    def _handle_confirmation_intent(self, session_state: Any, user_message: str, 
                                   intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle confirmation intent"""
        stage = getattr(session_state, 'stage', 'initial')
        booking_data = getattr(session_state, 'booking_data', {})
        
        if stage == 'confirming_appointment' and session_state.is_booking_complete():
            # Proceed with actual booking
            return self._execute_booking(session_state, user_message, intent_analysis)
        
        # Generate appropriate confirmation response
        context = self._build_context_from_session(session_state)
        context.update({'intent': intent_analysis['intent']})
        
        response = self.gemini_service.generate_response(user_message, context)
        
        return {
            'response': response,
            'type': 'text',
            'intent': intent_analysis['intent'],
            'confidence': intent_analysis['confidence'],
            'data': {'booking_data': booking_data}
        }
    
    def _execute_booking(self, session_state: Any, user_message: str, 
                        intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual appointment booking"""
        try:
            booking_data = getattr(session_state, 'booking_data', {})
            
            # Create appointment request
            appointment_request = AppointmentRequest(
                patient_name=booking_data['patient_name'],
                date=booking_data['date'],
                time=booking_data['time'],
                appointment_type=booking_data.get('appointment_type', 'checkup'),
                phone=booking_data.get('phone'),
                email=booking_data.get('email'),
                notes=booking_data.get('notes')
            )
            
            # Book appointment via calendar service
            booking_result = self.calendar_service.book_appointment(appointment_request)
            
            if booking_result['success']:
                # Clear booking data after successful booking
                session_state.clear_booking_data()
                session_state.stage = 'booking_complete'
                
                response = f"Great! Your appointment has been successfully booked for {booking_data['date']} at {booking_data['time']}. You'll receive a confirmation email if you provided one. Is there anything else I can help you with?"
                
                return {
                    'response': response,
                    'type': 'booking_success',
                    'intent': intent_analysis['intent'],
                    'confidence': intent_analysis['confidence'],
                    'data': {
                        'booking_details': booking_data,
                        'event_id': booking_result.get('event_id'),
                        'event_link': booking_result.get('event_link')
                    }
                }
            else:
                response = f"I apologize, but there was an issue booking your appointment: {booking_result['message']}. Would you like to try a different time?"
                
                return {
                    'response': response,
                    'type': 'booking_error',
                    'intent': intent_analysis['intent'],
                    'confidence': intent_analysis['confidence'],
                    'data': {'error_message': booking_result['message']}
                }
                
        except Exception as e:
            logger.error(f"Error executing booking: {e}")
            return {
                'response': "I encountered an error while booking your appointment. Please try again or call our office directly.",
                'type': 'error',
                'intent': intent_analysis['intent'],
                'confidence': intent_analysis['confidence']
            }
    
    def confirm_appointment_booking(self, session_id: str, session_state: Any, 
                                   selected_time: str) -> Dict[str, Any]:
        """Confirm appointment booking with selected time"""
        try:
            booking_data = getattr(session_state, 'booking_data', {})
            
            # Update booking data with selected time
            session_state.update_booking_data(time=selected_time)
            booking_data = getattr(session_state, 'booking_data', {})
            
            # Create appointment request
            appointment_request = AppointmentRequest(
                patient_name=booking_data['patient_name'],
                date=booking_data['date'],
                time=selected_time,
                appointment_type=booking_data.get('appointment_type', 'checkup'),
                phone=booking_data.get('phone'),
                email=booking_data.get('email'),
                notes=booking_data.get('notes')
            )
            
            # Book appointment
            booking_result = self.calendar_service.book_appointment(appointment_request)
            
            return booking_result
            
        except Exception as e:
            logger.error(f"Error confirming booking: {e}")
            return {
                'success': False,
                'message': 'Failed to confirm booking due to technical error'
            }
    
    def _handle_emergency_intent(self, user_message: str, 
                                intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emergency intent"""
        emergency_response = f"""This sounds like a dental emergency. Here's what you should do:

🚨 **Immediate Steps:**
1. If you're experiencing severe pain or trauma, please call our office immediately at {Config.BUSINESS_PHONE}
2. If it's after hours and this is a serious emergency, please visit the nearest emergency room

🦷 **For Dental Pain:**
- Rinse with warm salt water
- Take over-the-counter pain medication as directed
- Apply a cold compress to the outside of your cheek

📞 **Our Emergency Line:** {Config.BUSINESS_PHONE}

Would you also like me to help you schedule a follow-up appointment?"""
        
        return {
            'response': emergency_response,
            'type': 'emergency',
            'intent': intent_analysis['intent'],
            'confidence': intent_analysis['confidence'],
            'data': {
                'emergency_phone': Config.BUSINESS_PHONE,
                'business_name': Config.BUSINESS_NAME
            }
        }
    
    def _handle_modification_intent(self, intent: str, user_message: str, 
                                   intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle reschedule/cancel intents"""
        if intent == 'reschedule':
            response = f"""I'd be happy to help you reschedule your appointment. 

To reschedule, I'll need:
1. Your current appointment details (date and time)
2. Your preferred new date and time

Alternatively, you can call our office directly at {Config.BUSINESS_PHONE} and our staff will be happy to assist you.

What's your current appointment date and time?"""
        
        else:  # cancel
            response = f"""I understand you'd like to cancel your appointment.

For appointment cancellations, please call our office at {Config.BUSINESS_PHONE}. We appreciate 24-hour notice when possible.

Our office hours are {Config.BUSINESS_HOURS_START}:00 AM - {Config.BUSINESS_HOURS_END}:00 PM.

Is there anything else I can help you with today?"""
        
        return {
            'response': response,
            'type': 'modification',
            'intent': intent_analysis['intent'],
            'confidence': intent_analysis['confidence'],
            'data': {
                'modification_type': intent,
                'office_phone': Config.BUSINESS_PHONE
            }
        }
    
    def _handle_general_inquiry(self, user_message: str, 
                               intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general inquiry intent"""
        context = {
            'intent': intent_analysis['intent'],
            'business_info': {
                'name': Config.BUSINESS_NAME,
                'phone': Config.BUSINESS_PHONE,
                'email': Config.BUSINESS_EMAIL,
                'address': Config.BUSINESS_ADDRESS,
                'hours': f"{Config.BUSINESS_HOURS_START}:00 AM - {Config.BUSINESS_HOURS_END}:00 PM"
            },
            'services': list(Config.APPOINTMENT_TYPES.values())
        }
        
        response = self.gemini_service.generate_response(user_message, context)
        
        return {
            'response': response,
            'type': 'inquiry',
            'intent': intent_analysis['intent'],
            'confidence': intent_analysis['confidence'],
            'data': context
        }
    
    def _get_error_response(self, error_message: str) -> Dict[str, Any]:
        """Generate error response"""
        return {
            'response': f"I apologize, but I'm experiencing technical difficulties. Please try again or call our office at {Config.BUSINESS_PHONE} for immediate assistance.",
            'type': 'error',
            'intent': 'error',
            'confidence': 'low',
            'data': {'error': error_message}
        }
    
    def get_upcoming_appointments(self, days_ahead: int = 7) -> List[Dict]:
        """Get upcoming appointments from calendar"""
        try:
            return self.calendar_service.get_upcoming_appointments(days_ahead)
        except Exception as e:
            logger.error(f"Error getting upcoming appointments: {e}")
            return []
    
    def cancel_appointment_by_id(self, event_id: str) -> Dict[str, Any]:
        """Cancel appointment by calendar event ID"""
        try:
            return self.calendar_service.cancel_appointment(event_id)
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            return {
                'success': False,
                'message': 'Failed to cancel appointment'
            }
    
    def reschedule_appointment_by_id(self, event_id: str, new_date: str, 
                                    new_time: str) -> Dict[str, Any]:
        """Reschedule appointment by calendar event ID"""
        try:
            return self.calendar_service.reschedule_appointment(event_id, new_date, new_time)
        except Exception as e:
            logger.error(f"Error rescheduling appointment: {e}")
            return {
                'success': False,
                'message': 'Failed to reschedule appointment'
            }