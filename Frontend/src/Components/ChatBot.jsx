// // components/ChatBot.jsx
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
  const [showButtons, setShowButtons] = useState(false)
  const [buttonOptions, setButtonOptions] = useState([])
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  // FIXED: Maintain input focus
  useEffect(() => {
    if (inputRef.current && !isLoading) {
      inputRef.current.focus()
    }
  }, [isLoading, currentStep])

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

  // FIXED: Phone number validation
  const validatePhoneNumber = (phone) => {
    if (!phone) return false
    
    // Remove spaces, dashes, and parentheses
    const cleanPhone = phone.replace(/[\s\-\(\)]+/g, '')
    
    // Pakistan phone number patterns
    const patterns = [
      /^\+92[0-9]{10}$/,          // +92xxxxxxxxxx
      /^92[0-9]{10}$/,            // 92xxxxxxxxxx  
      /^0[0-9]{10}$/,             // 0xxxxxxxxxx
      /^[0-9]{11}$/,              // xxxxxxxxxxx
    ]
    
    for (const pattern of patterns) {
      if (pattern.test(cleanPhone)) {
        return true
      }
    }
    
    // Also accept basic 10+ digit numbers
    if (cleanPhone.length >= 10 && /^\d+$/.test(cleanPhone)) {
      return true
    }
        
    return false
  }

  // FIXED: Email validation
  const validateEmail = (email) => {
    if (!email) return true // Email is optional
    const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
    return pattern.test(email)
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

  // FIXED: Handle button clicks
  const handleButtonClick = (value) => {
    setShowButtons(false)
    setButtonOptions([])
    
    addMessage(value, 'user')
    addTypingMessage()

    setTimeout(async () => {
      await processUserResponse(value)
    }, 1000)
  }

  const handleUserInput = async (input) => {
    if (!input.trim()) return

    setShowButtons(false)
    setButtonOptions([])
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
        // FIXED: Don't show buttons immediately, wait for user to see personalized message
        addMessage(`Nice to meet you, ${input}! 😊\n\nHow can I assist you today?`)
        
        // FIXED: Delay showing buttons to let user read the personalized greeting
        setTimeout(() => {
          setShowButtons(true)
          setButtonOptions([
            { text: '🦷 Learn about our Services', value: 'services' },
            { text: '🕒 Check our Hours', value: 'hours' },
            { text: '📞 Get Contact Info', value: 'contact' },
            { text: '🚨 Emergency Information', value: 'emergency' },
            { text: '📅 Book an Appointment', value: 'book' }
          ])
        }, 2000) // 2 second delay
        
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
        // FIXED: Validate phone number
        if (!validatePhoneNumber(input)) {
          addMessage('Please provide a valid phone number. Examples:\n• +92-321-1234567\n• 0321-1234567\n• 03211234567')
          return
        }
        
        setUserData(prev => ({ ...prev, phone: input }))
        addMessage('"Great! What’s the best email to send your appointment details?" ')
        setCurrentStep('asking_email')
        break

      case 'asking_email':
        if (input.toLowerCase() !== 'skip') {
          // FIXED: Validate email format
          if (!validateEmail(input)) {
            addMessage('Please provide a valid email address or type "skip" to continue without email.')
            return
          }
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
        addMessage(`How can I assist you today, ${userData.name}?`)
        setShowButtons(true)
        setButtonOptions([
          { text: '🦷 Learn about our Services', value: 'services' },
          { text: '🕒 Check our Hours', value: 'hours' },
          { text: '📞 Get Contact Info', value: 'contact' },
          { text: '📅 Book an Appointment', value: 'book' }
        ])
        setCurrentStep('main_menu')
    }
  }

  const handleMainMenuChoice = async (input) => {
    const lowerInput = input.toLowerCase()

    if (lowerInput.includes('service') || lowerInput === 'services' || lowerInput.includes('dental')) {
      addMessage('Great! We offer comprehensive dental services:')
      
      setShowButtons(true)
      setButtonOptions([
        { text: '✨ Cosmetic Dentistry', value: 'cosmetic' },
        { text: '🛡️ General Dentistry', value: 'general' },
        { text: '🔧 Restorative Dentistry', value: 'restorative' },
        { text: '📅 Book an Appointment', value: 'book appointment' }
      ])
      setCurrentStep('service_selection')
    } else if (lowerInput.includes('hour') || lowerInput === 'hours' || lowerInput.includes('time')) {
      addMessage('🕒 Our office hours are:\n\n📅 Monday - Friday: 9:00 AM - 7:00 PM\n📅 Saturday: 9:00 AM - 7:00 PM\n📅 Sunday: Closed\n\nWould you like to book an appointment?')
      
      setShowButtons(true)
      setButtonOptions([
        { text: '📅 Book an Appointment', value: 'book appointment' },
        { text: '🏠 Back to Main Menu', value: 'main menu' }
      ])
      setCurrentStep('main_menu')
    } else if (lowerInput.includes('contact') || lowerInput === 'contact' || lowerInput.includes('phone') || lowerInput.includes('address')) {
      addMessage('📞 Contact Information:\n\n📱 Phone: (555) 123-4567\n📧 Email: contact@brightsmile.com\n📍 Address: 123 Main St, City, State 12345\n\nWould you like to schedule an appointment?')
      
      setShowButtons(true)
      setButtonOptions([
        { text: '📅 Book an Appointment', value: 'book appointment' },
        { text: '🏠 Back to Main Menu', value: 'main menu' }
      ])
      setCurrentStep('main_menu')
    } else if (lowerInput.includes('emergency') || lowerInput === 'emergency') {
      addMessage('🚨 For dental emergencies:\n\n📞 Call: (555) 123-4567\n🌙 After hours: (555) 999-HELP\n\nFor immediate care, please call us directly.\n\nWould you like to schedule a regular appointment?')
      
      setShowButtons(true)
      setButtonOptions([
        { text: '📅 Book an Appointment', value: 'book appointment' },
        { text: '🏠 Back to Main Menu', value: 'main menu' }
      ])
      setCurrentStep('main_menu')
    } else if (lowerInput.includes('book') || lowerInput === 'book' || lowerInput.includes('appointment') || lowerInput.includes('schedule')) {
      addMessage('Excellent! I\'d be happy to help you book an appointment. 📅\n\nWhat type of service do you need?')
      
      setShowButtons(true)
      setButtonOptions([
        { text: '✨ Cosmetic Dentistry', value: 'cosmetic' },
        { text: '🛡️ General Dentistry', value: 'general' },
        { text: '🔧 Restorative Dentistry', value: 'restorative' }
      ])
      setCurrentStep('service_selection')
    } else if (lowerInput.includes('main menu') || lowerInput === 'main menu') {
      addMessage(`How can I assist you today, ${userData.name}?`)
      
      setShowButtons(true)
      setButtonOptions([
        { text: '🦷 Learn about our Services', value: 'services' },
        { text: '🕒 Check our Hours', value: 'hours' },
        { text: '📞 Get Contact Info', value: 'contact' },
        { text: '📅 Book an Appointment', value: 'book' }
      ])
    } else {
      addMessage('I understand you\'re interested in our dental services. Let me help you with:')
      
      setShowButtons(true)
      setButtonOptions([
        { text: '🦷 Learn about our Services', value: 'services' },
        { text: '🕒 Check our Hours', value: 'hours' },
        { text: '📞 Get Contact Info', value: 'contact' },
        { text: '📅 Book an Appointment', value: 'book' }
      ])
    }
  }

  const handleServiceSelection = async (input) => {
    const lowerInput = input.toLowerCase()
    let selectedService = ''

    if (lowerInput.includes('cosmetic') || lowerInput === 'cosmetic' || lowerInput.includes('whitening') || lowerInput.includes('veneer')) {
      selectedService = 'Cosmetic Dentistry'
    } else if (lowerInput.includes('general') || lowerInput === 'general' || lowerInput.includes('cleaning') || lowerInput.includes('checkup')) {
      selectedService = 'General Dentistry'
    } else if (lowerInput.includes('restorative') || lowerInput === 'restorative' || lowerInput.includes('filling') || lowerInput.includes('crown') || lowerInput.includes('implant')) {
      selectedService = 'Restorative Dentistry'
    } else if (lowerInput.includes('book') || lowerInput.includes('appointment')) {
      selectedService = 'General Dentistry'
    } else {
      addMessage('I\'d be happy to help! Could you please specify which service you\'re interested in?')
      
      setShowButtons(true)
      setButtonOptions([
        { text: '✨ Cosmetic Dentistry', value: 'cosmetic' },
        { text: '🛡️ General Dentistry', value: 'general' },
        { text: '🔧 Restorative Dentistry', value: 'restorative' }
      ])
      return
    }

    setUserData(prev => ({ ...prev, service: selectedService }))
    addMessage(`Perfect! ${selectedService} is one of our specialties. 🌟\n\nWhen would you like to schedule your appointment?`)
    
    setShowButtons(true)
    setButtonOptions([
      { text: '📅 Today', value: 'today' },
      { text: '📅 Tomorrow', value: 'tomorrow' },
      { text: '📅 This Week', value: 'this week' },
      { text: '📅 Choose Specific Date', value: 'specific date' }
    ])
    setCurrentStep('asking_date_preference')
  }

  const handleDatePreference = async (input) => {
    const lowerInput = input.toLowerCase()

    if (lowerInput.includes('today') || lowerInput === 'today') {
      await checkTodayAvailability()
    } else if (lowerInput.includes('tomorrow') || lowerInput === 'tomorrow') {
      await checkSpecificDateAvailability('tomorrow')
    } else if (lowerInput.includes('this week') || lowerInput === 'this week') {
      await showNextFewDaysAvailability()
    } else if (lowerInput.includes('specific') || lowerInput === 'specific date') {
      addMessage('Please tell me your preferred date. You can say:\n• "Monday" or "Friday"\n• "July 28" or "28th July"\n• "Next week"\n• "2025-07-28"')
      setCurrentStep('asking_specific_date')
    } else {
      await handleSpecificDateInput(input)
    }
  }

  const checkSpecificDateAvailability = async (dateInput) => {
    setIsLoading(true)
    addMessage(`Let me check availability for ${dateInput}... 🔍`)
    
    try {
      const response = await axios.get(`/api/available-slots?date=${dateInput}`)
      
      if (response.data.success && response.data.available_slots.length > 0) {
        console.log(`📅 Found ${response.data.available_slots.length} slots for ${dateInput}`)
        
        setAvailableSlots(response.data.available_slots)
        const parsedDate = response.data.date || dateInput
        setUserData(prev => ({ ...prev, date: parsedDate, originalDateInput: dateInput }))
        
        const slotsText = response.data.available_slots
          .slice(0, 6)
          .map((slot, index) => `${index + 1}. ${slot.formatted_time}`)
          .join('\n')
        
        addMessage(`Great! I found available time slots for ${parsedDate}:\n\n${slotsText}`)
        
        setShowButtons(true)
        setButtonOptions(
          response.data.available_slots.slice(0, 6).map((slot, index) => ({
            text: `${index + 1}. ${slot.formatted_time}`,
            value: slot.formatted_time
          }))
        )
        setCurrentStep('slot_selection')
      } else {
        addMessage(`Sorry, no appointments are available for ${dateInput}. 😔\n\nWould you like to see availability for other days?`)
        await showNextFewDaysAvailability()
      }
    } catch (error) {
      console.error('Availability check error:', error)
      addMessage(`I couldn't check availability for ${dateInput}. Let me show you the next few days instead.`)
      await showNextFewDaysAvailability()
    } finally {
      setIsLoading(false)
    }
  }

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
        
        setAvailableSlots(response.data.available_slots)
        setUserData(prev => ({ ...prev, date: dateStr }))
        
        const slotsText = response.data.available_slots
          .slice(0, 6)
          .map((slot, index) => `${index + 1}. ${slot.formatted_time}`)
          .join('\n')
        
        addMessage(`Great! I found available time slots for today:\n\n${slotsText}`)
        
        setShowButtons(true)
        setButtonOptions(
          response.data.available_slots.slice(0, 6).map((slot, index) => ({
            text: `${index + 1}. ${slot.formatted_time}`,
            value: slot.formatted_time
          }))
        )
        setCurrentStep('slot_selection')
      } else {
        addMessage('Sorry, no appointments are available . 😔\n\nWould you like to see availability for  the next few days?')
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
    setIsLoading(true)
    addMessage('Let me show you availability for the next few days... 📅')
    
    try {
      const response = await axios.get('/api/next-days-availability?days=3')
      
      if (response.data.success && Object.keys(response.data.availability).length > 0) {
        const availability = response.data.availability
        const daysArray = Object.entries(availability)
        
        const daysText = daysArray
          .map(([dateStr, dayInfo], index) => `${index + 1}. ${dayInfo.day}, ${dayInfo.date}`)
          .join('\n')
        
        addMessage(`Here are the next few available days:\n\n${daysText}`)
        
        setShowButtons(true)
        setButtonOptions(
          daysArray.map(([dateStr, dayInfo], index) => ({
            text: `${index + 1}. ${dayInfo.day}, ${dayInfo.date}`,
            value: dateStr
          }))
        )
        
        setUserData(prev => ({ ...prev, availableDays: daysArray }))
        setCurrentStep('asking_specific_date')
      } else {
        addMessage('I couldn\'t find available appointments in the next few days. Please call us directly at (555) 123-4567 to schedule.')
        setCurrentStep('main_menu')
      }
    } catch (error) {
      console.error('Next days availability error:', error)
      addMessage('I couldn\'t retrieve availability information. Please try again or call us at (555) 123-4567.')
      setCurrentStep('main_menu')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSpecificDateInput = async (input) => {
    const { availableDays } = userData
    
    if (availableDays) {
      const selectedDay = availableDays.find(([dateStr]) => dateStr === input)
      if (selectedDay) {
        const [dateStr, dayInfo] = selectedDay
        setUserData(prev => ({ ...prev, date: dateStr }))
        await checkAvailability(dateStr)
        return
      }
    }

    const dayNumber = parseInt(input)
    if (dayNumber && availableDays && dayNumber >= 1 && dayNumber <= availableDays.length) {
      const [dateStr] = availableDays[dayNumber - 1]
      setUserData(prev => ({ ...prev, date: dateStr }))
      await checkAvailability(dateStr)
      return
    }

    setIsLoading(true)
    addMessage(`Let me check availability for "${input}"... 🔍`)
    
    try {
      const response = await axios.get(`/api/available-slots?date=${encodeURIComponent(input)}`)
      
      if (response.data.success && response.data.available_slots.length > 0) {
        setAvailableSlots(response.data.available_slots)
        const parsedDate = response.data.date || input
        setUserData(prev => ({ ...prev, date: parsedDate, originalDateInput: input }))
        
        const slotsText = response.data.available_slots
          .slice(0, 6)
          .map((slot, index) => `${index + 1}. ${slot.formatted_time}`)
          .join('\n')
        
        addMessage(`Great! I found available time slots for ${parsedDate}:\n\n${slotsText}`)
        
        setShowButtons(true)
        setButtonOptions(
          response.data.available_slots.slice(0, 6).map((slot, index) => ({
            text: `${index + 1}. ${slot.formatted_time}`,
            value: slot.formatted_time
          }))
        )
        setCurrentStep('slot_selection')
      } else {
        addMessage(`Sorry, no appointments are available for "${input}". 😔\n\n${response.data.message || 'Please try a different date.'}`)
        await showNextFewDaysAvailability()
      }
    } catch (error) {
      console.error('Date parsing/availability error:', error)
      
      if (error.response?.status === 400) {
        addMessage(`I couldn't understand "${input}". Please try formats like:\n• "Monday" or "Friday"\n• "Tomorrow"\n• "July 28"\n• "2025-07-28"`)
      } else {
        addMessage('I couldn\'t check availability right now. Please try again or call us at (555) 123-4567.')
      }
    } finally {
      setIsLoading(false)
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
        
        addMessage(`Great! I found available time slots for ${formattedDate}:\n\n${slotsText}`)
        
        setShowButtons(true)
        setButtonOptions(
          response.data.available_slots.slice(0, 6).map((slot, index) => ({
            text: `${index + 1}. ${slot.formatted_time}`,
            value: slot.formatted_time
          }))
        )
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

  const handleSlotSelection = async (input) => {
    let selectedSlot

    // Handle direct button clicks (formatted time)
    selectedSlot = availableSlots.find(slot => slot.formatted_time === input)
    
    if (!selectedSlot) {
      // Handle numbered selections
      const slotNumber = parseInt(input)
      if (slotNumber && slotNumber >= 1 && slotNumber <= availableSlots.length) {
        selectedSlot = availableSlots[slotNumber - 1]
      }
    }

    if (!selectedSlot) {
      // Try text matching
      const lowerInput = input.toLowerCase().trim()
      selectedSlot = availableSlots.find(slot => {
        const slotTime = slot.formatted_time.toLowerCase()
        return slotTime === lowerInput || slotTime.includes(lowerInput)
      })
    }

    if (selectedSlot) {
      const timeDisplay = selectedSlot.formatted_time
      // FIXED: Use the exact time string from backend without conversion
      const timeStr = selectedSlot.time_24h || selectedSlot.formatted_time
      
      console.log(`🕐 Selected slot: display="${timeDisplay}", backend="${timeStr}"`)
      
      setUserData(prev => ({ 
        ...prev, 
        time: timeStr,
        timeDisplay: timeDisplay,
        // FIXED: Store the original slot data to preserve exact timing
        selectedSlot: selectedSlot
      }))
      
      addMessage(`Perfect! I've reserved ${timeDisplay} for you. ⏰\n\nNow I need your phone number for confirmation.`)
      setCurrentStep('asking_phone')
    } else {
      addMessage(`I couldn't find that time slot. Please choose from the available options above or try again.`)
      
      setShowButtons(true)
      setButtonOptions(
        availableSlots.slice(0, 6).map((slot, index) => ({
          text: `${index + 1}. ${slot.formatted_time}`,
          value: slot.formatted_time
        }))
      )
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
    
    addMessage(`Perfect! Let me confirm your appointment details:\n\n👤 Name: ${name}\n🦷 Service: ${service}\n📅 Date: ${formattedDate}\n⏰ Time: ${displayTime}\n📞 Phone: ${phone}${email ? `\n📧 Email: ${email}` : ''}`)
    
    setShowButtons(true)
    setButtonOptions([
      { text: '✅ Yes, Book This Appointment', value: 'yes' },
      { text: '❌ No, Let Me Change Something', value: 'no' }
    ])
    setCurrentStep('final_confirmation')
  }

  const handleFinalConfirmation = async (input) => {
    const response = input.toLowerCase()
    if (response.includes('yes') || response === 'yes' || response.includes('confirm') || response.includes('book')) {
      await bookAppointment()
    } else if (response.includes('no') || response === 'no' || response.includes('cancel')) {
      addMessage('No problem! What would you like to change?')
      
      setShowButtons(true)
      setButtonOptions([
        { text: '📅 Choose Different Date/Time', value: 'change date' },
        { text: '🦷 Change Service', value: 'change service' },
        { text: '🏠 Start Over', value: 'start over' }
      ])
      setCurrentStep('main_menu')
    } else {
      addMessage('Please confirm your booking:')
      
      setShowButtons(true)
      setButtonOptions([
        { text: '✅ Yes, Book This Appointment', value: 'yes' },
        { text: '❌ No, Let Me Change Something', value: 'no' }
      ])
    }
  }

  const bookAppointment = async () => {
    setIsLoading(true)
    setShowButtons(false)
    addMessage('Booking your appointment... 📅')
    
    try {
      // FIXED: Preserve exact slot timing to prevent timezone issues
      let appointmentDate = userData.date
      let appointmentTime = userData.time
      
      // CRITICAL FIX: If we have the original slot data, use its exact start_time
      if (userData.selectedSlot && userData.selectedSlot.start_time) {
        // Parse the ISO datetime from the slot
        const slotDateTime = new Date(userData.selectedSlot.start_time)
        appointmentDate = slotDateTime.toISOString().split('T')[0] // YYYY-MM-DD
        appointmentTime = slotDateTime.toTimeString().substr(0, 5) // HH:MM
        
        console.log(`🎯 CRITICAL FIX - Using exact slot timing:`)
        console.log(`  Original slot start_time: ${userData.selectedSlot.start_time}`)
        console.log(`  Extracted date: ${appointmentDate}`)
        console.log(`  Extracted time: ${appointmentTime}`)
      } else {
        // Fallback to manual parsing
        if (!/^\d{4}-\d{2}-\d{2}$/.test(appointmentDate)) {
          const today = new Date()
          const testDate = new Date(appointmentDate)
          if (!isNaN(testDate.getTime())) {
            appointmentDate = testDate.toISOString().split('T')[0]
          } else {
            throw new Error('Invalid date format')
          }
        }
        
        if (!/^\d{2}:\d{2}$/.test(appointmentTime)) {
          console.warn(`Invalid time format: ${appointmentTime}, using fallback`)
          appointmentTime = '09:00'
        }
      }
      
      console.log('🚀 Final booking data:', {
        patient_name: userData.name,
        patient_phone: userData.phone,
        patient_email: userData.email || '',
        appointment_date: appointmentDate,
        appointment_time: appointmentTime,
        appointment_type: userData.service
      })

      const response = await axios.post('/api/book-appointment', {
        patient_name: userData.name,
        patient_phone: userData.phone,
        patient_email: userData.email || '',
        appointment_date: appointmentDate,
        appointment_time: appointmentTime,
        appointment_type: userData.service,
        notes: `Booked via AI Chatbot`
      })

      if (response.data.success) {
        const formattedDate = formatDateSafe(appointmentDate)
        const displayTime = userData.timeDisplay || appointmentTime
        
        addMessage(`🎉 Excellent! Your appointment has been successfully booked!\n\n✅ Confirmation Details:\n📅 ${formattedDate} at ${displayTime}\n🦷 ${userData.service}\n\nYou'll receive a confirmation call/email shortly. Is there anything else I can help you with?`)
        
        setShowButtons(true)
        setButtonOptions([
          { text: '📅 Book Another Appointment', value: 'book' },
          { text: '🏠 Back to Main Menu', value: 'main menu' },
          { text: '📞 Contact Us', value: 'contact' }
        ])
        
        setCurrentStep('main_menu')
        setUserData({ name: userData.name })
      } else {
        addMessage(`Sorry, there was an issue booking your appointment: ${response.data.message}`)
        
        if (response.data.alternatives && response.data.alternatives.length > 0) {
          const altSlotsText = response.data.alternatives
            .slice(0, 5)
            .map((slot, index) => `${index + 1}. ${slot.formatted_time}`)
            .join('\n')
          
          addMessage(`Here are alternative time slots available:\n\n${altSlotsText}`)
          
          setShowButtons(true)
          setButtonOptions(
            response.data.alternatives.slice(0, 5).map((slot, index) => ({
              text: `${index + 1}. ${slot.formatted_time}`,
              value: slot.formatted_time
            }))
          )
          
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
        errorMessage += ` ${error.response.data.message || 'Unknown error'}`
      } else if (error.request) {
        errorMessage += ' Could not connect to booking system. Please check if the backend is running.'
      } else {
        errorMessage += ` Error: ${error.message}`
      }
      
      addMessage(`${errorMessage}\n\nPlease try again or call us directly at (555) 123-4567.`)
      
      setShowButtons(true)
      setButtonOptions([
        { text: '🔄 Try Again', value: 'book' },
        { text: '📞 Call Us Instead', value: 'contact' },
        { text: '🏠 Main Menu', value: 'main menu' }
      ])
      setCurrentStep('main_menu')
    } finally {
      setIsLoading(false)
    }
  }

  // Enhanced quick actions
  const quickActions = [
    { text: '🏠 Start Over', action: () => {
      setCurrentStep('main_menu')
      setShowButtons(true)
      setButtonOptions([
        { text: '🦷 Learn about our Services', value: 'services' },
        { text: '🕒 Check our Hours', value: 'hours' },
        { text: '📞 Get Contact Info', value: 'contact' },
        { text: '📅 Book an Appointment', value: 'book' }
      ])
      addMessage(`How can I assist you today, ${userData.name || 'there'}?`)
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

        {/* Clickable Button Options */}
        {showButtons && buttonOptions.length > 0 && (
          <div className="flex flex-col space-y-2 max-w-md">
            {buttonOptions.map((option, index) => (
              <button
                key={index}
                onClick={() => handleButtonClick(option.value)}
                className="bg-white border border-dental-blue text-dental-blue px-4 py-2 rounded-lg hover:bg-dental-blue hover:text-white transition-colors duration-200 text-left"
                disabled={isLoading}
              >
                {option.text}
              </button>
            ))}
          </div>
        )}

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

      {/* Input Area with maintained focus */}
      <div className="bg-white border-t border-gray-200 p-4 flex-shrink-0">
        <div className="flex space-x-2 mb-3">
          <input
            ref={inputRef}
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleUserInput(userInput)}
            placeholder={showButtons ? "Choose an option above or type your message..." : "Type your message..."}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-dental-blue focus:border-dental-blue"
            disabled={isLoading}
            autoFocus
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
              disabled={isLoading}
            >
              {action.text}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default ChatBot







