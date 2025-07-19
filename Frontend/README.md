# 🦷 Dental Office AI Receptionist

A comprehensive AI-powered receptionist system for dental offices that handles appointment bookings, customer inquiries, and calendar management with natural language processing.

## ✨ Features

### 🤖 AI-Powered Chatbot
- **Natural Language Processing** using Google Gemini AI
- **24/7 Availability** for patient inquiries
- **Intelligent Conversation Flow** with context awareness
- **Multi-language Support** for diverse patient base

### 📅 Smart Appointment Management
- **Real-time Google Calendar Integration**
- **Conflict Detection** with buffer time management
- **Timezone-aware Scheduling** (Pakistan/Karachi timezone)
- **Automatic Slot Generation** with availability checking
- **Same-day Booking** with future time filtering

### 🛡️ Business Logic & Validation
- **Business Hours Enforcement** (Mon-Fri: 9AM-7PM, Sat: 9AM-3PM, Sun: Closed)
- **Past Appointment Prevention** with 15-minute buffer
- **Weekend Handling** (Sunday closure, Saturday availability)
- **Appointment Type Management** (General, Cosmetic, Restorative)

### 💻 Modern Tech Stack
- **Frontend**: React.js with Vite, Tailwind CSS, Lucide Icons
- **Backend**: Flask (Python) with RESTful APIs
- **AI**: Google Gemini 2.0 Flash for natural language processing
- **Calendar**: Google Calendar API integration
- **Deployment**: Local development with production readiness

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** (for Flask backend)
- **Google Cloud Project** with Calendar API enabled
- **Google Gemini API key**

### 1. Clone Repository
```bash
git clone <repository-url>
cd dental-office-ai-receptionist
```

### 2. Backend Setup (Flask)
```bash
cd backend
python -m venv dental_office
source dental_office/bin/activate  # On Windows: dental_office\Scripts\activate
pip install -r requirements.txt
```

**Backend Dependencies (`requirements.txt`):**
```txt
Flask==2.3.3
Flask-CORS==4.0.0
google-api-python-client==2.100.0
google-auth-httplib2==0.1.1
google-auth-oauthlib==1.0.0
google-generativeai==0.3.0
python-dotenv==1.0.0
pytz==2023.3
```

### 3. Frontend Setup (React)
```bash
cd frontend
npm install
```

### 4. Environment Configuration

**Backend `.env` (Flask):**
```env
# Google APIs
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_CALENDAR_CREDENTIALS_PATH=credentials/credentials.json
GOOGLE_CALENDAR_TOKEN_PATH=credentials/token.json
CALENDAR_ID=your_calendar_email@gmail.com

# Business Configuration
BUSINESS_NAME=Bright Smile Dental Office
BUSINESS_PHONE=(555) 123-4567
BUSINESS_EMAIL=contact@brightsmile.com
BUSINESS_ADDRESS=123 Main St, City, State 12345

# Schedule Configuration
BUSINESS_HOURS_START=9
BUSINESS_HOURS_END=19
TIMEZONE=Asia/Karachi
APPOINTMENT_DURATION_MINUTES=60
BUFFER_TIME_MINUTES=15

# Flask Configuration
SECRET_KEY=your-secret-key-change-in-production
FLASK_ENV=development
FLASK_DEBUG=True
```

**Frontend `.env` (React):**
```env
VITE_API_URL=http://localhost:5000
VITE_OFFICE_NAME=Bright Smile Dental Office
VITE_OFFICE_PHONE=(555) 123-4567
VITE_OFFICE_EMAIL=contact@brightsmile.com
```

### 5. Google Calendar Setup

1. **Create Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project
   - Enable Google Calendar API

2. **Create Credentials**:
   - Go to APIs & Services > Credentials
   - Create OAuth 2.0 Client ID
   - Download credentials as `credentials/credentials.json`

3. **Generate Token**:
   ```bash
   cd backend
   python calendar_service.py
   ```
   - Follow OAuth flow to generate `credentials/token.json`

### 6. Run Application

**Start Backend (Flask):**
```bash
cd backend
python run.py
```
✅ Backend API runs on: `http://localhost:5000`

**Start Frontend (React):**
```bash
cd frontend
npm run dev
```
✅ Frontend runs on: `http://localhost:3000`

## 🎯 Usage Examples

### Booking Flow
1. **User**: "I want to book an appointment"
2. **AI**: "What type of service do you need?"
3. **User**: "General dentistry"
4. **AI**: "Would you like to book for today or later?"
5. **User**: "Today"
6. **AI**: Shows available time slots for today
7. **User**: Selects time slot
8. **AI**: Collects contact information and confirms booking

### Natural Language Examples
- "Book me an appointment for tomorrow at 2 PM"
- "What are your office hours?"
- "I need emergency dental care"
- "Cancel my appointment"
- "What services do you offer?"

## ⚙️ Configuration

### Flask Backend Configuration
Configure in `backend/.env`:
```env
# Business Hours
BUSINESS_HOURS_START=9     # 9 AM
BUSINESS_HOURS_END=19      # 7 PM
TIMEZONE=Asia/Karachi      # Your timezone

# Flask Settings
FLASK_ENV=development      # or production
FLASK_DEBUG=True          # Enable debug mode
SECRET_KEY=your-secret-key
```

### Appointment Types
Defined in `backend/config.py`:
```python
APPOINTMENT_TYPES = {
    'cleaning': 'Regular Cleaning',
    'checkup': 'Dental Checkup',
    'consultation': 'Consultation',
    'emergency': 'Emergency Visit',
    'cosmetic': 'Cosmetic Dentistry',
    'general': 'General Dentistry',
    'restorative': 'Restorative Dentistry'
}
```

## 🧪 Testing

### Backend Tests (Flask)
```bash
cd backend

# Test calendar connection
python calendar_service.py

# Run Flask app
python run.py
```

### Frontend Testing (React)
```bash
cd frontend

# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 🚨 Troubleshooting

### Common Flask Backend Issues

**1. Timezone Mismatch Errors**
```bash
# Check timezone configuration
curl http://localhost:5000/api/test-timezone
```
**Solution**: Ensure `TIMEZONE=Asia/Karachi` in `backend/.env`

**2. Flask Calendar API Errors**
```bash
# Test calendar connection
cd backend
python calendar_service.py
```
**Solution**: Verify `credentials.json` and regenerate `token.json`

**3. Flask Import Errors**
```bash
# Check if all dependencies are installed
cd backend
pip install -r requirements.txt

# Activate virtual environment
source dental_office/bin/activate  # Linux/Mac
dental_office\Scripts\activate     # Windows
```

**4. Flask CORS Issues**
Check if Flask-CORS is installed and configured:
```python
# In run.py
from flask_cors import CORS
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend
```

**5. Past Appointment Errors**
- Ensure server timezone matches `Asia/Karachi`
- Check system clock accuracy
- Verify 15-minute buffer in bookings

### Flask Debug Mode
Enable detailed logging in `backend/.env`:
```env
LOG_LEVEL=DEBUG
FLASK_DEBUG=True
FLASK_ENV=development
```

### Backend Log Locations
- **Console Output**: Real-time logs when running `python run.py`
- **File Logs**: Configure in Flask app if needed
- **Calendar Logs**: Check Google Cloud Console for API errors

## 🔒 Security Considerations

### Flask Production Deployment
1. **Environment Variables**:
   ```env
   FLASK_ENV=production
   FLASK_DEBUG=False
   SECRET_KEY=secure-random-256-bit-key
   ```

2. **Flask Security**:
   - Use production WSGI server (Gunicorn, uWSGI)
   - Implement rate limiting with Flask-Limiter
   - Configure CORS for production domains only
   - Use HTTPS in production

3. **Python Dependencies**:
   ```bash
   # Generate exact dependencies
   pip freeze > requirements.txt
   
   # Security audit
   pip audit
   ```

## 🚀 Deployment

### Flask Backend Deployment

**Using Gunicorn (Production):**
```bash
cd backend
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

**Using Docker:**
```dockerfile
# backend/Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
```

### React Frontend Deployment
```bash
cd frontend
npm run build
# Deploy dist/ folder to your web server
```

## 📊 Flask Backend Architecture

```
Flask Application (run.py)
├── Routes & Endpoints
│   ├── /api/book-appointment
│   ├── /api/available-slots
│   ├── /api/today-availability
│   └── /api/health
├── Services Layer
│   ├── calendar_service.py (Google Calendar)
│   ├── gemini_service.py (AI Processing)
│   └── intent_processor.py (NLP)
├── Configuration
│   ├── config.py (Settings)
│   └── .env (Environment)
└── External APIs
    ├── Google Calendar API
    └── Google Gemini AI API
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

### Code Style
- Python: Follow PEP 8
- JavaScript: Use ESLint with provided configuration
- Commit messages: Use conventional commits format

## 📄 License

This project is licensed under the MIT License.

## 📚 Documentation

- [Google Calendar API Docs](https://developers.google.com/calendar)
- [Google Gemini AI Docs](https://ai.google.dev/)
- [React Documentation](https://react.dev/)
- [Flask Documentation](https://flask.palletsprojects.com/)

### FAQ

**Q: Can I use a different timezone?**
A: Yes, change `TIMEZONE` in `.env` to your desired timezone (e.g., `America/New_York`)

**Q: How do I add new appointment types?**
A: Modify `APPOINTMENT_TYPES` in `config.py` and restart the backend

**Q: Can I integrate with other calendar systems?**
A: The system is designed for Google Calendar, but can be extended for other providers

**Q: How do I customize business hours?**
A: Update `BUSINESS_HOURS_START` and `BUSINESS_HOURS_END` in `.env`

---

## 🌟 Acknowledgments

- Google Cloud Platform for Calendar and Gemini AI APIs
- React and Flask communities for excellent frameworks
- Tailwind CSS for beautiful styling
- Lucide for clean icons

---

**Made with ❤️ for dental practices worldwide**