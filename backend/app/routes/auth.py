"""
Authentication routes for Gmail OAuth 2.0 flow.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas import (
    TokenResponse, UserResponse, UserSettings, 
    OAuthCallbackResponse, MessageResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return user


def create_oauth_flow() -> Flow:
    """Create Google OAuth flow."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.gmail_client_id,
                "client_secret": settings.gmail_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.gmail_redirect_uri],
            }
        },
        scopes=settings.gmail_scopes,
    )
    flow.redirect_uri = settings.gmail_redirect_uri
    return flow


@router.get("/gmail", response_class=RedirectResponse)
async def initiate_gmail_auth():
    """
    Initiate Gmail OAuth 2.0 flow.
    Redirects user to Google consent page.
    """
    flow = create_oauth_flow()
    
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # Force consent to get refresh token
    )
    
    logger.info(f"Redirecting to Google OAuth: {authorization_url}")
    return RedirectResponse(url=authorization_url)


@router.get("/callback")
async def gmail_auth_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Gmail OAuth callback.
    Exchanges authorization code for tokens.
    """
    if error:
        logger.error(f"OAuth error: {error}")
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"http://localhost:5173/auth/error?message={error}"
        )
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code",
        )
    
    try:
        # Exchange code for tokens
        flow = create_oauth_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get user info from Google
        user_info_service = build("oauth2", "v2", credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        
        email = user_info.get("email")
        name = user_info.get("name")
        picture = user_info.get("picture")
        
        logger.info(f"OAuth successful for user: {email}")
        
        # Check if user exists
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if user:
            # Update existing user tokens
            user.access_token = credentials.token
            user.refresh_token = credentials.refresh_token or user.refresh_token
            user.token_expiry = credentials.expiry
            user.name = name
            user.picture = picture
            user.updated_at = datetime.utcnow()
        else:
            # Create new user
            user = User(
                email=email,
                name=name,
                picture=picture,
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_expiry=credentials.expiry,
            )
            db.add(user)
        
        await db.commit()
        await db.refresh(user)
        
        # Create JWT token for frontend
        access_token = create_access_token(data={"sub": str(user.id)})
        
        # Redirect to frontend with token
        return RedirectResponse(
            url=f"http://localhost:5173/auth/success?token={access_token}"
        )
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return RedirectResponse(
            url=f"http://localhost:5173/auth/error?message=Authentication failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current authenticated user information."""
    return current_user


@router.put("/settings", response_model=UserResponse)
async def update_user_settings(
    settings_update: UserSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user settings."""
    if settings_update.notification_enabled is not None:
        current_user.notification_enabled = settings_update.notification_enabled
    
    if settings_update.digest_enabled is not None:
        current_user.digest_enabled = settings_update.digest_enabled
    
    if settings_update.digest_time is not None:
        current_user.digest_time = settings_update.digest_time
    
    current_user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout current user.
    Note: JWT tokens are stateless, so we just return success.
    Frontend should discard the token.
    """
    return MessageResponse(success=True, message="Logged out successfully")


@router.delete("/disconnect", response_model=MessageResponse)
async def disconnect_gmail(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnect Gmail account and revoke tokens.
    This removes the user's OAuth tokens.
    """
    current_user.access_token = None
    current_user.refresh_token = None
    current_user.token_expiry = None
    current_user.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return MessageResponse(
        success=True, 
        message="Gmail disconnected. You can reconnect anytime."
    )
