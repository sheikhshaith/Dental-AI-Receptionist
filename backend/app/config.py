
# config.py

""" Configuration settings for the Dental Office AI Receptionist """
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    
    # Google APIs - FIXED: Use environment variable name, not the key value
    GOOGLE_GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_GEMINI_API_KEY')
    GOOGLE_CALENDAR_CREDENTIALS_PATH = os.environ.get('GOOGLE_CALENDAR_CREDENTIALS_PATH', 'credentials/credentials.json')
    GOOGLE_CALENDAR_TOKEN_PATH = os.environ.get('GOOGLE_CALENDAR_TOKEN_PATH', 'credentials/token.json')
    CALENDAR_ID = os.environ.get('CALENDAR_ID', 'primary')
    
    # Business Information
    BUSINESS_NAME = os.environ.get('BUSINESS_NAME', 'Bright Smile Dental Office')
    BUSINESS_PHONE = os.environ.get('BUSINESS_PHONE', '(555) 123-4567')
    BUSINESS_EMAIL = os.environ.get('BUSINESS_EMAIL', 'contact@brightsmile.com')
    BUSINESS_ADDRESS = os.environ.get('BUSINESS_ADDRESS', '123 Main St, City, State 12345')
    
    # Schedule Configuration - FIXED: Proper business hours and timezone
    BUSINESS_HOURS_START = int(os.environ.get('BUSINESS_HOURS_START', 9))      # 9 AM
    BUSINESS_HOURS_END = int(os.environ.get('BUSINESS_HOURS_END', 19))         # 7 PM (19:00)
    LUNCH_BREAK_START = int(os.environ.get('LUNCH_BREAK_START', 12))           # 12 PM
    LUNCH_BREAK_END = int(os.environ.get('LUNCH_BREAK_END', 13))               # 1 PM
    APPOINTMENT_DURATION_MINUTES = int(os.environ.get('APPOINTMENT_DURATION_MINUTES', 60))
    BUFFER_TIME_MINUTES = int(os.environ.get('BUFFER_TIME_MINUTES', 15))
    TIMEZONE = os.environ.get('TIMEZONE', 'Asia/Karachi')  # FIXED: Correct timezone for Pakistan
    
    # System Configuration
    MAX_SESSIONS = int(os.environ.get('MAX_SESSIONS', 1000))
    SESSION_TIMEOUT = timedelta(minutes=int(os.environ.get('SESSION_TIMEOUT_MINUTES', 30)))
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Appointment Types
    APPOINTMENT_TYPES = {
        'cleaning': 'Regular Cleaning',
        'checkup': 'Dental Checkup',
        'consultation': 'Consultation',
        'emergency': 'Emergency Visit',
        'filling': 'Dental Filling',
        'extraction': 'Tooth Extraction',
        'root_canal': 'Root Canal',
        'crown': 'Crown Placement',
        'whitening': 'Teeth Whitening',
        'orthodontics': 'Orthodontic Consultation',
        'cosmetic': 'Cosmetic Dentistry',
        'general': 'General Dentistry',
        'restorative': 'Restorative Dentistry'
    }
    
    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        required_vars = [
            'GOOGLE_GEMINI_API_KEY',
            'GOOGLE_CALENDAR_CREDENTIALS_PATH'
        ]
        
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    @classmethod
    def get_business_hours_display(cls):
        """Get formatted business hours for display"""
        return {
            'weekday': f'{cls.BUSINESS_HOURS_START}:00 AM - {cls.BUSINESS_HOURS_END}:00 PM',
            'saturday': f'{cls.BUSINESS_HOURS_START}:00 AM - 3:00 PM',
            'sunday': 'Closed'
        }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = 'INFO'
    
    # Override with production values
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Must be set in production
    
    @classmethod
    def validate_config(cls):
        """Additional validation for production"""
        super().validate_config()
        
        if not cls.SECRET_KEY or cls.SECRET_KEY == 'dev-key-change-in-production':
            raise ValueError("SECRET_KEY must be set to a secure value in production")

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    LOG_LEVEL = 'DEBUG'
    
    # Use test-specific values
    CALENDAR_ID = 'test-calendar'
    APPOINTMENT_DURATION_MINUTES = 30  # Shorter for testing

# Configuration factory
def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development').lower()
    
    if env == 'production':
        return ProductionConfig
    elif env == 'testing':
        return TestingConfig
    else:
        return DevelopmentConfig 


