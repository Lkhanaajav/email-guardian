import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  ArrowLeft, Mail, Clock, User, Tag, 
  AlertCircle, CheckCircle, ListChecks, Sparkles 
} from 'lucide-react'
import { emailsApi } from '../services/api'
import { format } from 'date-fns'
import clsx from 'clsx'

function EmailSummary() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [email, setEmail] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchEmail()
  }, [id])

  const fetchEmail = async () => {
    try {
      const response = await emailsApi.getById(id)
      setEmail(response.data)
      
      // Mark as read
      if (!response.data.is_read) {
        await emailsApi.markAsRead(id)
      }
    } catch (error) {
      console.error('Failed to fetch email:', error)
    } finally {
      setLoading(false)
    }
  }

  const getUrgencyColor = (urgency) => {
    const colors = {
      urgent: 'text-red-600 bg-red-50 border-red-200',
      normal: 'text-yellow-600 bg-yellow-50 border-yellow-200',
      low: 'text-green-600 bg-green-50 border-green-200',
    }
    return colors[urgency] || colors.normal
  }

  const getCategoryColor = (category) => {
    const colors = {
      work: 'bg-blue-100 text-blue-800',
      personal: 'bg-purple-100 text-purple-800',
      finance: 'bg-green-100 text-green-800',
      newsletter: 'bg-yellow-100 text-yellow-800',
      shopping: 'bg-pink-100 text-pink-800',
      other: 'bg-gray-100 text-gray-800',
    }
    return colors[category] || colors.other
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading email...</p>
        </div>
      </div>
    )
  }

  if (!email) {
    return (
      <div className="p-8">
        <div className="card p-8 text-center">
          <Mail className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Email not found</h3>
          <button
            onClick={() => navigate('/emails')}
            className="btn-primary mt-4"
          >
            Back to Emails
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Back Button */}
      <button
        onClick={() => navigate('/emails')}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="h-5 w-5" />
        Back to Emails
      </button>

      {/* Email Header */}
      <div className="card p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900">
            {email.subject || '(No Subject)'}
          </h1>
          <div className="flex items-center gap-2">
            <span className={clsx('badge', getCategoryColor(email.category))}>
              {email.category}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap gap-6 text-sm text-gray-600">
          <div className="flex items-center gap-2">
            <User className="h-4 w-4" />
            <span>{email.sender}</span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            <span>
              {email.received_at && format(new Date(email.received_at), 'PPpp')}
            </span>
          </div>
        </div>

        {/* Urgency Banner */}
        <div className={clsx(
          'mt-4 p-3 rounded-lg border flex items-center gap-3',
          getUrgencyColor(email.urgency)
        )}>
          {email.urgency === 'urgent' ? (
            <AlertCircle className="h-5 w-5" />
          ) : email.urgency === 'low' ? (
            <CheckCircle className="h-5 w-5" />
          ) : (
            <Tag className="h-5 w-5" />
          )}
          <span className="font-medium capitalize">
            {email.urgency} Priority
          </span>
        </div>
      </div>

      {/* AI Summary Section */}
      {email.summary && (
        <div className="card p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary-600" />
            AI Summary
          </h2>
          <p className="text-gray-700 leading-relaxed">
            {email.summary}
          </p>
        </div>
      )}

      {/* Key Points */}
      {email.key_points && email.key_points.length > 0 && (
        <div className="card p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <ListChecks className="h-5 w-5 text-blue-600" />
            Key Points
          </h2>
          <ul className="space-y-3">
            {email.key_points.map((point, index) => (
              <li key={index} className="flex items-start gap-3">
                <div className="mt-1.5 h-2 w-2 rounded-full bg-blue-500 flex-shrink-0" />
                <span className="text-gray-700">{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Action Items */}
      {email.action_items && email.action_items.length > 0 && (
        <div className="card p-6 mb-6 border-l-4 border-l-orange-500">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-orange-600" />
            Action Items
          </h2>
          <ul className="space-y-3">
            {email.action_items.map((item, index) => (
              <li key={index} className="flex items-start gap-3 p-3 bg-orange-50 rounded-lg">
                <input 
                  type="checkbox" 
                  className="mt-1 h-4 w-4 rounded border-gray-300 text-orange-600 focus:ring-orange-500"
                />
                <span className="text-gray-700">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Original Email Preview */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Mail className="h-5 w-5 text-gray-600" />
          Original Email
        </h2>
        <div className="bg-gray-50 rounded-lg p-4">
          {email.body_preview ? (
            <p className="text-gray-700 whitespace-pre-wrap">
              {email.body_preview}
            </p>
          ) : email.snippet ? (
            <p className="text-gray-600 italic">
              {email.snippet}
            </p>
          ) : (
            <p className="text-gray-500 italic">
              No email content available
            </p>
          )}
        </div>
      </div>

      {/* Labels */}
      {email.labels && email.labels.length > 0 && (
        <div className="mt-6 flex items-center gap-2 flex-wrap">
          <span className="text-sm text-gray-500">Labels:</span>
          {email.labels.map((label, index) => (
            <span 
              key={index}
              className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded"
            >
              {label}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default EmailSummary
