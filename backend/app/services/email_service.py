# app/services/email_service.py
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
from typing import Optional, Dict, Any

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # Email Configuration from environment
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('BUSINESS_EMAIL', 'contact@brightsmile.com')
        self.from_name = os.getenv('BUSINESS_NAME', 'Bright Smile Dental Office')
        
        # Business Information
        self.business_name = os.getenv('BUSINESS_NAME', 'Bright Smile Dental Office')
        self.business_phone = os.getenv('BUSINESS_PHONE', '(555) 123-4567')
        self.business_address = os.getenv('BUSINESS_ADDRESS', '123 Main St, City, State 12345')
        
    def send_appointment_confirmation(self, 
                                   patient_name: str, 
                                   patient_email: str, 
                                   appointment_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send appointment confirmation email to patient
        """
        try:
            if not patient_email or not self.smtp_username or not self.smtp_password:
                logger.warning("Email configuration incomplete - skipping email send")
                return {
                    'success': False,
                    'message': 'Email configuration not complete'
                }
                
            # Create email content
            subject = f"🦷 Appointment Confirmation - {self.business_name}"
            
            # HTML email template
            html_body = self._create_html_email_template(patient_name, appointment_details)
            
            # Plain text version
            text_body = self._create_text_email_template(patient_name, appointment_details)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = patient_email
            msg['Subject'] = subject
            
            # Add both plain text and HTML versions
            text_part = MIMEText(text_body, 'plain', 'utf-8')
            html_part = MIMEText(html_body, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                
            logger.info(f"✅ Confirmation email sent successfully to {patient_email}")
            
            return {
                'success': True,
                'message': 'Confirmation email sent successfully',
                'recipient': patient_email
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to send confirmation email: {e}")
            return {
                'success': False,
                'message': f'Failed to send confirmation email: {str(e)}',
                'error': str(e)
            }
    
    def _create_html_email_template(self, patient_name: str, appointment_details: Dict[str, Any]) -> str:
        """Create HTML email template for appointment confirmation"""
        
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Appointment Confirmation</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #FF6B6B 0%, #A855F7 100%);
        }}
        .email-container {{
            max-width: 600px;
            margin: 20px auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(10px);
        }}
        .header {{
            background: linear-gradient(135deg, #FF6B6B 0%, #A855F7 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: bold;
        }}
        .header p {{
            margin: 5px 0 0 0;
            font-size: 16px;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .greeting {{
            font-size: 18px;
            color: #4C1D95;
            margin-bottom: 20px;
        }}
        .appointment-card {{
            background: linear-gradient(135deg, rgba(255, 107, 107, 0.1), rgba(168, 85, 247, 0.1));
            border-radius: 12px;
            padding: 25px;
            margin: 20px 0;
            border: 1px solid rgba(168, 85, 247, 0.3);
        }}
        .appointment-title {{
            font-size: 20px;
            font-weight: bold;
            color: #4C1D95;
            margin-bottom: 15px;
            text-align: center;
        }}
        .detail-row {{
            display: flex;
            margin: 12px 0;
            padding: 8px 0;
            border-bottom: 1px solid rgba(168, 85, 247, 0.1);
        }}
        .detail-label {{
            font-weight: bold;
            color: #4C1D95;
            width: 120px;
            flex-shrink: 0;
        }}
        .detail-value {{
            color: #666;
            flex: 1;
        }}
        .important-note {{
            background: rgba(255, 107, 107, 0.1);
            border-left: 4px solid #FF6B6B;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }}
        .contact-info {{
            background: rgba(168, 85, 247, 0.05);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        .contact-title {{
            font-weight: bold;
            color: #4C1D95;
            margin-bottom: 10px;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 14px;
            border-top: 1px solid rgba(168, 85, 247, 0.1);
        }}
        .button {{
            display: inline-block;
            background: linear-gradient(135deg, #FF6B6B, #A855F7);
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 25px;
            font-weight: bold;
            margin: 10px 5px;
            transition: transform 0.2s;
        }}
        .button:hover {{
            transform: translateY(-2px);
        }}
        .emoji {{
            font-size: 20px;
            margin-right: 8px;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>🦷 {self.business_name}</h1>
            <p>Your Trusted Dental Care Partner</p>
        </div>
        
        <div class="content">
            <div class="greeting">
                Hello {patient_name}! 👋
            </div>
            
            <p>Thank you for booking your appointment with us! We're excited to take care of your dental needs.</p>
            
            <div class="appointment-card">
                <div class="appointment-title">
                    ✅ Your Appointment is Confirmed!
                </div>
                
                <div class="detail-row">
                    <div class="detail-label">👤 Patient:</div>
                    <div class="detail-value">{patient_name}</div>
                </div>
                
                <div class="detail-row">
                    <div class="detail-label">🦷 Service:</div>
                    <div class="detail-value">{appointment_details.get('type', 'General Checkup')}</div>
                </div>
                
                <div class="detail-row">
                    <div class="detail-label">📅 Date:</div>
                    <div class="detail-value">{appointment_details.get('date', 'Date not available')}</div>
                </div>
                
                <div class="detail-row">
                    <div class="detail-label">⏰ Time:</div>
                    <div class="detail-value">{appointment_details.get('time', 'Time not available')}</div>
                </div>
                
                <div class="detail-row">
                    <div class="detail-label">⏱️ Duration:</div>
                    <div class="detail-value">{appointment_details.get('duration', '60 minutes')}</div>
                </div>
                
                <div class="detail-row">
                    <div class="detail-label">🏥 Location:</div>
                    <div class="detail-value">{self.business_address}</div>
                </div>
            </div>
            
            <div class="important-note">
                <strong>📋 Important Reminders:</strong>
                <ul>
                    <li>Please arrive 15 minutes early for check-in</li>
                    <li>Bring a valid ID and insurance card (if applicable)</li>
                    <li>If you need to reschedule, please call us at least 24 hours in advance</li>
                    <li>For emergencies, call us immediately</li>
                </ul>
            </div>
            
            <div class="contact-info">
                <div class="contact-title">📞 Contact Information:</div>
                <strong>Phone:</strong> {self.business_phone}<br>
                <strong>Email:</strong> {self.from_email}<br>
                <strong>Address:</strong> {self.business_address}
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="tel:{self.business_phone.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')}" class="button">
                    📞 Call Us
                </a>
                <a href="mailto:{self.from_email}" class="button">
                    📧 Email Us
                </a>
            </div>
            
            <p>We look forward to seeing you soon! If you have any questions or concerns, please don't hesitate to contact us.</p>
            
            <p style="margin-top: 30px;">
                <strong>Best regards,</strong><br>
                The {self.business_name} Team 🦷✨
            </p>
        </div>
        
        <div class="footer">
            <p>This is an automated confirmation email from {self.business_name}</p>
            <p>📅 Booked on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            <p style="font-size: 12px; margin-top: 15px;">
                Please do not reply to this email. For any inquiries, contact us at {self.business_phone}
            </p>
        </div>
    </div>
</body>
</html>
"""

    def _create_text_email_template(self, patient_name: str, appointment_details: Dict[str, Any]) -> str:
        """Create plain text email template for appointment confirmation"""
        
        return f"""
🦷 {self.business_name}
APPOINTMENT CONFIRMATION

Hello {patient_name}!

Thank you for booking your appointment with us! We're excited to take care of your dental needs.

✅ YOUR APPOINTMENT DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 Patient: {patient_name}
🦷 Service: {appointment_details.get('type', 'General Checkup')}
📅 Date: {appointment_details.get('date', 'Date not available')}
⏰ Time: {appointment_details.get('time', 'Time not available')}
⏱️ Duration: {appointment_details.get('duration', '60 minutes')}
🏥 Location: {self.business_address}

📋 IMPORTANT REMINDERS:
━━━━━━━━━━━━━━━━━━━━━━━━

• Please arrive 15 minutes early for check-in
• Bring a valid ID and insurance card (if applicable)  
• If you need to reschedule, please call us at least 24 hours in advance
• For emergencies, call us immediately

📞 CONTACT INFORMATION:
━━━━━━━━━━━━━━━━━━━━━━━━

Phone: {self.business_phone}
Email: {self.from_email}
Address: {self.business_address}

We look forward to seeing you soon! If you have any questions or concerns, please don't hesitate to contact us.

Best regards,
The {self.business_name} Team 🦷✨

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated confirmation email from {self.business_name}
📅 Booked on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

Please do not reply to this email. For any inquiries, contact us at {self.business_phone}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def send_reminder_email(self, 
                          patient_name: str, 
                          patient_email: str, 
                          appointment_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send appointment reminder email (for future use)
        """
        try:
            subject = f"🔔 Appointment Reminder - {self.business_name}"
            
            html_body = self._create_reminder_html_template(patient_name, appointment_details)
            text_body = self._create_reminder_text_template(patient_name, appointment_details)
            
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = patient_email
            msg['Subject'] = subject
            
            text_part = MIMEText(text_body, 'plain', 'utf-8')
            html_part = MIMEText(html_body, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                
            logger.info(f"✅ Reminder email sent successfully to {patient_email}")
            
            return {
                'success': True,
                'message': 'Reminder email sent successfully',
                'recipient': patient_email
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to send reminder email: {e}")
            return {
                'success': False,
                'message': f'Failed to send reminder email: {str(e)}',
                'error': str(e)
            }
    
    def _create_reminder_html_template(self, patient_name: str, appointment_details: Dict[str, Any]) -> str:
        """Create HTML template for appointment reminder"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #f9f9f9; border-radius: 10px; }}
        .header {{ background: linear-gradient(135deg, #FF6B6B, #A855F7); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ padding: 20px; background: white; }}
        .reminder-box {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔔 Appointment Reminder</h1>
            <p>{self.business_name}</p>
        </div>
        <div class="content">
            <h2>Hello {patient_name}!</h2>
            <div class="reminder-box">
                <strong>⏰ Your appointment is coming up soon!</strong>
            </div>
            <p><strong>📅 Date:</strong> {appointment_details.get('date')}</p>
            <p><strong>⏰ Time:</strong> {appointment_details.get('time')}</p>
            <p><strong>🦷 Service:</strong> {appointment_details.get('type')}</p>
            <p><strong>📞 Contact:</strong> {self.business_phone}</p>
            <p>See you soon!</p>
        </div>
    </div>
</body>
</html>
"""

    def _create_reminder_text_template(self, patient_name: str, appointment_details: Dict[str, Any]) -> str:
        """Create plain text template for appointment reminder"""
        return f"""
🔔 APPOINTMENT REMINDER - {self.business_name}

Hello {patient_name}!

⏰ Your appointment is coming up soon!

📅 Date: {appointment_details.get('date')}
⏰ Time: {appointment_details.get('time')}
🦷 Service: {appointment_details.get('type')}

📞 Contact us: {self.business_phone}

See you soon!

Best regards,
{self.business_name} Team
"""

    def test_email_configuration(self) -> Dict[str, Any]:
        """Test email configuration and connectivity"""
        try:
            if not self.smtp_username or not self.smtp_password:
                return {
                    'success': False,
                    'message': 'SMTP credentials not configured',
                    'details': 'Please set SMTP_USERNAME and SMTP_PASSWORD in your .env file'
                }
            
            # Test connection
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                
            logger.info("✅ Email configuration test successful")
            
            return {
                'success': True,
                'message': 'Email configuration is working correctly',
                'details': {
                    'smtp_server': self.smtp_server,
                    'smtp_port': self.smtp_port,
                    'from_email': self.from_email,
                    'from_name': self.from_name
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Email configuration test failed: {e}")
            return {
                'success': False,
                'message': f'Email configuration test failed: {str(e)}',
                'error': str(e)
            }

# Create global email service instance
email_service = EmailService()

# Convenience functions for easy importing
def send_appointment_confirmation(patient_name: str, patient_email: str, appointment_details: Dict[str, Any]) -> Dict[str, Any]:
    """Send appointment confirmation email"""
    return email_service.send_appointment_confirmation(patient_name, patient_email, appointment_details)

def send_reminder_email(patient_name: str, patient_email: str, appointment_details: Dict[str, Any]) -> Dict[str, Any]:
    """Send appointment reminder email"""
    return email_service.send_reminder_email(patient_name, patient_email, appointment_details)

def test_email_configuration() -> Dict[str, Any]:
    """Test email configuration"""
    return email_service.test_email_configuration()

if __name__ == "__main__":
    # Test email configuration when run directly
    print("🧪 Testing Email Configuration...")
    result = test_email_configuration()
    print(f"Result: {result}")