import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect, createContext, useContext } from 'react'
import Dashboard from './components/Dashboard'
import EmailList from './components/EmailList'
import EmailSummary from './components/EmailSummary'
import ChatInterface from './components/ChatInterface'
import Login from './components/Login'
import AuthCallback from './components/AuthCallback'
import Layout from './components/Layout'
import api from './services/api'

// Auth Context
export const AuthContext = createContext(null)

export function useAuth() {
  return useContext(AuthContext)
}

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check for stored token
    const token = localStorage.getItem('token')
    if (token) {
      api.setToken(token)
      fetchUser()
    } else {
      setLoading(false)
    }
  }, [])

  const fetchUser = async () => {
    try {
      const response = await api.get('/auth/me')
      setUser(response.data)
    } catch (error) {
      console.error('Failed to fetch user:', error)
      localStorage.removeItem('token')
      api.setToken(null)
    } finally {
      setLoading(false)
    }
  }

  const login = (token) => {
    localStorage.setItem('token', token)
    api.setToken(token)
    fetchUser()
  }

  const logout = () => {
    localStorage.removeItem('token')
    api.setToken(null)
    setUser(null)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading EmailGuardian...</p>
        </div>
      </div>
    )
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, fetchUser }}>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={!user ? <Login /> : <Navigate to="/" />} />
        <Route path="/auth/success" element={<AuthCallback />} />
        <Route path="/auth/error" element={<AuthCallback error />} />

        {/* Protected routes */}
        <Route
          path="/"
          element={user ? <Layout /> : <Navigate to="/login" />}
        >
          <Route index element={<Dashboard />} />
          <Route path="emails" element={<EmailList />} />
          <Route path="emails/:id" element={<EmailSummary />} />
          <Route path="chat" element={<ChatInterface />} />
        </Route>

        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </AuthContext.Provider>
  )
}

export default App
