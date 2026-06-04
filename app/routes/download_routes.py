import uuid
import zipfile
import time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List

# (Presupun că imporți funcțiile tale de auth din alt fișier, ex: auth.py)
from app.auth import get_current_user
from app.models import User
from app.utils import get_user_path, safe_join_user_path

# Inițializăm router-ul pentru acest fișier
router = APIRouter()

# Dicționarul din memoria RAM
zip_sessions = {}

class DownloadZipRequest(BaseModel):
    paths: List[str]

@router.post("/prepare-zip")
def prepare_zip(data: DownloadZipRequest, current_user: User = Depends(get_current_user)):
    user_root = get_user_path(current_user.id)
    valid_files = []
    
    for fname in data.paths:
        clean_fname = fname.replace("\\", "/").strip("/")
        try:
            fpath = safe_join_user_path(user_root, clean_fname)
            if fpath.exists() and fpath.is_file():
                valid_files.append((fpath, clean_fname))
        except ValueError:
            continue

    if not valid_files:
        raise HTTPException(status_code=400, detail="Niciun fișier valid selectat.")

    # 1. Creăm un folder invizibil ".temp" în folderul utilizatorului
    temp_dir = Path(user_root) / ".temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 2. Auto-Curățare DISK: Ștergem arhivele mai vechi de 1 oră
    current_time = time.time()
    for f in temp_dir.glob("*.zip"):
        if current_time - f.stat().st_mtime > 3600:
            try:
                f.unlink()
            except Exception:
                pass

    # 🚨 NOU: Auto-Curățare RAM (Evităm Memory Leak-ul)
    # Ștergem din dicționar toate sesiunile ale căror fișiere nu mai există fizic
    expired_sessions = [sid for sid, path in zip_sessions.items() if not Path(path).exists()]
    for sid in expired_sessions:
        del zip_sessions[sid]

    # 3. Creăm arhiva fizic pe disc
    session_id = str(uuid.uuid4())
    zip_path = temp_dir / f"Aether_{session_id}.zip"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fpath, arcname in valid_files:
            zf.write(fpath, arcname=arcname)

    # Salvăm calea fișierului în memoria Pi-ului
    zip_sessions[session_id] = str(zip_path)
    
    return {"session_id": session_id}


@router.get("/download-zip/{session_id}")
def download_zip_file(session_id: str):
    if session_id not in zip_sessions:
        raise HTTPException(status_code=404, detail="Sesiune expirată sau invalidă.")
        
    zip_path = Path(zip_sessions[session_id])
    if not zip_path.exists():
        # Dacă fișierul a fost șters, curățăm și dicționarul rapid
        del zip_sessions[session_id]
        raise HTTPException(status_code=404, detail="Fișierul arhivat nu mai există pe disc.")

    # 4. Returnăm fișierul FIZIC
    return FileResponse(
        path=str(zip_path),
        filename="Aether_Files.zip",
        media_type="application/zip",
        headers={'Accept-Ranges': 'bytes'} # Super bine pus!
    )