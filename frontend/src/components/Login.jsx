import { Mail, Shield, Sparkles, Clock, BarChart3 } from 'lucide-react'
import { authApi } from '../services/api'

function Login() {
  const handleGoogleLogin = () => {
    window.location.href = authApi.getGmailAuthUrl()
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-primary-100">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-16">
            <div className="flex items-center justify-center mb-6">
              <div className="bg-primary-600 p-4 rounded-2xl">
                <Mail className="h-12 w-12 text-white" />
              </div>
            </div>
            <h1 className="text-5xl font-bold text-gray-900 mb-4">
              EmailGuardian
            </h1>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Your intelligent email companion. Let AI summarize, categorize, and prioritize your inbox so you can focus on what matters.
            </p>
          </div>

          {/* Features Grid */}
          <div className="grid md:grid-cols-2 gap-6 mb-16">
            <FeatureCard
              icon={<Sparkles className="h-6 w-6" />}
              title="AI-Powered Summaries"
              description="Get instant 2-3 sentence summaries of every email, powered by Claude AI."
            />
            <FeatureCard
              icon={<Shield className="h-6 w-6" />}
              title="Smart Prioritization"
              description="Automatically detect urgent emails and action items that need your attention."
            />
            <FeatureCard
              icon={<Clock className="h-6 w-6" />}
              title="Daily Digests"
              description="Start your day with a curated summary of yesterday's important emails."
            />
            <FeatureCard
              icon={<BarChart3 className="h-6 w-6" />}
              title="Inbox Analytics"
              description="Understand your email patterns with visual breakdowns and trends."
            />
          </div>

          {/* Login Card */}
          <div className="card p-8 max-w-md mx-auto text-center">
            <h2 className="text-2xl font-semibold mb-4">Get Started</h2>
            <p className="text-gray-600 mb-6">
              Connect your Gmail account to start organizing your inbox with AI.
            </p>
            <button
              onClick={handleGoogleLogin}
              className="w-full flex items-center justify-center gap-3 bg-white border border-gray-300 rounded-lg px-6 py-3 text-gray-700 font-medium hover:bg-gray-50 hover:shadow-md transition-all"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Sign in with Google
            </button>
            <p className="text-sm text-gray-500 mt-4">
              We only request read access to your emails. Your data stays private.
            </p>
          </div>

          {/* Footer */}
          <div className="text-center mt-16 text-gray-500 text-sm">
            <p>EmailGuardian uses OAuth 2.0 for secure Gmail access.</p>
            <p className="mt-1">Your emails are processed locally and never stored on external servers.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function FeatureCard({ icon, title, description }) {
  return (
    <div className="card p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start gap-4">
        <div className="bg-primary-100 text-primary-600 p-3 rounded-lg">
          {icon}
        </div>
        <div>
          <h3 className="font-semibold text-lg text-gray-900 mb-1">{title}</h3>
          <p className="text-gray-600">{description}</p>
        </div>
      </div>
    </div>
  )
}

export default Login
