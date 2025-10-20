"""
Authentication and authorization utilities.

Provides JWT token creation/validation and password hashing.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import Settings, get_settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
bearer_scheme = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hashed password
    """
    return pwd_context.hash(password)


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None, settings: Settings = Depends(get_settings)
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode in token
        expires_delta: Token expiration time (defaults to settings value)
        settings: Application settings

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str, settings: Settings) -> dict:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token to decode
        settings: Application settings

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token
        settings: Application settings

    Returns:
        User data from token payload

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    payload = decode_access_token(token, settings)

    # Extract user info from payload
    username: Optional[str] = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "username": username,
        "payload": payload,
    }


async def verify_router_api_key(
    api_key: Optional[str] = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> bool:
    """
    Verify the router API key for router-to-server communication.

    Args:
        api_key: API key from X-API-Key header
        settings: Application settings

    Returns:
        True if API key is valid

    Raises:
        HTTPException: If API key is invalid or missing
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"X-API-Key": "required"},
        )

    # Constant-time comparison to prevent timing attacks
    import hmac

    if not hmac.compare_digest(api_key, settings.router_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return True


async def require_active_scanning_enabled(
    settings: Settings = Depends(get_settings),
) -> bool:
    """
    Verify that active scanning is enabled.

    This is a safety check for intrusive operations that should only
    be performed in authorized testing environments.

    Args:
        settings: Application settings

    Returns:
        True if active scanning is enabled

    Raises:
        HTTPException: If active scanning is disabled
    """
    if not settings.enable_active_scanning:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Active/intrusive scanning is disabled. "
                "Enable ENABLE_ACTIVE_SCANNING only in authorized testing environments."
            ),
        )
    return True
