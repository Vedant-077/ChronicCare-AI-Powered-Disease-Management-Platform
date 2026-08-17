# auth.py
# Handles two jobs:
# 1. Password hashing (so we never store plain-text passwords)
# 2. Creating & verifying JWT tokens (so a logged-in user can prove who they are
#    on every future request, without re-sending their password each time)

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
import models

# In a real deployment, load this from an environment variable, never hardcode it.
SECRET_KEY = "dev-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # tokens last 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# This tells FastAPI: "expect a Bearer token in the Authorization header,
# and the login endpoint that issues it is at /auth/login"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """
    This runs automatically on any endpoint that depends on it.
    It reads the token from the request, checks it's valid, and
    returns the matching User row -- so route code can just say
    "this request belongs to `current_user`".
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user
