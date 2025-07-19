# app/routes/health.py
"""
Health check endpoints
"""
import logging
from flask import Blueprint, jsonify
from datetime import datetime
from app.config import Config

logger = logging.getLogger(__name__)
health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'Dental Office AI Receptionist',
            'version': '1.0.0'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@health_bp.route('/health/detailed', methods=['GET'])
def detailed_health_check():
    """Detailed health check with service dependencies"""
    try:
        # Check Gemini API
        gemini_status = 'unknown'
        if Config.GOOGLE_GEMINI_API_KEY:
            gemini_status = 'configured'
        else:
            gemini_status = 'not_configured'
        
        # Check Calendar API
        calendar_status = 'unknown'
        try:
            import os
            if os.path.exists(Config.GOOGLE_CALENDAR_CREDENTIALS_PATH):
                calendar_status = 'configured'
            else:
                calendar_status = 'not_configured'
        except Exception:
            calendar_status = 'error'
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'Dental Office AI Receptionist',
            'version': '1.0.0',
            'dependencies': {
                'gemini_api': gemini_status,
                'calendar_api': calendar_status
            },
            'config': {
                'business_name': Config.BUSINESS_NAME,
                'business_hours': f"{Config.BUSINESS_HOURS_START}:00 - {Config.BUSINESS_HOURS_END}:00",
                'timezone': Config.TIMEZONE
            }
        })
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500