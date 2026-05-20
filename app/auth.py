from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

try:
    import models
    from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
    from database import get_db
except ImportError:
    from app import models
    from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
    from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# 2. Setăm "Mașina de tocat" parole (BCRYPT)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- FUNCȚII PENTRU PAROLE ---

def get_password_hash(password: str):
    """Transformă parola '1234' în hash criptat"""
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    """Verifică dacă parola introdusă se potrivește cu hash-ul din baza de date"""
    return pwd_context.verify(plain_password, hashed_password)


# --- FUNCȚII PENTRU TOKEN (JWT) ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Generează 'Biletul de acces' (JWT Token)"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire}) # Adăugăm data expirării în token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nu s-a putut valida credențialele",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception

    return user