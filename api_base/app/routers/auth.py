"""Authentication endpoints (JWT login + OAuth).

This implementation attempts to authenticate against the `Users` table in
the connected database. If no matching user is found, it falls back to the
existing static admin credentials from configuration.
"""

import secrets

import httpx
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api_base.app.models.schemas import LoginRequest, TokenResponse, RegisterRequest, RegisterResponse, UserProfile
from api_base.app.security.security import create_access_token, decode_access_token, verify_password, hash_password
from api_base.app.config import CONFIG
from api_base.app.models.base_db import get_db
from api_base.app.models.schema_db import User


router = APIRouter(prefix="/auth", tags=["auth"])

_oauth_states: dict[str, str] = {}


# ── Google OAuth ──────────────────────────────────────────────────────────────

@router.get("/google/login")
async def google_login():
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = "google"
    redirect_uri = f"{CONFIG.oauth_redirect_base}/api/auth/google/callback"
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={CONFIG.google_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&state={state}"
    )
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    if state not in _oauth_states:
        return RedirectResponse(url="/login?error=Invalid+state")
    del _oauth_states[state]

    redirect_uri = f"{CONFIG.oauth_redirect_base}/api/auth/google/callback"

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": CONFIG.google_client_id,
                "client_secret": CONFIG.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        if "access_token" not in token_data:
            return RedirectResponse(url="/login?error=Token+exchange+failed")

        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        user_data = user_resp.json()

    email = user_data.get("email", "")
    name = user_data.get("name", "")
    if not email:
        return RedirectResponse(url="/login?error=No+email+from+Google")

    user = db.query(User).filter(User.Email == email).first()
    if not user:
        user = User(
            Username=email,
            Email=email,
            FullName=name,
            Role="user",
            PasswordHash="",
        )
        db.add(user)
        db.commit()

    token = create_access_token(subject=user.Username)
    return RedirectResponse(url=f"/ui?token={token}&oauth=google")


# ── GitHub OAuth ──────────────────────────────────────────────────────────────

@router.get("/github/login")
async def github_login():
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = "github"
    redirect_uri = f"{CONFIG.oauth_redirect_base}/api/auth/github/callback"
    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={CONFIG.github_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=read:user%20user:email"
        f"&state={state}"
    )
    return RedirectResponse(url=url)


@router.get("/github/callback")
async def github_callback(code: str, state: str, db: Session = Depends(get_db)):
    if state not in _oauth_states:
        return RedirectResponse(url="/login?error=Invalid+state")
    del _oauth_states[state]

    redirect_uri = f"{CONFIG.oauth_redirect_base}/api/auth/github/callback"

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "code": code,
                "client_id": CONFIG.github_client_id,
                "client_secret": CONFIG.github_client_secret,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        if "access_token" not in token_data:
            return RedirectResponse(url="/login?error=Token+exchange+failed")

        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        user_data = user_resp.json()

        email_resp = await client.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        emails = email_resp.json()

    email = ""
    for e in emails:
        if e.get("primary") and e.get("verified"):
            email = e["email"]
            break
    if not email and emails:
        email = emails[0].get("email", "")

    login = user_data.get("login", "")
    name = user_data.get("name") or login
    if not email:
        return RedirectResponse(url="/login?error=No+email+from+GitHub")

    user = db.query(User).filter(User.Email == email).first()
    if not user:
        user = User(
            Username=email,
            Email=email,
            FullName=name,
            Role="user",
            PasswordHash="",
        )
        db.add(user)
        db.commit()

    token = create_access_token(subject=user.Username)
    return RedirectResponse(url=f"/ui?token={token}&oauth=github")

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate a user and return an access token.

    Priority: try DB user match first, then fallback to configured admin.
    If the stored DB password appears to be plaintext, upgrade it to a
    salted hash on first successful login.
    """
    # Try DB lookup by username OR email (support logging in with email)
    user = db.query(User).filter(or_(User.Username == payload.username, User.Email == payload.username)).first()
    if user:
        stored = user.PasswordHash or ""
        # Support existing plaintext passwords by accepting equality and
        # upgrading to the hashed form for future logins.
        if verify_password(payload.password, stored) or stored == payload.password:
            # If stored was plaintext, update to hashed value
            if stored == payload.password:
                user.PasswordHash = hash_password(payload.password)
                db.add(user)
                db.commit()
            # Use canonical username as token subject so /auth/me can find the DB row
            token = create_access_token(subject=user.Username)
            is_admin = (user.Role == "admin")
            return TokenResponse(access_token=token, is_admin=is_admin)

    # Fallback to configured admin credentials
    if payload.username == CONFIG.admin_username and verify_password(payload.password, CONFIG.admin_password_hash):
        token = create_access_token(subject=payload.username)
        return TokenResponse(access_token=token)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")



@router.post("/register", response_model=RegisterResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    """Create a new user in the `users` table.

    The `username` is unique; `Email` column is also checked to avoid duplicates.
    Password is stored as a salted hash.
    """
    # Treat username as email in this app's UI
    existing = db.query(User).filter((User.Username == payload.username) | (User.Email == payload.username)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with that email already exists")

    new_user = User(
        Username=payload.username,
        Email=payload.username,
        PasswordHash=hash_password(payload.password),
        FullName=getattr(payload, 'fullname', None),
        Role="user",
    )
    db.add(new_user)
    db.commit()
    return RegisterResponse(message="User created")


@router.get("/me", response_model=UserProfile)
def me(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()), db: Session = Depends(get_db)) -> UserProfile:
    """Return profile for the current bearer token subject."""
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    username = payload.sub
    user = db.query(User).filter(User.Username == username).first()
    is_admin = False
    if user:
        is_admin = (user.Role == "admin")
    elif username == CONFIG.admin_username:
        is_admin = True
    if not user:
        return UserProfile(username=username, email=username, fullname=None, is_admin=is_admin)
    return UserProfile(
        username=user.Username,
        email=user.Email,
        fullname=getattr(user, 'FullName', None) or None,
        is_admin=is_admin,
    )

# HÀM XÁC THỰC NGƯỜI DÙNG (Cổng an ninh)
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()), db: Session = Depends(get_db)) -> User:
    """Extracts and validates the token, then returns the User object."""
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ hoặc đã hết hạn")
    
    # Tìm user trong DB dựa trên username (subject) trong token
    user = db.query(User).filter(User.Username == payload.sub).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Người dùng không tồn tại")
    
    return user