# app/utils/exceptions.py
"""
Custom exceptions for the application
"""

class DentalReceptionistError(Exception):
    """Base exception for the application"""
    pass

class ConfigurationError(DentalReceptionistError):
    """Raised when configuration is invalid"""
    pass

class CalendarServiceError(DentalReceptionistError):
    """Raised when calendar operations fail"""
    pass

class GeminiServiceError(DentalReceptionistError):
    """Raised when Gemini API operations fail"""
    pass

class SessionError(DentalReceptionistError):
    """Raised when session operations fail"""
    pass

class ValidationError(DentalReceptionistError):
    """Raised when input validation fails"""
    pass