import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, Bot, User, Mail, Sparkles, Loader2 } from 'lucide-react'
import { emailsApi } from '../services/api'
import clsx from 'clsx'

const SUGGESTED_QUERIES = [
  "Show me urgent emails from today",
  "What emails about meetings do I have?",
  "Summarize my emails about project deadlines",
  "Any emails from my manager?",
  "Show me unread newsletters",
]

function ChatInterface() {
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    
    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const response = await emailsApi.chat({
        query: userMessage,
        conversation_history: messages.slice(-10), // Keep last 10 messages for context
      })

      // Add assistant response
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.data.answer,
        emails: response.data.relevant_emails,
      }])
    } catch (error) {
      console.error('Chat error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Sorry, I encountered an error while processing your request. Please try again.",
        isError: true,
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleSuggestionClick = (query) => {
    setInput(query)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 bg-white">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-primary-600" />
          Chat with Your Inbox
        </h1>
        <p className="text-gray-600 mt-1">
          Ask questions about your emails in natural language
        </p>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="bg-primary-100 p-4 rounded-full mb-4">
              <Bot className="h-12 w-12 text-primary-600" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              How can I help you today?
            </h2>
            <p className="text-gray-600 mb-6 max-w-md">
              I can help you search, summarize, and understand your emails. 
              Try asking me something!
            </p>
            
            {/* Suggested Queries */}
            <div className="flex flex-wrap gap-2 justify-center max-w-2xl">
              {SUGGESTED_QUERIES.map((query, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(query)}
                  className="px-4 py-2 bg-white border border-gray-200 rounded-full text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors"
                >
                  {query}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <MessageBubble
                key={index}
                message={message}
                onEmailClick={(id) => navigate(`/emails/${id}`)}
              />
            ))}
            
            {loading && (
              <div className="flex items-start gap-3">
                <div className="bg-primary-100 p-2 rounded-full">
                  <Bot className="h-5 w-5 text-primary-600" />
                </div>
                <div className="bg-gray-100 rounded-2xl rounded-tl-none px-4 py-3">
                  <Loader2 className="h-5 w-5 animate-spin text-gray-500" />
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="p-6 border-t border-gray-200 bg-white">
        <div className="flex items-end gap-4">
          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your emails..."
              rows={1}
              className="input resize-none pr-12"
              style={{ minHeight: '48px', maxHeight: '120px' }}
            />
          </div>
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="btn-primary p-3"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}

function MessageBubble({ message, onEmailClick }) {
  const isUser = message.role === 'user'

  return (
    <div className={clsx('flex items-start gap-3', isUser && 'flex-row-reverse')}>
      {/* Avatar */}
      <div className={clsx(
        'p-2 rounded-full flex-shrink-0',
        isUser ? 'bg-gray-200' : 'bg-primary-100'
      )}>
        {isUser ? (
          <User className="h-5 w-5 text-gray-600" />
        ) : (
          <Bot className="h-5 w-5 text-primary-600" />
        )}
      </div>

      {/* Content */}
      <div className={clsx('flex-1 max-w-2xl', isUser && 'text-right')}>
        <div className={clsx(
          'inline-block rounded-2xl px-4 py-3',
          isUser 
            ? 'bg-primary-600 text-white rounded-tr-none' 
            : 'bg-gray-100 text-gray-900 rounded-tl-none',
          message.isError && 'bg-red-50 text-red-700'
        )}>
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* Relevant Emails */}
        {message.emails && message.emails.length > 0 && (
          <div className="mt-3 space-y-2">
            <p className="text-sm text-gray-500">Related emails:</p>
            {message.emails.map((email) => (
              <div
                key={email.id}
                onClick={() => onEmailClick(email.id)}
                className="bg-white border border-gray-200 rounded-lg p-3 cursor-pointer hover:shadow-md transition-shadow text-left"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Mail className="h-4 w-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-900 truncate">
                    {email.subject || '(No Subject)'}
                  </span>
                </div>
                <p className="text-xs text-gray-500 truncate">
                  From: {email.sender}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatInterface
