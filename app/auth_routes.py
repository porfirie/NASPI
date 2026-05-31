from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

try:
    import auth
    from auth import get_current_user
    from config import ACCESS_TOKEN_EXPIRE_MINUTES
    from app.database import get_db
    import app.models
    from schemas import PasswordChange, UsernameChange
except ImportError:
    from app import auth
    from app.auth import get_current_user
    from app.config import ACCESS_TOKEN_EXPIRE_MINUTES
    from app.database import get_db
    from app import models
    from app.schemas import PasswordChange, UsernameChange

router = APIRouter()


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilizator sau parolă incorectă",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not auth.verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Parola veche este incorectă")

    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not db_user:
        raise HTTPException(status_code=500, detail="Utilizatorul nu poate fi găsit")

    db_user.hashed_password = auth.get_password_hash(data.new_password)
    db.commit()
    return {"message": "Parola a fost schimbată cu succes!"}


@router.post("/change-username")
async def change_username(
    data: UsernameChange,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    existing = db.query(models.User).filter(models.User.username == data.new_username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Acest nume de utilizator este deja folosit.")

    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    db_user.username = data.new_username
    db.commit()

    new_token = auth.create_access_token(data={"sub": db_user.username, "role": db_user.role})
    return {"message": "Numele a fost schimbat cu succes!", "new_token": new_token}
