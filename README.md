# EmailGuardian

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi) ![React](https://img.shields.io/badge/React-18-61DAFB?logo=react) ![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker) ![License](https://img.shields.io/badge/License-MIT-yellow)

An intelligent email monitoring and summarization application powered by AI. EmailGuardian connects to your Gmail account, automatically fetches and categorizes emails, generates AI-powered summaries, and helps you stay on top of your inbox with minimal effort.

## Features

- **Gmail Integration**: Secure OAuth 2.0 authentication with Gmail
- **AI-Powered Summaries**: Claude AI generates concise summaries for each email
- **Smart Categorization**: Automatic classification into work, personal, finance, newsletter, shopping, or other
- **Priority Detection**: Identifies urgent emails that need immediate attention
- **Action Item Extraction**: Automatically extracts tasks and action items from emails
- **Daily Digests**: Get a summary of yesterday's emails every morning
- **Natural Language Chat**: Ask questions about your inbox in plain English
- **Analytics Dashboard**: Visual insights into your email patterns
- **Background Sync**: Automatic email fetching every 15 minutes

## Architecture

```
Gmail API ──► Email Fetcher ──► SQLite/PostgreSQL
                                      │
                                 Summarizer (Claude API)
                                      │
                           ┌──────────┴──────────┐
                      Classifier            Scheduler
                    (6 categories)      (15-min sync)
                           │
                    FastAPI Backend
                           │
                    React Frontend
                    (Dashboard / Chat / Analytics)
```

## Tech Stack

### Backend
- **Python 3.11+** with FastAPI
- **SQLAlchemy** with SQLite (upgradeable to PostgreSQL)
- **APScheduler** for background tasks
- **Anthropic Claude API** for AI summarization
- **Google Gmail API** for email access

### Frontend
- **React 18** with Vite
- **Tailwind CSS** for styling
- **Recharts** for analytics visualization
- **React Router** for navigation

## Prerequisites

Before you begin, you'll need:

1. **Python 3.11+** installed
2. **Node.js 18+** installed
3. **Google Cloud Project** with Gmail API enabled
4. **Anthropic API Key** for Claude

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Lkhanaajav/email-guardian.git
cd email-guardian
```

### 2. Configure Google Cloud / Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it
4. Configure OAuth Consent Screen:
   - Go to "APIs & Services" > "OAuth consent screen"
   - Choose "External" user type
   - Fill in the required fields (app name, support email, etc.)
   - Add scopes: `gmail.readonly`, `gmail.labels`, `userinfo.email`
5. Create OAuth Credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Web application"
   - Add authorized redirect URI: `http://localhost:8000/auth/callback`
   - Save the Client ID and Client Secret

### 3. Get Anthropic API Key

1. Sign up at [Anthropic Console](https://console.anthropic.com/)
2. Create an API key
3. Save the key securely

### 4. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

Edit `.env` with your credentials:

```env
GMAIL_CLIENT_ID=your_client_id_here
GMAIL_CLIENT_SECRET=your_client_secret_here
GMAIL_REDIRECT_URI=http://localhost:8000/auth/callback
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DATABASE_URL=sqlite+aiosqlite:///./email_guardian.db
SECRET_KEY=your-super-secret-key-change-in-production
FETCH_INTERVAL_MINUTES=15
DEBUG=true
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

The backend will be available at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Docker Deployment

For production deployment using Docker:

```bash
# Create .env file in root directory with your credentials
cp backend/.env.example .env
# Edit .env with your credentials

# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

The application will be available at:
- Frontend: `http://localhost`
- Backend API: `http://localhost:8000`

## Usage

1. **Connect Gmail**: Click "Sign in with Google" and authorize access
2. **Sync Emails**: Click "Sync Emails" or wait for automatic sync
3. **View Dashboard**: See your email overview, urgent items, and analytics
4. **Browse Emails**: Filter and search your summarized emails
5. **Chat**: Ask questions like "Show me urgent emails about deadlines"

## API Endpoints

### Authentication
- `GET /auth/gmail` - Initiate Gmail OAuth flow
- `GET /auth/callback` - OAuth callback handler
- `GET /auth/me` - Get current user info
- `PUT /auth/settings` - Update user settings

### Emails
- `GET /emails` - List emails with filters
- `GET /emails/{id}` - Get single email details
- `GET /emails/urgent` - Get urgent emails
- `GET /emails/today` - Get today's emails
- `GET /emails/digest` - Get daily digest
- `POST /emails/sync` - Trigger manual sync
- `POST /emails/chat` - Natural language query

### Analytics
- `GET /analytics` - Get email statistics
- `GET /analytics/trends` - Get email trends
- `GET /analytics/action-items` - Get pending action items

## Project Structure

```
email-guardian/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration
│   │   ├── database.py          # Database setup
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── services/
│   │   │   ├── email_fetcher.py # Gmail API integration
│   │   │   ├── summarizer.py    # Claude AI integration
│   │   │   ├── classifier.py    # Email classification
│   │   │   └── scheduler.py     # Background tasks
│   │   └── routes/
│   │       ├── auth.py          # Auth endpoints
│   │       ├── emails.py        # Email endpoints
│   │       └── analytics.py     # Stats endpoints
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── EmailList.jsx
│   │   │   ├── EmailSummary.jsx
│   │   │   ├── ChatInterface.jsx
│   │   │   └── ...
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Security Considerations

- OAuth tokens are stored in the database (encrypt in production)
- Use strong SECRET_KEY in production
- Never commit `.env` files or credentials
- Enable HTTPS in production
- Consider rate limiting for API endpoints
- Regularly rotate API keys

## Troubleshooting

### OAuth Error: "redirect_uri_mismatch"
Ensure your redirect URI in Google Cloud Console exactly matches `GMAIL_REDIRECT_URI` in your `.env`

### Emails Not Syncing
- Check that your Gmail API credentials are correct
- Verify the OAuth consent screen is properly configured
- Check the backend logs for errors

### Claude API Errors
- Verify your Anthropic API key is valid
- Check your API quota/billing status
- Ensure the model name in config is correct

## Future Enhancements (Phase 2)

- [ ] Email thread summarization
- [ ] Smart notifications (Telegram/Slack)
- [ ] Multi-account support
- [ ] Export to Notion/Obsidian
- [ ] Receipt/invoice extraction
- [ ] Email response suggestions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Open a GitHub issue
- Check existing documentation
- Review the API docs at `/docs`
