import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

try:
    from auth import get_current_user
    from app.database import get_db
    import app.models
    from utils import get_user_path, safe_join_user_path
except ImportError:
    from app.auth import get_current_user
    from app.database import get_db
    from app import models
    from app.utils import get_user_path, safe_join_user_path

router = APIRouter()


class ShareRequest(BaseModel):
    file_paths: List[str]
    expiration: str = "24h"


class InternalShareRequest(BaseModel):
    file_paths: List[str]
    target_username: str
    expiration_hours: int = 24


@router.post("/share-multiple")
async def share_multiple_files(request: ShareRequest, current_user: models.User = Depends(get_current_user)):
    if not request.file_paths:
        raise HTTPException(status_code=400, detail="Nu ai selectat niciun fișier.")

    user_root = get_user_path(current_user.username)
    bin_id = str(uuid.uuid4())
    uploaded_count = 0
    errors = []

    async with httpx.AsyncClient(timeout=120) as client:
        for rel_path in request.file_paths:
            try:
                full_path = safe_join_user_path(user_root, rel_path)
                if not full_path.exists() or not full_path.is_file():
                    errors.append(f"Fișierul nu a fost găsit: {rel_path}")
                    continue

                with full_path.open('rb') as f:
                    url = f"https://filebin.net/{bin_id}/{full_path.name}"
                    headers = {'Expiration': request.expiration}
                    response = await client.put(url, content=f.read(), headers=headers)
                    if response.status_code == 201:
                        uploaded_count += 1
                    else:
                        errors.append(f"Eroare la {full_path.name}")
            except Exception as e:
                errors.append(f"Eroare locală la {rel_path}: {str(e)}")

    if uploaded_count == 0:
        raise HTTPException(status_code=500, detail="Niciun fișier nu a putut fi încărcat.")

    return {"link": f"https://filebin.net/{bin_id}", "uploaded": uploaded_count, "errors": errors}


@router.post("/share-internal")
async def share_internal(data: InternalShareRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    target_user = db.query(models.User).filter(models.User.username == data.target_username).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilizatorul nu a fost găsit în Aether.")
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Nu îți poți da share singur!")

    exp_date = datetime.utcnow() + timedelta(hours=data.expiration_hours)
    for filepath in data.file_paths:
        filename = Path(filepath).name
        new_share = models.SharedFile(
            owner_id=current_user.id,
            shared_with_id=target_user.id,
            file_path=filepath,
            filename=filename,
            expires_at=exp_date,
        )
        db.add(new_share)

    db.commit()
    return {"message": f"Fișiere partajate cu succes cu {data.target_username}!"}
