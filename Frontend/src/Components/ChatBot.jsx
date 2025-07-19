

// components/ChatBot.jsx
import { useState, useEffect, useRef } from 'react'
import { Send, Bot, User, Clock, Phone, Mail, AlertCircle } from 'lucide-react'
import axios from 'axios'

const ChatBot = () => {
  const [messages, setMessages] = useState([])
  const [currentStep, setCurrentStep] = useState('welcome')
  const [userInput, setUserInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [userData, setUserData] = useState({})
  const [availableSlots, setAvailableSlots] = useState([])
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  // FIXED: Simple and reliable time conversion
  const convertTo24Hour = (time12h) => {
    try {
      // Clean input and handle different formats
      const cleanTime = time12h.trim().replace(/\s+/g, ' ')
      
      // Handle cases like "10:30 AM", "2:30 PM", "14:30"
      if (!cleanTime.includes('AM') && !cleanTime.includes('PM')) {
        // Already 24-hour format
        return cleanTime
      }
      
      const [time, period] = cleanTime.split(' ')
      let [hours, minutes] = time.split(':')
      
      hours = parseInt(hours, 10)
      minutes = minutes || '00'
      
      // Convert to 24-hour
      if (period.toUpperCase() === 'AM') {
        if (hours === 12) hours = 0
      } else if (period.toUpperCase() === 'PM') {
        if (hours !== 12) hours += 12
      }
      
      const result = `${hours.toString().padStart(2, '0')}:${minutes.padStart(2, '0')}`
      console.log(`🕐 Time conversion: "${time12h}" -> "${result}"`)
      return result
      
    } catch (e) {
      console.error('Time conversion error:', e)
      return '09:00'
    }
  }

  const formatDateSafe = (dateString) => {
    try {
      if (!dateString) return 'Date not selected'
      
      const date = new Date(dateString + 'T00:00:00')
      if (isNaN(date.getTime())) {
        return dateString
      }
      
      return date.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: '2-digit', 
        year: 'numeric'
      })
    } catch (e) {
      console.error('Date formatting error:', e)
      return dateString || 'Date not selected'
    }
  }

  const isWeekend = (dateString) => {
    try {
      const date = new Date(dateString + 'T00:00:00')
      const dayOfWeek = date.getDay()
      return dayOfWeek === 0 // Only Sunday
    } catch (e) {
      console.error('Weekend check error:', e)
      return false
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    const welcomeMessage = {
      id: Date.now(),
      type: 'bot',
      content: '🦷 Welcome to Bright Smile Dental Office! I\'m your AI assistant, here to help you 24/7.\n\nTo get started, may I know your name please?',
      timestamp: new Date()
    }
    setMessages([welcomeMessage])
    setCurrentStep('asking_name')
  }, [])

  const addMessage = (content, type = 'bot') => {
    const newMessage = {
      id: Date.now() + Math.random(),
      type,
      content,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, newMessage])
  }

  const addTypingMessage = () => {
    setIsLoading(true)
    setTimeout(() => {
      setIsLoading(false)
    }, 1000)
  }

  const handleUserInput = async (input) => {
    if (!input.trim()) return

    addMessage(input, 'user')
    setUserInput('')
    addTypingMessage()

    setTimeout(async () => {
      await processUserResponse(input.trim())
    }, 1000)
  }

  const processUserResponse = async (input) => {
    switch (currentStep) {
      case 'asking_name':
        setUserData(prev => ({ ...prev, name: input }))
        addMessage(`Nice to meet you, ${input}! 😊\n\nHow can I assist you today? You can:\n\n🦷 Learn about our Services\n🕒 Check our Hours\n📞 Get Contact Info\n🚨 Emergency Information\n📅 Book an Appointment`)
        setCurrentStep('main_menu')
        break

      case 'main_menu':
        await handleMainMenuChoice(input)
        break

      case 'service_selection':
        await handleServiceSelection(input)
        break

      case 'asking_date_preference':
        await handleDatePreference(input)
        break

      case 'asking_specific_date':
        await handleSpecificDateInput(input)
        break

      case 'asking_time':
        await handleTimeInput(input)
        break

      case 'asking_phone':
        setUserData(prev => ({ ...prev, phone: input }))
        addMessage('Perfect! And what\'s your email address? (Optional - you can type "skip" if you prefer)')
        setCurrentStep('asking_email')
        break

      case 'asking_email':
        if (input.toLowerCase() !== 'skip') {
          setUserData(prev => ({ ...prev, email: input }))
        }
        await confirmAndBookAppointment()
        break

      case 'slot_selection':
        await handleSlotSelection(input)
        break

      case 'final_confirmation':
        await handleFinalConfirmation(input)
        break

      default:
        addMessage(`How can I assist you today, ${userData.name}?\n\n🦷 Learn about our Services\n🕒 Check our Hours\n📞 Get Contact Info\n📅 Book an Appointment`)
        setCurrentStep('main_menu')
    }
  }

  const handleMainMenuChoice = async (input) => {
    const lowerInput = input.toLowerCase()

    if (lowerInput.includes('service') || lowerInput.includes('dental')) {
      addMessage('Great! We offer comprehensive dental services:\n\n✨ Cosmetic Dentistry\n   (Teeth whitening, veneers, smile makeovers)\n\n🛡️ General Dentistry\n   (Cleanings, checkups, preventive care)\n\n🔧 Restorative Dentistry\n   (Fillings, crowns, bridges, implants)\n\nWhich service interests you, or would you like to book an appointment?')
      setCurrentStep('service_selection')
    } else if (lowerInput.includes('hour') || lowerInput.includes('time')) {
      addMessage('🕒 Our office hours are:\n\n📅 Monday - Friday: 9:00 AM - 7:00 PM\n📅 Saturday: 9:00 AM - 3:00 PM\n📅 Sunday: Closed\n\nWould you like to book an appointment?')
      setCurrentStep('main_menu')
    } else if (lowerInput.includes('contact') || lowerInput.includes('phone') || lowerInput.includes('address')) {
      addMessage('📞 Contact Information:\n\n📱 Phone: (555) 123-4567\n📧 Email: contact@brightsmile.com\n📍 Address: 123 Main St, City, State 12345\n\nWould you like to schedule an appointment?')
      setCurrentStep('main_menu')
    } else if (lowerInput.includes('emergency')) {
      addMessage('🚨 For dental emergencies:\n\n📞 Call: (555) 123-4567\n🌙 After hours: (555) 999-HELP\n\nFor immediate care, please call us directly.\n\nWould you like to schedule a regular appointment?')
      setCurrentStep('main_menu')
    } else if (lowerInput.includes('book') || lowerInput.includes('appointment') || lowerInput.includes('schedule')) {
      addMessage('Excellent! I\'d be happy to help you book an appointment. 📅\n\nWhat type of service do you need?\n\n✨ Cosmetic Dentistry\n🛡️ General Dentistry  \n🔧 Restorative Dentistry\n\nOr just tell me what you need help with!')
      setCurrentStep('service_selection')
    } else {
      addMessage('I understand you\'re interested in our dental services. Let me help you with:\n\n🦷 Learn about our Services\n🕒 Check our Hours\n📞 Get Contact Info\n📅 Book an Appointment\n\nWhat would you like to know?')
    }
  }

  const handleServiceSelection = async (input) => {
    const lowerInput = input.toLowerCase()
    let selectedService = ''

    if (lowerInput.includes('cosmetic') || lowerInput.includes('whitening') || lowerInput.includes('veneer')) {
      selectedService = 'Cosmetic Dentistry'
    } else if (lowerInput.includes('general') || lowerInput.includes('cleaning') || lowerInput.includes('checkup')) {
      selectedService = 'General Dentistry'
    } else if (lowerInput.includes('restorative') || lowerInput.includes('filling') || lowerInput.includes('crown') || lowerInput.includes('implant')) {
      selectedService = 'Restorative Dentistry'
    } else if (lowerInput.includes('book') || lowerInput.includes('appointment')) {
      selectedService = 'General Dentistry'
    } else {
      addMessage('I\'d be happy to help! Could you please specify which service you\'re interested in?\n\n✨ Cosmetic Dentistry\n🛡️ General Dentistry\n🔧 Restorative Dentistry\n\nOr just type "book appointment" to proceed with general services.')
      return
    }

    setUserData(prev => ({ ...prev, service: selectedService }))
    addMessage(`Perfect! ${selectedService} is one of our specialties. 🌟\n\nWould you like to book an appointment for today or on a later day?`)
    setCurrentStep('asking_date_preference')
  }

  const handleDatePreference = async (input) => {
    const lowerInput = input.toLowerCase()

    if (lowerInput.includes('today')) {
      await checkTodayAvailability()
    } else if (lowerInput.includes('later') || lowerInput.includes('tomorrow') || lowerInput.includes('another') || lowerInput.includes('different')) {
      await showNextFewDaysAvailability()
    } else {
      await handleSpecificDateInput(input)
    }
  }

  // FIXED: Enhanced today availability check with proper time filtering
  const checkTodayAvailability = async () => {
    setIsLoading(true)
    addMessage('Let me check today\'s availability... 🔍')
    
    try {
      const today = new Date()
      const dateStr = today.toISOString().split('T')[0]
      
      console.log(`🔍 Checking today: ${dateStr}`)
      
      const response = await axios.get(`/api/available-slots?date=${dateStr}`)
      
      if (response.data.success && response.data.available_slots.length > 0) {
        console.log(`📅 Found ${response.data.available_slots.length} slots for today`)
        
        // FIXED: Use backend-filtered slots (they're already filtered for future times)
        const futureSlots = response.data.available_slots
        
        if (futureSlots.length > 0) {
          setAvailableSlots(futureSlots)
          setUserData(prev => ({ ...prev, date: dateStr }))
          
          const slotsText = futureSlots
            .slice(0, 6)
            .map((slot, index) => `${index + 1}. ${slot.formatted_time}`)
            .join('\n')
          
          addMessage(`Great! I found available time slots for today:\n\n${slotsText}\n\nPlease tell me the number (1-${Math.min(6, futureSlots.length)}) or specific time you prefer.`)
          setCurrentStep('slot_selection')
        } else {
          addMessage('Sorry, no appointments are available for the rest of today. 😔\n\nWould you like to see availability for tomorrow or the next few days?')
          await showNextFewDaysAvailability()
        }
      } else {
        addMessage('Sorry, no appointments are available today. 😔\n\nWould you like to see availability for the next few days?')
        await showNextFewDaysAvailability()
      }
    } catch (error) {
      console.error('Today availability check error:', error)
      addMessage('I couldn\'t check today\'s availability. Let me show you the next few days instead.')
      await showNextFewDaysAvailability()
    } finally {
      setIsLoading(false)
    }
  }

  const showNextFewDaysAvailability = async () => {
    addMessage('Let me show you availability for the next few days... 📅')
    
    const nextDays = []
    const today = new Date()
    
    for (let i = 1; i <= 4; i++) {
      const futureDate = new Date(today)
      futureDate.setDate(today.getDate() + i)
      
      const dayOfWeek = futureDate.getDay()
      if (dayOfWeek !== 0) { // Skip Sundays
        const dateStr = futureDate.toISOString().split('T')[0]
        const dayName = futureDate.toLocaleDateString('en-US', { weekday: 'long' })
        const dateDisplay = futureDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        
        nextDays.push({
          dateStr,
          display: `${dayName}, ${dateDisplay}`,
          dayName
        })
      }
    }
    
    const daysText = nextDays
      .map((day, index) => `${index + 1}. ${day.display}`)
      .join('\n')
    
    addMessage(`Here are the next few available days:\n\n${daysText}\n\nPlease choose a number (1-${nextDays.length}) or tell me a specific date you prefer.`)
    
    setUserData(prev => ({ ...prev, availableDays: nextDays }))
    setCurrentStep('asking_specific_date')
  }

  const handleSpecificDateInput = async (input) => {
    const { availableDays } = userData
    
    const dayNumber = parseInt(input)
    if (dayNumber && availableDays && dayNumber >= 1 && dayNumber <= availableDays.length) {
      const selectedDay = availableDays[dayNumber - 1]
      setUserData(prev => ({ ...prev, date: selectedDay.dateStr }))
      await checkAvailability(selectedDay.dateStr)
      return
    }

    try {
      let appointmentDate
      const today = new Date()
      
      if (input.includes('/') || input.includes('-')) {
        appointmentDate = new Date(input)
      } else {
        if (input.toLowerCase().includes('tomorrow')) {
          appointmentDate = new Date(today)
          appointmentDate.setDate(today.getDate() + 1)
        } else if (input.toLowerCase().includes('today')) {
          await checkTodayAvailability()
          return
        } else {
          appointmentDate = new Date(input + ', ' + today.getFullYear())
        }
      }

      if (isNaN(appointmentDate.getTime())) {
        throw new Error('Invalid date format')
      }

      if (appointmentDate < today) {
        addMessage('Please choose a future date. What date would work for you?')
        return
      }

      const year = appointmentDate.getFullYear()
      const month = String(appointmentDate.getMonth() + 1).padStart(2, '0')
      const day = String(appointmentDate.getDate()).padStart(2, '0')
      const dateStr = `${year}-${month}-${day}`
      
      if (isWeekend(dateStr)) {
        addMessage('We\'re closed on Sundays. Please choose Monday through Saturday for your appointment.')
        return
      }
      
      setUserData(prev => ({ ...prev, date: dateStr }))
      await checkAvailability(dateStr)
      
    } catch (error) {
      console.error('Date parsing error:', error)
      addMessage('I couldn\'t understand that date format. Please try again with formats like:\n• "July 28"\n• "2025-07-28"\n• "Tomorrow"\n\nOr choose from the numbered options above.')
    }
  }

  const checkAvailability = async (dateStr) => {
    setIsLoading(true)
    addMessage('Let me check availability for that date... 🔍')
    
    try {
      const response = await axios.get(`/api/available-slots?date=${dateStr}`)
      
      if (response.data.success && response.data.available_slots.length > 0) {
        setAvailableSlots(response.data.available_slots)
        
        const formattedDate = formatDateSafe(dateStr)
        
        const slotsText = response.data.available_slots
          .slice(0, 6)
          .map((slot, index) => `${index + 1}. ${slot.formatted_time}`)
          .join('\n')
        
        addMessage(`Great! I found available time slots for ${formattedDate}:\n\n${slotsText}\n\nPlease tell me the number (1-${Math.min(6, response.data.available_slots.length)}) or specific time you prefer.`)
        setCurrentStep('slot_selection')
      } else {
        addMessage('Sorry, no appointments are available on that date. 😔\n\nWould you like to try another date?')
        await showNextFewDaysAvailability()
      }
    } catch (error) {
      console.error('Availability check error:', error)
      
      if (error.response && error.response.status === 404) {
        addMessage('Sorry, I couldn\'t check availability right now. Let me ask for your preferred time manually.\n\nWhat time would you prefer? Our hours are 9:00 AM to 7:00 PM.\n\nPlease specify like "11:00 AM" or "14:30"')
        setCurrentStep('asking_time')
      } else {
        addMessage('Sorry, I couldn\'t connect to our booking system. Please try again or call us directly at (555) 123-4567.')
        setCurrentStep('main_menu')
      }
    } finally {
      setIsLoading(false)
    }
  }

  // FIXED: Completely rewritten slot selection to prevent time conversion bugs
  const handleSlotSelection = async (input) => {
    const slotNumber = parseInt(input)
    let selectedSlot

    console.log(`🎯 Slot selection input: "${input}", parsed number: ${slotNumber}`)
    console.log(`📋 Available slots:`, availableSlots.map(s => ({ formatted: s.formatted_time, time24: s.time_24h })))

    if (slotNumber && slotNumber >= 1 && slotNumber <= availableSlots.length) {
      // User selected by number
      selectedSlot = availableSlots[slotNumber - 1]
      console.log(`✅ Selected slot by number: ${JSON.stringify(selectedSlot)}`)
    } else {
      // User typed a time - find exact match
      const lowerInput = input.toLowerCase().trim()
      
      selectedSlot = availableSlots.find(slot => {
        const slotTime = slot.formatted_time.toLowerCase()
        
        // Direct match with formatted time
        if (slotTime === lowerInput) return true
        
        // Partial match
        if (slotTime.includes(lowerInput)) return true
        
        // Try to match with 24-hour format if available
        if (slot.time_24h && slot.time_24h === input) return true
        
        return false
      })
      
      console.log(`🔍 Selected slot by text: ${selectedSlot ? JSON.stringify(selectedSlot) : 'Not found'}`)
    }

    if (selectedSlot) {
      // FIXED: Use the exact formatted time and convert reliably
      const timeDisplay = selectedSlot.formatted_time
      let timeStr
      
      // Use the 24-hour format if available, otherwise convert
      if (selectedSlot.time_24h) {
        timeStr = selectedSlot.time_24h
      } else {
        timeStr = convertTo24Hour(selectedSlot.formatted_time)
      }
      
      console.log(`🕐 Final time assignment: display="${timeDisplay}", backend="${timeStr}"`)
      
      setUserData(prev => ({ 
        ...prev, 
        time: timeStr,
        timeDisplay: timeDisplay
      }))
      
      addMessage(`Perfect! I've reserved ${timeDisplay} for you. ⏰\n\nNow I need your phone number for confirmation.`)
      setCurrentStep('asking_phone')
    } else {
      const availableOptions = availableSlots.slice(0, 6).map((slot, index) => 
        `${index + 1}. ${slot.formatted_time}`
      ).join('\n')
      
      addMessage(`I couldn't find that time slot. Please choose from:\n\n${availableOptions}\n\nSelect a number (1-6) or type the exact time.`)
    }
  }

  const handleTimeInput = async (input) => {
    try {
      const timeRegex = /(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm)?/
      const match = input.match(timeRegex)
      
      if (match) {
        let hour = parseInt(match[1])
        let minute = parseInt(match[2] || '0')
        const period = match[3]?.toUpperCase()
        
        if (period === 'PM' && hour !== 12) hour += 12
        if (period === 'AM' && hour === 12) hour = 0
        
        if (hour >= 9 && hour < 19) {
          const timeStr = `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`
          setUserData(prev => ({ 
            ...prev, 
            time: timeStr,
            timeDisplay: input
          }))
          addMessage(`Great! I've noted ${input} for your appointment. ⏰\n\nNow I need your phone number for confirmation.`)
          setCurrentStep('asking_phone')
        } else {
          addMessage('Please choose a time between 9:00 AM and 7:00 PM.')
        }
      } else {
        addMessage('Please provide a valid time format like "2:30 PM" or "14:30".')
      }
    } catch (error) {
      addMessage('I couldn\'t understand that time. Please try again with format like "2:30 PM".')
    }
  }

  const confirmAndBookAppointment = async () => {
    const { name, service, date, time, timeDisplay, phone, email } = userData
    
    const formattedDate = formatDateSafe(date)
    const displayTime = timeDisplay || time || 'Time not selected'
    
    addMessage(`Perfect! Let me confirm your appointment details:\n\n👤 Name: ${name}\n🦷 Service: ${service}\n📅 Date: ${formattedDate}\n⏰ Time: ${displayTime}\n📞 Phone: ${phone}${email ? `\n📧 Email: ${email}` : ''}\n\nShall I book this appointment for you? (Yes/No)`)
    setCurrentStep('final_confirmation')
  }

  const handleFinalConfirmation = async (input) => {
    const response = input.toLowerCase()
    if (response.includes('yes') || response.includes('confirm') || response.includes('book')) {
      await bookAppointment()
    } else if (response.includes('no') || response.includes('cancel')) {
      addMessage('No problem! Would you like to:\n\n📅 Choose a different date/time\n🏠 Start over\n📞 Contact us directly')
      setCurrentStep('main_menu')
    } else {
      addMessage('Please reply with "Yes" to confirm the booking or "No" to cancel.')
    }
  }

  const bookAppointment = async () => {
    setIsLoading(true)
    addMessage('Booking your appointment... 📅')
    
    try {
      // FIXED: Use the exact time format without additional conversion
      let appointmentTime = userData.time
      
      // Validate time format
      if (!/^\d{2}:\d{2}$/.test(appointmentTime)) {
        console.warn(`Invalid time format: ${appointmentTime}, converting...`)
        appointmentTime = convertTo24Hour(userData.timeDisplay || appointmentTime)
      }
      
      console.log('🚀 Final booking data:', {
        patient_name: userData.name,
        patient_phone: userData.phone,
        patient_email: userData.email || '',
        appointment_date: userData.date,
        appointment_time: appointmentTime,
        appointment_type: userData.service
      })

      const response = await axios.post('/api/book-appointment', {
        patient_name: userData.name,
        patient_phone: userData.phone,
        patient_email: userData.email || '',
        appointment_date: userData.date,
        appointment_time: appointmentTime,
        appointment_type: userData.service,
        notes: `Booked via AI Chatbot`
      })

      if (response.data.success) {
        const formattedDate = formatDateSafe(userData.date)
        const displayTime = userData.timeDisplay || appointmentTime
        
        addMessage(`🎉 Excellent! Your appointment has been successfully booked!\n\n✅ Confirmation Details:\n📅 ${formattedDate} at ${displayTime}\n🦷 ${userData.service}\n\nYou'll receive a confirmation call/email shortly. Is there anything else I can help you with?`)
        
        setCurrentStep('main_menu')
        setUserData({ name: userData.name })
      } else {
        addMessage(`Sorry, there was an issue booking your appointment: ${response.data.message}\n\nWould you like to try a different time slot?`)
        
        if (response.data.alternatives && response.data.alternatives.length > 0) {
          const altSlotsText = response.data.alternatives
            .slice(0, 5)
            .map((slot, index) => `${index + 1}. ${slot.formatted_time}`)
            .join('\n')
          
          addMessage(`Here are alternative time slots available:\n\n${altSlotsText}\n\nWould you like to select one of these?`)
          setAvailableSlots(response.data.alternatives)
          setCurrentStep('slot_selection')
        } else {
          await showNextFewDaysAvailability()
        }
      }
    } catch (error) {
      console.error('Booking error:', error)
      let errorMessage = 'Sorry, I encountered an error while booking.'
      
      if (error.response) {
        errorMessage += ` Server responded with: ${error.response.data.message || 'Unknown error'}`
      } else if (error.request) {
        errorMessage += ' Could not connect to booking system. Please check if the backend is running.'
      } else {
        errorMessage += ` Error: ${error.message}`
      }
      
      addMessage(`${errorMessage}\n\nPlease try again or call us directly at (555) 123-4567.`)
      setCurrentStep('main_menu')
    } finally {
      setIsLoading(false)
    }
  }

  const quickActions = [
    { text: '🏠 Start Over', action: () => {
      setCurrentStep('main_menu')
      addMessage(`How can I assist you today, ${userData.name || 'there'}?\n\n🦷 Learn about our Services\n🕒 Check our Hours\n📞 Get Contact Info\n📅 Book an Appointment`)
    }},
    { text: '🚨 Emergency', action: () => {
      addMessage('🚨 For dental emergencies:\n\n📞 Call: (555) 123-4567\n🌙 After hours: (555) 999-HELP\n\nFor immediate care, please call us directly.')
    }},
    { text: '📞 Call Us', action: () => {
      addMessage('📞 Contact Information:\n\n📱 Phone: (555) 123-4567\n📧 Email: contact@brightsmile.com\n📍 Address: 123 Main St, City, State 12345')
    }}
  ]

  return (
    <div className="flex flex-col h-screen">
      {/* Chat Header */}
      <div className="bg-dental-blue text-white p-4 flex items-center space-x-3 flex-shrink-0">
        <Bot className="w-6 h-6" />
        <div>
          <h3 className="font-semibold">AI Dental Assistant</h3>
          <p className="text-dental-light text-sm">Online now • {userData.name && `Chatting with ${userData.name}`}</p>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-gray-50 min-h-0">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex items-start space-x-3 ${
              message.type === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {message.type === 'bot' && (
              <div className="bg-dental-blue p-2 rounded-full flex-shrink-0">
                <Bot className="w-4 h-4 text-white" />
              </div>
            )}
            
            <div className={`chat-bubble ${message.type} max-w-md`}>
              <p className="whitespace-pre-line">{message.content}</p>
              <p className={`text-xs mt-2 ${
                message.type === 'user' ? 'text-dental-light' : 'text-gray-500'
              }`}>
                {message.timestamp.toLocaleTimeString()}
              </p>
            </div>

            {message.type === 'user' && (
              <div className="bg-gray-600 p-2 rounded-full flex-shrink-0">
                <User className="w-4 h-4 text-white" />
              </div>
            )}
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex items-start space-x-3">
            <div className="bg-dental-blue p-2 rounded-full flex-shrink-0">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="bg-gray-100 rounded-2xl p-4">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 p-4 flex-shrink-0">
        <div className="flex space-x-2 mb-3">
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleUserInput(userInput)}
            placeholder="Type your message..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-dental-blue focus:border-dental-blue"
            disabled={isLoading}
          />
          <button
            onClick={() => handleUserInput(userInput)}
            disabled={isLoading || !userInput.trim()}
            className="bg-dental-blue text-white px-4 py-2 rounded-lg hover:bg-dental-dark disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>

        {/* Quick Actions */}
        <div className="flex justify-center space-x-4 text-sm">
          {quickActions.map((action, index) => (
            <button
              key={index}
              onClick={action.action}
              className="text-dental-blue hover:text-dental-dark"
            >
              {action.text}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default ChatBot;
