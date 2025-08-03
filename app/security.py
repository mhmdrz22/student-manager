from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .models import User
from .database import get_db

# Password Hashing Setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
# In a real application, this should be a secret key stored securely, not hardcoded.
SECRET_KEY = "a-very-secret-key-that-should-be-in-an-env-file"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# This function will be the dependency
def get_current_user(token: str, db):
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
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=302, detail="Not authenticated", headers={"Location": "/login"})

    token_value = token.split(" ")[1] if token else None
    if not token_value:
        raise HTTPException(status_code=302, detail="Not authenticated", headers={"Location": "/login"})

    return get_current_user(token=token_value, db=db)
