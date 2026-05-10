import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Token management
let authToken = null

api.setToken = (token) => {
  authToken = token
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common['Authorization']
  }
}

// Request interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API methods
export const authApi = {
  getGmailAuthUrl: () => `${API_BASE_URL}/auth/gmail`,
  getCurrentUser: () => api.get('/auth/me'),
  updateSettings: (settings) => api.put('/auth/settings', settings),
  logout: () => api.post('/auth/logout'),
  disconnect: () => api.delete('/auth/disconnect'),
}

export const emailsApi = {
  list: (params) => api.get('/emails', { params }),
  getById: (id) => api.get(`/emails/${id}`),
  getUrgent: (limit = 10) => api.get('/emails/urgent', { params: { limit } }),
  getToday: () => api.get('/emails/today'),
  getDigest: (date) => api.get('/emails/digest', { params: { date } }),
  generateDigest: (data) => api.post('/emails/digest/generate', data),
  markAsRead: (id) => api.put(`/emails/${id}/read`),
  sync: () => api.post('/emails/sync'),
  getSyncStatus: () => api.get('/emails/sync/status'),
  chat: (data) => api.post('/emails/chat', data),
}

export const analyticsApi = {
  get: (days = 7) => api.get('/analytics', { params: { days } }),
  getTrends: (days = 30) => api.get('/analytics/trends', { params: { days } }),
  getActionItems: (limit = 20) => api.get('/analytics/action-items', { params: { limit } }),
  getCategoryDetails: (category, days = 7) => api.get(`/analytics/category/${category}`, { params: { days } }),
}

export default api
