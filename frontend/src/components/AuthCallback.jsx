import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../App'
import { CheckCircle, XCircle, Loader2 } from 'lucide-react'

function AuthCallback({ error: isError }) {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { login } = useAuth()
  const [status, setStatus] = useState('processing')

  useEffect(() => {
    if (isError) {
      const message = searchParams.get('message') || 'Authentication failed'
      setStatus('error')
      // Redirect to login after showing error
      setTimeout(() => navigate('/login'), 3000)
      return
    }

    const token = searchParams.get('token')
    if (token) {
      login(token)
      setStatus('success')
      // Redirect to dashboard
      setTimeout(() => navigate('/'), 1500)
    } else {
      setStatus('error')
      setTimeout(() => navigate('/login'), 3000)
    }
  }, [isError, searchParams, login, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="card p-8 max-w-md text-center">
        {status === 'processing' && (
          <>
            <Loader2 className="h-16 w-16 text-primary-600 animate-spin mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Completing Authentication
            </h2>
            <p className="text-gray-600">
              Please wait while we set up your account...
            </p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Authentication Successful!
            </h2>
            <p className="text-gray-600">
              Redirecting you to your dashboard...
            </p>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Authentication Failed
            </h2>
            <p className="text-gray-600 mb-4">
              {searchParams.get('message') || 'Something went wrong. Please try again.'}
            </p>
            <button
              onClick={() => navigate('/login')}
              className="btn-primary"
            >
              Back to Login
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default AuthCallback
