import ChatBot from './Components/ChatBot'
import { Smile } from 'lucide-react'

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-dental-light to-white">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center space-x-3">
            <div className="bg-dental-blue p-2 rounded-lg">
              <Smile className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Bright Smile Dental Office</h1>
              <p className="text-sm text-gray-600">AI Receptionist Assistant</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - Full Height Chatbot */}
      <main className="h-[calc(100vh-120px)]">
        <div className="h-full max-w-4xl mx-auto">
          <ChatBot />
        </div>
      </main>
    </div>
  )
}

export default App