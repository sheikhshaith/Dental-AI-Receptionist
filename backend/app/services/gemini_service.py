# app/services/gemini_service.py
"""
Google Gemini AI service for natural language processing
"""
import logging
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional
import google.generativeai as genai
from app.config import Config
from app.utils.exceptions import GeminiServiceError

logger = logging.getLogger(__name__)

class GeminiService:
    """Service for interacting with Google Gemini AI"""
    
    def __init__(self):
        """Initialize Gemini service"""
        try:
            if not Config.GOOGLE_GEMINI_API_KEY:
                raise GeminiServiceError("Gemini API key not configured")
                
            genai.configure(api_key=Config.GOOGLE_GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            # Generation configuration
            self.generation_config = {
                'temperature': 0.7,
                'top_p': 0.8,
                'top_k': 40,
                'max_output_tokens': 1024,
            }
            
            logger.info("Gemini service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini service: {e}")
            raise GeminiServiceError(f"Gemini initialization failed: {e}")
    
    def analyze_intent(self, user_message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze user message to extract intent and entities"""
        
        system_prompt = self._build_intent_analysis_prompt()
        
        try:
            # Build full prompt with context
            full_prompt = f"{system_prompt}\n\nUser message: \"{user_message}\""
            
            if context:
                full_prompt += f"\n\nConversation context: {json.dumps(context)}"
            
            # Generate response
            response = self.model.generate_content(
                full_prompt,
                generation_config=self.generation_config
            )
            
            # Parse JSON response
            return self._parse_intent_response(response.text, user_message)
            
        except Exception as e:
            logger.error(f"Error analyzing intent: {e}")
            return self._fallback_intent_analysis(user_message)
    
    def generate_response(self, user_message: str, context: Dict[str, Any]) -> str:
        """Generate natural response based on context"""
        
        try:
            system_prompt = self._build_response_generation_prompt()
            
            # Build context string
            context_str = self._format_context_for_prompt(context)
            
            full_prompt = f"""
{system_prompt}

Current context: {context_str}

User message: "{user_message}"

Generate a helpful, professional response as the dental office AI receptionist.
"""
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=self.generation_config
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._fallback_response(context.get('intent', 'general_inquiry'))
    
    def _build_intent_analysis_prompt(self) -> str:
        """Build system prompt for intent analysis"""
        return f"""
You are an AI assistant analyzing patient messages for a dental office receptionist system.

BUSINESS CONTEXT:
- Office: {Config.BUSINESS_NAME}
- Hours: {Config.BUSINESS_HOURS_START}:00 AM - {Config.BUSINESS_HOURS_END}:00 PM
- Phone: {Config.BUSINESS_PHONE}
- Available appointment types: {', '.join(Config.APPOINTMENT_TYPES.keys())}

TASK:
Analyze the user's message and extract:
1. Primary intent
2. Entities (dates, times, names, appointment types)
3. Confidence level
4. Sentiment

INTENTS:
- booking: User wants to schedule an appointment
- availability_check: User asking about available times
- reschedule: User wants to change existing appointment
- cancel: User wants to cancel appointment
- emergency: Urgent dental emergency
- general_inquiry: Questions about services, hours, location, etc.
- confirmation: User confirming a suggested time/action

RESPONSE FORMAT (JSON only):
{{
    "intent": "intent_name",
    "entities": {{
        "date": "YYYY-MM-DD or null",
        "time": "HH:MM or null",
        "patient_name": "string or null",
        "appointment_type": "string or null",
        "phone": "string or null"
    }},
    "confidence": "high|medium|low",
    "sentiment": "positive|neutral|negative|urgent",
    "extracted_text": "summary of what user wants"
}}

Current date/time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    def _build_response_generation_prompt(self) -> str:
        """Build system prompt for response generation"""
        return f"""
You are a friendly, professional AI receptionist for {Config.BUSINESS_NAME}.

PERSONALITY:
- Warm and welcoming
- Professional but conversational
- Helpful and solution-oriented
- Empathetic to patient needs

KNOWLEDGE:
- Office hours: {Config.BUSINESS_HOURS_START}:00 AM - {Config.BUSINESS_HOURS_END}:00 PM
- Phone: {Config.BUSINESS_PHONE}
- Services: General dentistry, cleanings, consultations, emergencies
- Appointment types: {', '.join(Config.APPOINTMENT_TYPES.values())}

GUIDELINES:
- Keep responses concise but complete
- Always offer next steps
- For emergencies, prioritize immediate care advice
- Ask for clarification when needed
- Confirm booking details before finalizing
- Be understanding of patient anxiety or concerns

TONE:
Professional yet friendly. Use natural language, avoid being robotic.
"""
    
    def _parse_intent_response(self, response_text: str, original_message: str) -> Dict[str, Any]:
        """Parse JSON response from Gemini"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # Validate and clean the response
                return self._validate_intent_result(result)
            else:
                logger.warning("No JSON found in Gemini response")
                return self._fallback_intent_analysis(original_message)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return self._fallback_intent_analysis(original_message)
    
    def _validate_intent_result(self, result: Dict) -> Dict[str, Any]:
        """Validate and clean intent analysis result"""
        # Ensure required fields exist
        validated = {
            'intent': result.get('intent', 'general_inquiry'),
            'entities': result.get('entities', {}),
            'confidence': result.get('confidence', 'medium'),
            'sentiment': result.get('sentiment', 'neutral'),
            'extracted_text': result.get('extracted_text', '')
        }
        
        # Validate intent
        valid_intents = ['booking', 'availability_check', 'reschedule', 'cancel', 'emergency', 'general_inquiry', 'confirmation']
        if validated['intent'] not in valid_intents:
            validated['intent'] = 'general_inquiry'
        
        # Validate confidence
        if validated['confidence'] not in ['high', 'medium', 'low']:
            validated['confidence'] = 'medium'
        
        # Validate sentiment
        if validated['sentiment'] not in ['positive', 'neutral', 'negative', 'urgent']:
            validated['sentiment'] = 'neutral'
        
        return validated
    
    def _fallback_intent_analysis(self, user_message: str) -> Dict[str, Any]:
        """Fallback intent analysis using simple keyword matching"""
        message_lower = user_message.lower()
        
        # Intent detection based on keywords
        if any(word in message_lower for word in ['emergency', 'urgent', 'pain', 'hurt', 'broken']):
            intent = 'emergency'
            sentiment = 'urgent'
        elif any(word in message_lower for word in ['book', 'schedule', 'appointment', 'need']):
            intent = 'booking'
            sentiment = 'neutral'
        elif any(word in message_lower for word in ['available', 'open', 'free', 'when']):
            intent = 'availability_check'
            sentiment = 'neutral'
        elif any(word in message_lower for word in ['cancel', 'reschedule', 'change', 'move']):
            intent = 'reschedule'
            sentiment = 'neutral'
        elif any(word in message_lower for word in ['yes', 'confirm', 'book it', 'that works']):
            intent = 'confirmation'
            sentiment = 'positive'
        else:
            intent = 'general_inquiry'
            sentiment = 'neutral'
        
        return {
            'intent': intent,
            'entities': {
                'date': None,
                'time': None,
                'patient_name': None,
                'appointment_type': None,
                'phone': None
            },
            'confidence': 'low',
            'sentiment': sentiment,
            'extracted_text': user_message
        }
    
    def _format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """Format context information for prompt"""
        context_parts = []
        
        if context.get('intent'):
            context_parts.append(f"Intent: {context['intent']}")
        
        if context.get('stage'):
            context_parts.append(f"Conversation stage: {context['stage']}")
        
        if context.get('booking_data'):
            booking_data = context['booking_data']
            if booking_data:
                context_parts.append(f"Booking progress: {booking_data}")
        
        if context.get('available_slots'):
            slots = context['available_slots']
            if slots:
                slot_times = [f"{slot['start']}-{slot['end']}" for slot in slots[:3]]
                context_parts.append(f"Available slots: {', '.join(slot_times)}")
        
        return ' | '.join(context_parts) if context_parts else 'Initial conversation'
    
    def _fallback_response(self, intent: str) -> str:
        """Generate fallback response when Gemini fails"""
        fallback_responses = {
            'booking': "I'd be happy to help you schedule an appointment! Could you please tell me your preferred date and time?",
            'availability_check': "I can check our availability for you. What date are you looking for?",
            'emergency': f"If this is a dental emergency, please call our office immediately at {Config.BUSINESS_PHONE} or visit the nearest emergency room if it's after hours.",
            'general_inquiry': f"Thank you for contacting {Config.BUSINESS_NAME}! How can I help you today?",
            'reschedule': f"I understand you'd like to reschedule. Please call our office at {Config.BUSINESS_PHONE} and our staff will be happy to help you.",
            'cancel': f"To cancel an appointment, please call our office at {Config.BUSINESS_PHONE}. We appreciate 24-hour notice when possible."
        }
        
        return fallback_responses.get(intent, 
            f"I'm here to help! You can ask me about appointments, our services, or office information. "
            f"For immediate assistance, call us at {Config.BUSINESS_PHONE}."
        )