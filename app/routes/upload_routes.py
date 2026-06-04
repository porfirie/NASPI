import os
import shutil
import hashlib
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import FileIndex, User
from app.utils import get_dir_size, get_user_path, safe_join_user_path, get_temp_file_path
from app.services.ai_service import ai_background_worker
from app.events import manager, ai_state

router = APIRouter()



@router.get("/upload/status")
def check_upload_status(
    filename: str = Query(...),
    target_path: str = Query(""),
    total_size: int = Query(...),
    current_user: User = Depends(get_current_user)
):
    """
    PASUL 1: Handshake-ul. React ne întreabă de unde să înceapă.
    """
    if target_path.startswith("Shared with me"):
        raise HTTPException(status_code=400, detail="Nu poți încărca direct în 'Shared with me'.")

    user_root = get_user_path(current_user.username)
    target_dir = safe_join_user_path(user_root, target_path, create=True)
    final_file_path = target_dir / filename

    # Verificăm dacă fișierul există deja la destinația finală
    if final_file_path.exists():
        raise HTTPException(status_code=400, detail=f"Fișierul '{filename}' există deja.")

    # Verificare cotă înainte să primim vreun byte
    current_size_bytes = get_dir_size(user_root)
    if (current_size_bytes + total_size) > (current_user.storage_quota_mb * 1024 * 1024):
        raise HTTPException(status_code=400, detail="Cotă depășită!")

    # Verificăm dacă avem deja o bucată din acest fișier descărcată anterior
    temp_file = get_temp_file_path(user_root, target_path, filename)
    if temp_file.exists():
        return {"uploadedBytes": temp_file.stat().st_size}
        
    return {"uploadedBytes": 0}


@router.post("/upload/chunk")
async def upload_chunk(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    filename: str = Form(...),
    target_path: str = Form(""),
    offset: int = Form(...),
    total_size: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    PASUL 2: Primirea feliilor și asamblarea finală.
    """
    if target_path.startswith("Shared with me"):
        raise HTTPException(status_code=400, detail="Eroare permisiuni.")

    user_root = get_user_path(current_user.username)
    target_dir = safe_join_user_path(user_root, target_path, create=True)
    final_file_path = target_dir / filename

    temp_file = get_temp_file_path(user_root, target_path, filename)

    # 1. Lipim felia primită la fișierul temporar
    # "ab" înseamnă Append Binary. Dacă e prima bucată (offset 0), folosim "wb" (Write Binary)
    mode = "ab" if offset > 0 else "wb"
    with open(temp_file, mode) as buffer:
        shutil.copyfileobj(file.file, buffer)

    current_temp_size = temp_file.stat().st_size

    # 2. Verificăm dacă am terminat tot fișierul
    if current_temp_size >= total_size:
        # Fișierul e complet! Îl mutăm la locul lui final.
        shutil.move(str(temp_file), str(final_file_path))

        # Adăugăm în Baza de Date
        new_file_index = FileIndex(
            filename=filename,
            folder_path=target_path,
            size_kb=round(final_file_path.stat().st_size / 1024, 2),
            owner_id=current_user.id,
        )
        db.add(new_file_index)
        db.commit()
        db.refresh(new_file_index)

        # Trimitem la AI Worker
        background_tasks.add_task(ai_background_worker, new_file_index.id, str(final_file_path))
        ai_state.queue_count += 1
        ai_state.log(f"UPLOAD: '{filename}' salvat.", "info")

        # Anunțăm interfața să dea refresh
        await manager.broadcast({"type": "REFRESH_FILES", "message": "New upload"})
        
        return {"status": "completed", "filename": filename}

    # Dacă nu e gata, spunem interfeței să trimită următoarea bucată
    return {"status": "uploading", "uploadedBytes": current_temp_size}