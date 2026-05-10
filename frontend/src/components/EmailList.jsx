import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { 
  Search, Filter, ChevronLeft, ChevronRight, 
  Mail, Clock, AlertCircle, Star 
} from 'lucide-react'
import { emailsApi } from '../services/api'
import { format, formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

const CATEGORIES = [
  { value: '', label: 'All Categories' },
  { value: 'work', label: 'Work' },
  { value: 'personal', label: 'Personal' },
  { value: 'finance', label: 'Finance' },
  { value: 'newsletter', label: 'Newsletter' },
  { value: 'shopping', label: 'Shopping' },
  { value: 'other', label: 'Other' },
]

const URGENCY_LEVELS = [
  { value: '', label: 'All Priorities' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'normal', label: 'Normal' },
  { value: 'low', label: 'Low' },
]

function EmailList() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  
  const [emails, setEmails] = useState([])
  const [loading, setLoading] = useState(true)
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 20,
    total: 0,
    hasMore: false,
  })

  // Filters
  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [category, setCategory] = useState(searchParams.get('category') || '')
  const [urgency, setUrgency] = useState(searchParams.get('urgency') || '')
  const [showFilters, setShowFilters] = useState(false)

  useEffect(() => {
    fetchEmails()
  }, [searchParams])

  const fetchEmails = async () => {
    setLoading(true)
    try {
      const params = {
        page: parseInt(searchParams.get('page')) || 1,
        page_size: 20,
        search: searchParams.get('search') || undefined,
        category: searchParams.get('category') || undefined,
        urgency: searchParams.get('urgency') || undefined,
      }
      
      const response = await emailsApi.list(params)
      setEmails(response.data.emails)
      setPagination({
        page: response.data.page,
        pageSize: response.data.page_size,
        total: response.data.total,
        hasMore: response.data.has_more,
      })
    } catch (error) {
      console.error('Failed to fetch emails:', error)
    } finally {
      setLoading(false)
    }
  }

  const applyFilters = () => {
    const params = new URLSearchParams()
    if (search) params.set('search', search)
    if (category) params.set('category', category)
    if (urgency) params.set('urgency', urgency)
    params.set('page', '1')
    setSearchParams(params)
  }

  const handlePageChange = (newPage) => {
    const params = new URLSearchParams(searchParams)
    params.set('page', String(newPage))
    setSearchParams(params)
  }

  const handleEmailClick = (email) => {
    navigate(`/emails/${email.id}`)
  }

  const getUrgencyBadge = (urgency) => {
    const classes = {
      urgent: 'badge-urgent',
      normal: 'badge-normal',
      low: 'badge-low',
    }
    return classes[urgency] || 'badge-normal'
  }

  const getCategoryColor = (cat) => {
    const colors = {
      work: 'bg-blue-100 text-blue-800',
      personal: 'bg-purple-100 text-purple-800',
      finance: 'bg-green-100 text-green-800',
      newsletter: 'bg-yellow-100 text-yellow-800',
      shopping: 'bg-pink-100 text-pink-800',
      other: 'bg-gray-100 text-gray-800',
    }
    return colors[cat] || colors.other
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Emails</h1>
          <p className="text-gray-600 mt-1">
            {pagination.total} emails total
          </p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="card p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search emails..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && applyFilters()}
              className="input pl-10"
            />
          </div>

          {/* Filter Toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={clsx(
              'btn-secondary flex items-center gap-2',
              showFilters && 'bg-gray-200'
            )}
          >
            <Filter className="h-4 w-4" />
            Filters
          </button>

          {/* Search Button */}
          <button onClick={applyFilters} className="btn-primary">
            Search
          </button>
        </div>

        {/* Filter Options */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t border-gray-200 grid md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="input"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Priority
              </label>
              <select
                value={urgency}
                onChange={(e) => setUrgency(e.target.value)}
                className="input"
              >
                {URGENCY_LEVELS.map((level) => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={() => {
                  setSearch('')
                  setCategory('')
                  setUrgency('')
                  setSearchParams(new URLSearchParams())
                }}
                className="btn-secondary w-full"
              >
                Clear Filters
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Email List */}
      {loading ? (
        <div className="card p-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading emails...</p>
        </div>
      ) : emails.length === 0 ? (
        <div className="card p-8 text-center">
          <Mail className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">No emails found</h3>
          <p className="text-gray-600 mt-1">
            Try adjusting your filters or sync your inbox.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {emails.map((email) => (
            <div
              key={email.id}
              onClick={() => handleEmailClick(email)}
              className={clsx(
                'card p-4 cursor-pointer hover:shadow-md transition-shadow',
                !email.is_read && 'bg-blue-50 border-blue-200'
              )}
            >
              <div className="flex items-start gap-4">
                {/* Urgency Indicator */}
                <div className="flex-shrink-0 pt-1">
                  {email.urgency === 'urgent' ? (
                    <AlertCircle className="h-5 w-5 text-red-500" />
                  ) : email.is_starred ? (
                    <Star className="h-5 w-5 text-yellow-500 fill-yellow-500" />
                  ) : (
                    <Mail className={clsx(
                      'h-5 w-5',
                      email.is_read ? 'text-gray-400' : 'text-primary-600'
                    )} />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <p className={clsx(
                        'text-sm truncate',
                        !email.is_read ? 'font-semibold text-gray-900' : 'text-gray-700'
                      )}>
                        {email.sender}
                      </p>
                      <h3 className={clsx(
                        'text-base truncate mt-1',
                        !email.is_read ? 'font-semibold text-gray-900' : 'text-gray-900'
                      )}>
                        {email.subject || '(No Subject)'}
                      </h3>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <p className="text-xs text-gray-500">
                        {email.received_at && formatDistanceToNow(new Date(email.received_at), { addSuffix: true })}
                      </p>
                    </div>
                  </div>

                  {/* Summary Preview */}
                  {email.summary && (
                    <p className="text-sm text-gray-600 mt-2 line-clamp-2">
                      {email.summary}
                    </p>
                  )}

                  {/* Tags */}
                  <div className="flex items-center gap-2 mt-3">
                    <span className={clsx('badge', getUrgencyBadge(email.urgency))}>
                      {email.urgency}
                    </span>
                    <span className={clsx('badge', getCategoryColor(email.category))}>
                      {email.category}
                    </span>
                    {email.action_items?.length > 0 && (
                      <span className="badge bg-orange-100 text-orange-800">
                        {email.action_items.length} action{email.action_items.length > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {pagination.total > pagination.pageSize && (
        <div className="mt-6 flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Showing {((pagination.page - 1) * pagination.pageSize) + 1} to{' '}
            {Math.min(pagination.page * pagination.pageSize, pagination.total)} of{' '}
            {pagination.total} emails
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className="btn-secondary p-2"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <span className="px-4 py-2 text-sm">
              Page {pagination.page}
            </span>
            <button
              onClick={() => handlePageChange(pagination.page + 1)}
              disabled={!pagination.hasMore}
              className="btn-secondary p-2"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default EmailList
