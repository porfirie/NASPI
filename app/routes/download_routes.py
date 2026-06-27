import uuid
import zipfile
import time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List

from app.auth import get_current_user, get_current_user_media
from app.models import User
from app.utils import get_user_path, safe_join_user_path

# Inițializăm router-ul pentru acest fișier
router = APIRouter()

# Dicționarul din memoria RAM.
# ACUM stocăm și owner_id-ul, ca să legăm fiecare sesiune de utilizatorul care a creat-o.
zip_sessions = {}


class DownloadZipRequest(BaseModel):
    paths: List[str]


# ============================================================================
# NOU: Descărcare SECURIZATĂ a unui singur fișier.
# Repară butonul din Dashboard care trimitea către /download/{path} (inexistent).
# Folosește get_current_user_media pentru că window.location.href (navigare browser)
# nu poate trimite header Authorization -> token vine din ?access_token=... sau ?token=...
# ============================================================================
@router.get("/download/{file_path:path}")
def download_single_file(
    file_path: str,
    current_user: User = Depends(get_current_user_media),
):
    user_root = get_user_path(current_user.id)

    clean_path = file_path.replace("\\", "/").strip("/")
    try:
        full_path = safe_join_user_path(user_root, clean_path)
    except ValueError:
        raise HTTPException(status_code=400, detail="Cale invalidă.")

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="Fișier negăsit.")

    # filename + media_type 'application/octet-stream' forțează descărcarea
    # (Content-Disposition: attachment), nu afișarea inline în browser.
    return FileResponse(
        path=str(full_path),
        filename=full_path.name,
        media_type="application/octet-stream",
    )


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

    # Auto-Curățare RAM: scoatem din dicționar sesiunile ale căror fișiere nu mai există
    expired_sessions = [sid for sid, info in zip_sessions.items() if not Path(info["path"]).exists()]
    for sid in expired_sessions:
        del zip_sessions[sid]

    # 3. Creăm arhiva fizic pe disc
    session_id = str(uuid.uuid4())
    zip_path = temp_dir / f"Aether_{session_id}.zip"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fpath, arcname in valid_files:
            zf.write(fpath, arcname=arcname)

    # Salvăm calea + proprietarul, ca să putem verifica la descărcare cine are voie.
    zip_sessions[session_id] = {"path": str(zip_path), "owner_id": current_user.id}

    return {"session_id": session_id}


@router.get("/download-zip/{session_id}")
def download_zip_file(
    session_id: str,
    current_user: User = Depends(get_current_user_media),
):
    info = zip_sessions.get(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="Sesiune expirată sau invalidă.")

    # SECURIZARE: doar utilizatorul care a creat arhiva o poate descărca.
    if info["owner_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Nu ai acces la această arhivă.")

    zip_path = Path(info["path"])
    if not zip_path.exists():
        # Dacă fișierul a fost șters, curățăm și dicționarul rapid
        del zip_sessions[session_id]
        raise HTTPException(status_code=404, detail="Fișierul arhivat nu mai există pe disc.")

    return FileResponse(
        path=str(zip_path),
        filename="Aether_Files.zip",
        media_type="application/zip",
        headers={'Accept-Ranges': 'bytes'}
    )