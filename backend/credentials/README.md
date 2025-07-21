# 🦷 AI Dental Receptionist Assistant

An intelligent AI-powered virtual receptionist designed for dental clinics. This application streamlines appointment scheduling by integrating with Google Calendar and automatically sends personalized confirmation messages to patients—enhancing patient experience and administrative efficiency.

## ✨ Features

- **Smart Appointment Scheduling**: AI-powered scheduling with natural language processing
- **Google Calendar Integration**: Seamless synchronization with existing calendar systems
- **Automated Confirmations**: Personalized appointment confirmation messages
- **Patient Management**: Comprehensive patient information handling
- **Multi-Channel Communication**: SMS, email, and phone integration
- **Intelligent Rescheduling**: Automatic conflict detection and resolution
- **Customizable Templates**: Personalized messaging templates for different appointment types
- **Real-time Availability**: Live calendar availability checking

## 🚀 Quick Start

### Prerequisites

- Node.js 18.0 or higher
- Python 3.8+ (for AI components)
- Google Cloud Platform account
- Google calender api integration
### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/ai-dental-receptionist.git
   cd ai-dental-receptionist
   ```

2. **Install dependencies**
   ```bash
   npm install
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   ```bash
   cp .env.example .env
   ```
   
   Configure your environment variables:
   ```env
   # Google Calendar API
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   GOOGLE_REDIRECT_URI=your_redirect_uri
   
   # Twilio Configuration
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_PHONE_NUMBER=your_twilio_number
   
   # Database
   DATABASE_URL=postgresql://username:password@localhost:5432/dental_assistant
   
   # AI Configuration
   OPENAI_API_KEY=your_openai_api_key
   ```

4. **Database Setup**
   ```bash
   npm run db:migrate
   npm run db:seed
   ```

5. **Start the application**
   ```bash
   npm run dev
   ```

## 📋 API Endpoints

### Appointments
- `GET /api/appointments` - List all appointments
- `POST /api/appointments` - Create new appointment
- `PUT /api/appointments/:id` - Update appointment
- `DELETE /api/appointments/:id` - Cancel appointment

### Patients
- `GET /api/patients` - List all patients
- `POST /api/patients` - Add new patient
- `PUT /api/patients/:id` - Update patient information

### Calendar
- `GET /api/calendar/availability` - Check available time slots
- `POST /api/calendar/sync` - Sync with Google Calendar

## 🛠️ Configuration

### Google Calendar Setup

1. Create a Google Cloud Project
2. Enable the Google Calendar API
3. Create OAuth 2.0 credentials
4. Add authorized redirect URIs
5. Download credentials and update environment variables

### AI Model Configuration

The assistant uses advanced NLP models for:
- Appointment intent recognition
- Patient query understanding
- Automated response generation
- Conflict resolution

Configure AI settings in `config/ai.json`:
```json
{
  "model": "gpt-4",
  "temperature": 0.7,
  "maxTokens": 150,
  "appointmentTypes": [
    "cleaning",
    "checkup",
    "filling",
    "extraction",
    "consultation"
  ]
}
```

## 📱 Usage Examples

### Scheduling an Appointment
```javascript
const appointment = await scheduleAppointment({
  patientName: "John Doe",
  phone: "+1234567890",
  appointmentType: "cleaning",
  preferredDate: "2024-08-15",
  preferredTime: "2:00 PM"
});
```

### Automated Confirmation Message
```
Hi John! 👋

Your dental appointment is confirmed:
📅 Date: August 15, 2024
⏰ Time: 2:00 PM
🏥 Location: Bright Smile Dental Clinic
👨‍⚕️ Provider: Dr. Smith

Please arrive 15 minutes early. Reply CANCEL to cancel.

Thank you for choosing our clinic! 🦷
```

## 🔧 Advanced Features

### Custom Workflows
Create custom appointment workflows in `workflows/`:
```yaml
name: "Emergency Appointment"
triggers:
  - keyword: "emergency"
  - keyword: "urgent"
actions:
  - priority: high
  - notification: immediate
  - availability_check: same_day
```

### Integration Webhooks
Set up webhooks for external integrations:
```javascript
app.post('/webhook/appointment-created', (req, res) => {
  // Custom logic for appointment creation
  sendCustomNotification(req.body.appointment);
  res.status(200).send('OK');
});
```

## 📊 Analytics & Reporting

The system provides comprehensive analytics:
- Appointment booking rates
- Patient satisfaction scores
- Response time metrics
- Calendar utilization
- Peak booking times

Access reports at `/dashboard/analytics`

## 🧪 Testing

Run the test suite:
```bash
npm test                 # Unit tests
npm run test:integration # Integration tests
npm run test:e2e        # End-to-end tests
```

## 🚀 Deployment

### Docker Deployment
```bash
docker build -t dental-assistant .
docker run -p 3000:3000 dental-assistant
```

### Production Environment
```bash
npm run build
npm run start:production
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📧 Email: support@dentalassistant.ai
- 💬 Discord: [Join our community](https://discord.gg/dentalassistant)
- 📖 Documentation: [Full Documentation](https://docs.dentalassistant.ai)
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/ai-dental-receptionist/issues)

## 🙏 Acknowledgments

- Google Calendar API team
- Twilio communications platform
- OpenAI for natural language processing
- The dental healthcare community for feedback and requirements

---

Built with ❤️ for dental professionals by the AI Dental Assistant team