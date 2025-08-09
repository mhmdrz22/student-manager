from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .models import User
from .database import get_db
from .config import settings

# JWT Configuration is loaded from settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed one using bcrypt."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """Hashes a plain password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(user: User, expires_delta: Optional[timedelta] = None):
    """Creates a new JWT access token, including the user's role."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": user.username,
        "role": user.role,
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str, db: Session) -> Optional[User]:
    """
    Decodes the JWT token and retrieves the user from the database.
    Returns the user object or None if validation fails.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None

        user = db.query(User).filter(User.username == username).first()
        # The role from the token should be validated against the DB role if needed,
        # but for now, we trust the token if the user exists.
        return user

    except JWTError:
        return None

async def get_current_active_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Dependency to get the current authenticated user.
    Raises an HTTPException if the user is not authenticated.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # The token from the browser cookie is expected to be in the format "Bearer <token>"
    token_value = token.split(" ")[1] if " " in token else token

    user = get_current_user(token=token_value, db=db)
    if not user:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    return user

async def try_get_current_active_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Dependency to optionally get the current authenticated user.
    Returns the user object or None if not authenticated.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None

    token_value = token.split(" ")[1] if " " in token else token

    user = get_current_user(token=token_value, db=db)
    return user

def require_role(allowed_roles: list[str]):
    """
    Dependency factory that returns a dependency that checks for user role.
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action."
            )
        return current_user
    return role_checker
