import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Mail, AlertCircle, CheckCircle, Clock, 
  TrendingUp, Users, Inbox, BarChart3 
} from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { analyticsApi, emailsApi } from '../services/api'
import { format } from 'date-fns'

const CATEGORY_COLORS = {
  work: '#3b82f6',
  personal: '#8b5cf6',
  finance: '#10b981',
  newsletter: '#f59e0b',
  shopping: '#ec4899',
  other: '#6b7280',
}

const URGENCY_COLORS = {
  urgent: '#ef4444',
  normal: '#f59e0b',
  low: '#10b981',
}

function Dashboard() {
  const navigate = useNavigate()
  const [analytics, setAnalytics] = useState(null)
  const [urgentEmails, setUrgentEmails] = useState([])
  const [actionItems, setActionItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      const [analyticsRes, urgentRes, actionsRes] = await Promise.all([
        analyticsApi.get(7),
        emailsApi.getUrgent(5),
        analyticsApi.getActionItems(10),
      ])
      setAnalytics(analyticsRes.data)
      setUrgentEmails(urgentRes.data)
      setActionItems(actionsRes.data.action_items || [])
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  const categoryData = analytics?.category_breakdown?.map(item => ({
    name: item.category.charAt(0).toUpperCase() + item.category.slice(1),
    value: item.count,
    color: CATEGORY_COLORS[item.category] || CATEGORY_COLORS.other,
  })) || []

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">
          Overview of your email activity for the last 7 days
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={<Mail className="h-6 w-6" />}
          label="Total Emails"
          value={analytics?.total_emails || 0}
          subtext={`${analytics?.emails_today || 0} today`}
          color="blue"
        />
        <StatCard
          icon={<AlertCircle className="h-6 w-6" />}
          label="Urgent"
          value={analytics?.urgent_count || 0}
          subtext="Need attention"
          color="red"
        />
        <StatCard
          icon={<Inbox className="h-6 w-6" />}
          label="Unread"
          value={analytics?.unread_count || 0}
          subtext="In your inbox"
          color="yellow"
        />
        <StatCard
          icon={<CheckCircle className="h-6 w-6" />}
          label="Processed"
          value={analytics?.processed_count || 0}
          subtext="AI summarized"
          color="green"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid lg:grid-cols-3 gap-8">
        {/* Category Chart */}
        <div className="lg:col-span-1 card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-gray-500" />
            Categories
          </h2>
          {categoryData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {categoryData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-500">
              No email data yet
            </div>
          )}
        </div>

        {/* Urgent Emails */}
        <div className="lg:col-span-1 card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-500" />
            Urgent Emails
          </h2>
          {urgentEmails.length > 0 ? (
            <ul className="space-y-3">
              {urgentEmails.map((email) => (
                <li 
                  key={email.id}
                  onClick={() => navigate(`/emails/${email.id}`)}
                  className="p-3 bg-red-50 rounded-lg cursor-pointer hover:bg-red-100 transition-colors"
                >
                  <p className="font-medium text-gray-900 truncate text-sm">
                    {email.subject || '(No Subject)'}
                  </p>
                  <p className="text-xs text-gray-600 truncate mt-1">
                    {email.sender}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                <p>No urgent emails!</p>
              </div>
            </div>
          )}
        </div>

        {/* Action Items */}
        <div className="lg:col-span-1 card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Clock className="h-5 w-5 text-yellow-500" />
            Action Items
          </h2>
          {actionItems.length > 0 ? (
            <ul className="space-y-3 max-h-64 overflow-y-auto">
              {actionItems.slice(0, 8).map((item, index) => (
                <li 
                  key={index}
                  className="flex items-start gap-3 p-2 hover:bg-gray-50 rounded-lg"
                >
                  <div className="mt-1 h-2 w-2 rounded-full bg-yellow-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900">{item.action}</p>
                    <p className="text-xs text-gray-500 truncate mt-1">
                      From: {item.from_email?.subject || 'Unknown'}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                <p>No pending actions!</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Top Senders */}
      <div className="mt-8 card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Users className="h-5 w-5 text-gray-500" />
          Top Senders (Last 7 Days)
        </h2>
        {analytics?.top_senders?.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {analytics.top_senders.slice(0, 5).map((sender, index) => (
              <div 
                key={index}
                className="text-center p-4 bg-gray-50 rounded-lg"
              >
                <div className="w-12 h-12 rounded-full bg-primary-100 flex items-center justify-center mx-auto mb-2">
                  <span className="text-primary-700 font-semibold">
                    {(sender.sender_email || '?')[0].toUpperCase()}
                  </span>
                </div>
                <p className="text-sm font-medium text-gray-900 truncate">
                  {sender.sender_email?.split('@')[0] || 'Unknown'}
                </p>
                <p className="text-xs text-gray-500">
                  {sender.email_count} emails
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">No sender data yet</p>
        )}
      </div>
    </div>
  )
}

function StatCard({ icon, label, value, subtext, color }) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    red: 'bg-red-50 text-red-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    green: 'bg-green-50 text-green-600',
  }

  return (
    <div className="card p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{label}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
          <p className="text-sm text-gray-500 mt-1">{subtext}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  )
}

export default Dashboard
