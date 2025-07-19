# app/models/appointment.py
"""
Appointment-related data models
"""
from datetime import datetime, time
from typing import Optional, Dict, List
from dataclasses import dataclass
from app.config import Config

@dataclass
class TimeSlot:
    """Represents an available time slot"""
    start_time: time
    end_time: time
    is_available: bool = True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format"""
        return {
            'start': self.start_time.strftime('%I:%M %p'),
            'end': self.end_time.strftime('%I:%M %p'),
            'available': self.is_available,
            'start_24h': self.start_time.strftime('%H:%M'),
            'end_24h': self.end_time.strftime('%H:%M')
        }

@dataclass
class AppointmentRequest:
    """Represents an appointment booking request"""
    patient_name: str
    date: str  # YYYY-MM-DD format
    time: str  # HH:MM format
    appointment_type: str = 'checkup'
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    
    def to_calendar_event(self) -> Dict:
        """Convert to Google Calendar event format"""
        appointment_type_display = Config.APPOINTMENT_TYPES.get(
            self.appointment_type, 
            self.appointment_type.title()
        )
        
        return {
            'summary': f'{appointment_type_display} - {self.patient_name}',
            'description': self._build_description(),
            'location': Config.BUSINESS_ADDRESS,
            'attendees': self._build_attendees()
        }
    
    def _build_description(self) -> str:
        """Build appointment description"""
        description_parts = [
            f'Patient: {self.patient_name}',
            f'Type: {Config.APPOINTMENT_TYPES.get(self.appointment_type, self.appointment_type.title())}',
        ]
        
        if self.phone:
            description_parts.append(f'Phone: {self.phone}')
        
        if self.email:
            description_parts.append(f'Email: {self.email}')
        
        if self.notes:
            description_parts.append(f'Notes: {self.notes}')
        
        description_parts.append(f'\nBooked via AI Receptionist')
        
        return '\n'.join(description_parts)
    
    def _build_attendees(self) -> List[Dict]:
        """Build attendees list"""
        attendees = []
        
        if self.email:
            attendees.append({
                'email': self.email,
                'displayName': self.patient_name,
                'responseStatus': 'needsAction'
            })
        
        return attendees