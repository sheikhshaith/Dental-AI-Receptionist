# app/models/conversation.py
"""
Conversation and session management models
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from app.config import Config

@dataclass
class Message:
    """Represents a chat message"""
    content: str
    sender: str  # 'user' or 'assistant'
    timestamp: datetime = field(default_factory=datetime.now)
    message_type: str = 'text'
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert message to dictionary"""
        return {
            'content': self.content,
            'sender': self.sender,
            'timestamp': self.timestamp.isoformat(),
            'type': self.message_type,
            'metadata': self.metadata
        }

@dataclass
class ConversationState:
    """Represents conversation state and booking progress"""
    stage: str = 'initial'  # initial, collecting_info, showing_slots, confirming, completed
    booking_data: Dict = field(default_factory=dict)
    last_intent: Optional[str] = None
    context: Dict = field(default_factory=dict)
    
    def update_booking_data(self, **kwargs):
        """Update booking data with new information"""
        self.booking_data.update(kwargs)
    
    def is_booking_complete(self) -> bool:
        """Check if booking has all required information"""
        required_fields = ['patient_name', 'date', 'time']
        return all(field in self.booking_data for field in required_fields)
    
    def clear_booking_data(self):
        """Clear booking data after completion"""
        self.booking_data.clear()
        self.stage = 'initial'

class SessionManager:
    """Manages conversation sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.session_timeout = Config.SESSION_TIMEOUT
    
    def get_session(self, session_id: str) -> Dict:
        """Get or create a session"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'state': ConversationState(),
                'messages': [],
                'created_at': datetime.now(),
                'last_activity': datetime.now()
            }
        
        # Update last activity
        self.sessions[session_id]['last_activity'] = datetime.now()
        return self.sessions[session_id]
    
    def add_message(self, session_id: str, message: Message):
        """Add message to session"""
        session = self.get_session(session_id)
        session['messages'].append(message)
        
        # Keep only last 50 messages per session
        if len(session['messages']) > 50:
            session['messages'] = session['messages'][-50:]
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        now = datetime.now()
        expired_sessions = [
            session_id for session_id, session_data in self.sessions.items()
            if now - session_data['last_activity'] > self.session_timeout
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
    
    def get_session_count(self) -> int:
        """Get active session count"""
        return len(self.sessions)