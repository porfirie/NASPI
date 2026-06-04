from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import shutil
from sqlalchemy import or_
from app.utils import get_user_path

try:
    import auth
    from auth import get_current_user
    from app.database import get_db
    import models
    from schemas import UserCreate, UserEdit
except ImportError:
    from app import auth
    from app.auth import get_current_user
    from app.database import get_db
    from app import models
    from app.schemas import UserCreate, UserEdit

router = APIRouter()


@router.get("/admin/users")
def get_users(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="DOAR ADMINUL ARE ACCES")
    users = db.query(models.User).all()
    return [{"id": u.id, "username": u.username, "role": u.role, "storage_quota_mb": u.storage_quota_mb} for u in users]


@router.post("/admin/users")
def create_user(user_data: UserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="DOAR ADMINUL ARE ACCES")

    if db.query(models.User).filter(models.User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="UTILIZATORUL EXISTĂ DEJA")

    new_user = models.User(
        username=user_data.username,
        hashed_password=auth.get_password_hash(user_data.password),
        role=user_data.role,
        storage_quota_mb=user_data.storage_quota_mb,
    )
    db.add(new_user)
    db.commit()
    return {"message": "Utilizator creat"}


@router.put("/admin/users/{user_id}")
def edit_user(user_id: int, data: UserEdit, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="DOAR ADMINUL ARE ACCES")

    user_to_edit = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_to_edit:
        raise HTTPException(status_code=404, detail="Utilizatorul nu există.")

    user_to_edit.role = data.role
    user_to_edit.storage_quota_mb = data.storage_quota_mb
    db.commit()
    return {"message": "Utilizator actualizat."}


@router.delete("/admin/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="DOAR ADMINUL ARE ACCES")

    user_to_delete = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="USERUL NU EXISTĂ")

    if user_to_delete.id == current_user.id:
        raise HTTPException(status_code=400, detail="NU TE POȚI ȘTERGE SINGUR")

    try:
        # 1. CURĂȚARE HARD DISK
        user_folder = get_user_path(user_to_delete.id)
        if user_folder.exists() and user_folder.is_dir():
            shutil.rmtree(user_folder)

        # 2. CURĂȚARE BAZĂ DE DATE (Share-uri și Index-uri)
        db.query(models.SharedFile).filter(
            or_(models.SharedFile.owner_id == user_to_delete.id, 
                models.SharedFile.shared_with_id == user_to_delete.id)
        ).delete(synchronize_session=False)

        db.query(models.FileIndex).filter(models.FileIndex.owner_id == user_to_delete.id).delete(synchronize_session=False)

        # 3. ȘTERGERE CONT
        db.delete(user_to_delete)
        db.commit()
        return {"message": "Utilizatorul și toate fișierele sale au fost șterse complet."}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Eroare la curățarea datelor: {e}")