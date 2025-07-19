# app/utils/validators.py
"""
Input validation utilities
"""
import re
from datetime import datetime, date
from typing import Optional, Tuple, Dict
from app.utils.exceptions import ValidationError

class InputValidator:
    """Validates user inputs and API parameters"""
    
    @staticmethod
    def validate_session_id(session_id: str) -> str:
        """Validate session ID format"""
        if not session_id or not isinstance(session_id, str):
            raise ValidationError("Session ID is required and must be a string")
        
        if len(session_id) > 100:
            raise ValidationError("Session ID is too long")
        
        # Allow alphanumeric and common special characters
        if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
            raise ValidationError("Session ID contains invalid characters")
        
        return session_id.strip()
    
    @staticmethod
    def validate_message_content(content: str) -> str:
        """Validate chat message content"""
        if not content or not isinstance(content, str):
            raise ValidationError("Message content is required")
        
        content = content.strip()
        
        if len(content) == 0:
            raise ValidationError("Message cannot be empty")
        
        if len(content) > 1000:
            raise ValidationError("Message is too long (max 1000 characters)")
        
        return content
    
    @staticmethod
    def validate_date_string(date_str: str) -> date:
        """Validate and parse date string"""
        if not date_str:
            raise ValidationError("Date is required")
        
        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError("Invalid date format. Use YYYY-MM-DD")
        
        # Check if date is not in the past
        if parsed_date < date.today():
            raise ValidationError("Cannot book appointments in the past")
        
        # Check if date is not too far in the future (e.g., 1 year)
        max_future_date = date.today().replace(year=date.today().year + 1)
        if parsed_date > max_future_date:
            raise ValidationError("Cannot book appointments more than 1 year in advance")
        
        return parsed_date
    
    @staticmethod
    def validate_time_string(time_str: str) -> Tuple[int, int]:
        """Validate and parse time string"""
        if not time_str:
            raise ValidationError("Time is required")
        
        # Support both 24-hour and 12-hour formats
        time_patterns = [
            r'^(\d{1,2}):(\d{2})$',  # 24-hour format
            r'^(\d{1,2}):(\d{2})\s*(AM|PM)$',  # 12-hour format
        ]
        
        for pattern in time_patterns:
            match = re.match(pattern, time_str.strip().upper())
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))
                
                if len(match.groups()) == 3:  # 12-hour format
                    meridiem = match.group(3)
                    if meridiem == 'PM' and hour != 12:
                        hour += 12
                    elif meridiem == 'AM' and hour == 12:
                        hour = 0
                
                if not (0 <= hour <= 23):
                    raise ValidationError("Invalid hour (must be 0-23)")
                
                if not (0 <= minute <= 59):
                    raise ValidationError("Invalid minute (must be 0-59)")
                
                return hour, minute
        
        raise ValidationError("Invalid time format. Use HH:MM or HH:MM AM/PM")
    
    @staticmethod
    def validate_patient_name(name: str) -> str:
        """Validate patient name"""
        if not name or not isinstance(name, str):
            raise ValidationError("Patient name is required")
        
        name = name.strip()
        
        if len(name) < 2:
            raise ValidationError("Patient name is too short")
        
        if len(name) > 100:
            raise ValidationError("Patient name is too long")
        
        # Allow letters, spaces, hyphens, and apostrophes
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", name):
            raise ValidationError("Patient name contains invalid characters")
        
        return name
    
    @staticmethod
    def validate_phone_number(phone: Optional[str]) -> Optional[str]:
        """Validate phone number"""
        if not phone:
            return None
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        
        # Check length (US phone numbers)
        if len(digits_only) == 10:
            return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
        elif len(digits_only) == 11 and digits_only[0] == '1':
            return f"({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}"
        else:
            raise ValidationError("Invalid phone number format")
    
    @staticmethod
    def validate_email(email: Optional[str]) -> Optional[str]:
        """Validate email address"""
        if not email:
            return None
        
        email = email.strip().lower()
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format")
        
        return email
    
    @staticmethod
    def validate_appointment_type(appointment_type: str) -> str:
        """Validate appointment type"""
        from app.config import Config
        
        if not appointment_type:
            return 'checkup'  # Default
        
        appointment_type = appointment_type.lower().strip()
        
        # Check if it's a valid appointment type
        valid_types = list(Config.APPOINTMENT_TYPES.keys())
        
        if appointment_type in valid_types:
            return appointment_type
        
        # Try to find a close match
        for valid_type in valid_types:
            if appointment_type in valid_type or valid_type in appointment_type:
                return valid_type
        
        # Return default if no match found
        return 'checkup'