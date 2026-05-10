import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../App'
import { 
  Mail, LayoutDashboard, Inbox, MessageSquare, 
  Settings, LogOut, RefreshCw, User 
} from 'lucide-react'
import { useState } from 'react'
import { emailsApi } from '../services/api'

function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [syncing, setSyncing] = useState(false)

  const handleSync = async () => {
    setSyncing(true)
    try {
      await emailsApi.sync()
      // Could show a toast notification here
    } catch (error) {
      console.error('Sync failed:', error)
    } finally {
      setSyncing(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="bg-primary-600 p-2 rounded-lg">
              <Mail className="h-6 w-6 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900">EmailGuardian</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            <NavItem to="/" icon={<LayoutDashboard />} label="Dashboard" end />
            <NavItem to="/emails" icon={<Inbox />} label="Emails" />
            <NavItem to="/chat" icon={<MessageSquare />} label="Chat" />
          </ul>
        </nav>

        {/* Sync Button */}
        <div className="p-4 border-t border-gray-200">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="w-full btn-secondary flex items-center justify-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Syncing...' : 'Sync Emails'}
          </button>
        </div>

        {/* User Section */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            {user?.picture ? (
              <img 
                src={user.picture} 
                alt={user.name} 
                className="h-10 w-10 rounded-full"
              />
            ) : (
              <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                <User className="h-5 w-5 text-gray-500" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {user?.name || 'User'}
              </p>
              <p className="text-xs text-gray-500 truncate">
                {user?.email}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 text-gray-600 hover:text-gray-900 text-sm py-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}

function NavItem({ to, icon, label, end = false }) {
  return (
    <li>
      <NavLink
        to={to}
        end={end}
        className={({ isActive }) =>
          `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
            isActive
              ? 'bg-primary-50 text-primary-700 font-medium'
              : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
          }`
        }
      >
        <span className="h-5 w-5">{icon}</span>
        {label}
      </NavLink>
    </li>
  )
}

export default Layout
