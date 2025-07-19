# app/__init__.py
"""
Flask application factory for Dental Office AI Receptionist
"""
import os
import logging
from flask import Flask
from flask_cors import CORS
from app.config import Config

logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    """Create and configure Flask application"""
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configure CORS
    CORS(app, 
         origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    )
    
    # Ensure required directories exist
    os.makedirs('logs', exist_ok=True)
    os.makedirs('credentials', exist_ok=True)
    
    # Register blueprints
    from app.routes.health import health_bp
    from app.routes.chat import chat_bp
    # from app.routes.calendar import calendar_bp
    
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(chat_bp, url_prefix='/api')
    # app.register_blueprint(calendar_bp, url_prefix='/api')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Endpoint not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return {'error': 'Internal server error'}, 500
    
    logger.info("Flask application created successfully")
    return app