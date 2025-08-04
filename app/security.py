from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .models import User
from .database import get_db

# JWT Configuration
SECRET_KEY = "a-very-secret-key-that-should-be-in-an-env-file"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


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


def get_current_user(token: str, db: Session):
    credentials_exception = HTTPException(
        status_code=302,
        detail="Could not validate credentials",
        headers={"Location": "/login"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise credentials_exception

        user.token_role = payload.get("role")
        return user

    except JWTError:
        raise credentials_exception

async def get_current_active_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=302, detail="Not authenticated", headers={"Location": "/login"})

    token_value = token.split(" ")[1] if token else None
    if not token_value:
        raise HTTPException(status_code=302, detail="Not authenticated", headers={"Location": "/login"})

    return get_current_user(token=token_value, db=db)

def require_role(allowed_roles: list[str]):
    """
    Dependency factory that returns a dependency that checks for user role.
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.token_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action."
            )
        return current_user
    return role_checker
