# utils/auth.py
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional

# JWT and OAuth2 configurations
import os


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


SECRET_KEY = _required_env("SECRET_KEY")
SESSION_SECRET = _required_env("SESSION_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 69
ACCESS_TOKEN_COOKIE_NAME = "accessToken"

USER_TYPE_USER = "user"
USER_TYPE_TEAM = "team"
USER_TYPE_ADMIN = "admin"

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Import database singleton
from utils.database import db


# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str):
    """Authenticate user by username and password from MongoDB."""
    user = db.get_user_by_username(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_auth_token(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
):
    if token:
        return token

    cookie_token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    raise _credentials_exception()


def get_current_user(token: str = Depends(get_auth_token)):
    """Get current user from JWT token or auth cookie."""
    credentials_exception = _credentials_exception()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user


def require_roles(*roles: str):
    allowed_roles = set(roles)

    def dependency(current_user: dict = Depends(get_current_user)):
        if current_user and current_user.get("role") in allowed_roles:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized for this role",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return dependency


def is_admin(current_user: dict = Depends(get_current_user)):
    """Check if current user is admin."""
    return require_roles(USER_TYPE_ADMIN)(current_user)
