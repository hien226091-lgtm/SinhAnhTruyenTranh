"""Authentication endpoints (JWT login).

This implementation attempts to authenticate against the `Users` table in
the connected database. If no matching user is found, it falls back to the
existing static admin credentials from configuration.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api_base.app.models.schemas import LoginRequest, TokenResponse
from api_base.app.models.schemas import LoginRequest, TokenResponse, RegisterRequest, RegisterResponse
from api_base.app.security.security import create_access_token, verify_password, hash_password
from api_base.app.security.security import decode_access_token
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from api_base.app.models.schemas import UserProfile
from api_base.app.config import CONFIG
from api_base.app.models.base_db import get_db
from api_base.app.models.models import Users


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate a user and return an access token.

    Priority: try DB user match first, then fallback to configured admin.
    If the stored DB password appears to be plaintext, upgrade it to a
    salted hash on first successful login.
    """
    # Try DB lookup by username OR email (support logging in with email)
    user = db.query(Users).filter(or_(Users.Username == payload.username, Users.Email == payload.username)).first()
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
            return TokenResponse(access_token=token)

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
    existing = db.query(Users).filter((Users.Username == payload.username) | (Users.Email == payload.username)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with that email already exists")

    new_user = Users(
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
    user = db.query(Users).filter(Users.Username == username).first()
    if not user:
        # If not in DB, return minimal profile from token
        return UserProfile(username=username, email=username, fullname=None)
    return UserProfile(username=user.Username, email=user.Email, fullname=getattr(user, 'FullName', None) or None)
