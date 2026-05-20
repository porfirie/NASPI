import asyncio
import io
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import or_, cast, String
from sqlalchemy.orm import Session

from events import manager, ai_state  # asigura-te ca il imporți corect
import time # Ai nevoie de time pentru sleep

try:
    from auth import get_current_user
    from database import SessionLocal, get_db
    from events import manager
    from models import FileIndex, SharedFile, User
    from services.ai_service import process_image_with_ai
    from utils import get_dir_size, get_user_path, safe_join_user_path
except ImportError:
    from app.auth import get_current_user
    from app.database import SessionLocal, get_db
    from app.events import manager
    from app.models import FileIndex, SharedFile, User
    from app.services.ai_service import process_image_with_ai
    from app.utils import get_dir_size, get_user_path, safe_join_user_path

router = APIRouter()


@router.get("/search")
def search_files(q: str, use_ai: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not q or q.strip() == "":
        return []

    base_query = db.query(FileIndex).filter(FileIndex.owner_id == current_user.id)

    if use_ai:
        results = base_query.filter(FileIndex.ai_tags.ilike(f"%{q}%")).all()
    else:
        results = base_query.filter(
            or_(
                FileIndex.filename.ilike(f"%{q}%"),
                cast(FileIndex.size_kb, String).ilike(f"%{q}%")
            )
        ).all()

    formatted_results = []
    for f in results:
        folder = getattr(f, 'folder_path', '') or "Root"
        formatted_results.append({
            "id": str(f.id),
            "name": f.filename,
            "path": folder,
            "size": f.size_kb,
            "date": "Sincronizat"
        })

    return formatted_results


class FolderCreate(BaseModel):
    path: str
    folder_name: str


class MoveRequest(BaseModel):
    source_paths: List[str]
    destination_folder: str


class DeleteMultipleRequest(BaseModel):
    filenames: List[str]


class CopyFilesRequest(BaseModel):
    source_paths: List[str]
    destination_folder: str


class RenameFolderRequest(BaseModel):
    folder_path: str
    new_name: str


@router.post("/create-folder")
async def create_folder(data: FolderCreate, current_user: User = Depends(get_current_user)):
    user_root = get_user_path(current_user.username)
    target_dir = safe_join_user_path(user_root, Path(data.path) / data.folder_name)

    if target_dir.exists():
        raise HTTPException(status_code=400, detail="Folderul există deja")

    target_dir.mkdir(parents=True, exist_ok=False)
    await manager.broadcast({"type": "REFRESH_FILES", "message": "Folder creat"})
    return {"message": "Folder creat cu succes!"}


@router.post("/move")
async def move_files(data: MoveRequest, current_user: User = Depends(get_current_user)):
    user_root = get_user_path(current_user.username)
    dest_dir = safe_join_user_path(user_root, data.destination_folder, create=True)

    errors = []
    for rel_path in data.source_paths:
        try:
            source_full_path = safe_join_user_path(user_root, rel_path)
        except ValueError:
            errors.append(f"Cale invalidă: {rel_path}")
            continue

        if source_full_path.exists():
            try:
                final_dest = dest_dir / source_full_path.name
                if final_dest.exists():
                    errors.append(f"Fișierul {source_full_path.name} există deja la destinație.")
                    continue
                source_full_path.replace(final_dest)
            except Exception as e:
                errors.append(f"Eroare la mutarea {rel_path}: {e}")

    await manager.broadcast({"type": "REFRESH_FILES", "message": "Files moved"})
    return {"status": "ok", "errors": errors}


@router.post("/copy-files")
async def copy_files(data: CopyFilesRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if data.destination_folder.startswith("Shared with me"):
        raise HTTPException(status_code=400, detail="Nu poți copia fișiere direct în folderul 'Shared with me'.")

    user_root = get_user_path(current_user.username)
    dest_dir = safe_join_user_path(user_root, data.destination_folder, create=True)

    errors = []
    for rel_path in data.source_paths:
        try:
            source_full_path = safe_join_user_path(user_root, rel_path)
        except ValueError:
            errors.append(f"Cale invalidă: {rel_path}")
            continue

        if not source_full_path.exists():
            errors.append(f"Fișierul {rel_path} nu există.")
            continue

        if source_full_path.is_dir():
            errors.append(f"Nu poți copia directoare. Selectează doar fișiere: {rel_path}")
            continue

        final_dest = dest_dir / source_full_path.name
        if final_dest.exists():
            errors.append(f"Fișierul {source_full_path.name} există deja la destinație.")
            continue

        try:
            shutil.copy2(source_full_path, final_dest)
            new_file_index = FileIndex(
                filename=source_full_path.name,
                folder_path=data.destination_folder,
                size_kb=round(final_dest.stat().st_size / 1024, 2),
                owner_id=current_user.id,
            )
            db.add(new_file_index)
        except Exception as e:
            errors.append(f"Eroare la copierea {rel_path}: {e}")

    db.commit()
    await manager.broadcast({"type": "REFRESH_FILES", "message": "Files copied"})
    return {"status": "ok", "errors": errors}


@router.post("/rename-folder")
async def rename_folder(data: RenameFolderRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not data.folder_path or data.folder_path.startswith("Shared with me"):
        raise HTTPException(status_code=400, detail="Folderul selectat nu poate fi redenumit.")

    if not data.new_name or data.new_name.strip() == "" or "/" in data.new_name or data.new_name in (".", ".."):
        raise HTTPException(status_code=400, detail="Nume de folder invalid.")

    user_root = get_user_path(current_user.username)
    old_folder = safe_join_user_path(user_root, data.folder_path)
    if not old_folder.exists() or not old_folder.is_dir():
        raise HTTPException(status_code=404, detail="Folderul nu a fost găsit.")

    new_folder_path = old_folder.parent / data.new_name
    if new_folder_path.exists():
        raise HTTPException(status_code=400, detail="Există deja un folder cu acest nume în aceeași locație.")

    try:
        old_folder.replace(new_folder_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Eroare la redenumire: {e}")

    prefix = data.folder_path.rstrip('/')
    if '/' in prefix:
        parent_prefix = '/'.join(prefix.split('/')[:-1])
        new_prefix = f"{parent_prefix}/{data.new_name}"
    else:
        new_prefix = data.new_name

    file_records = db.query(FileIndex).filter(
        FileIndex.owner_id == current_user.id,
        or_(FileIndex.folder_path == prefix, FileIndex.folder_path.like(f"{prefix}/%"))
    ).all()

    for record in file_records:
        if record.folder_path == prefix:
            record.folder_path = new_prefix
        else:
            suffix = record.folder_path[len(prefix):]
            if suffix.startswith('/'):
                suffix = suffix[1:]
            record.folder_path = f"{new_prefix}/{suffix}" if new_prefix else suffix

    db.commit()
    await manager.broadcast({"type": "REFRESH_FILES", "message": "Folder redenumit"})
    return {"status": "ok", "new_path": new_prefix}


def ai_worker_sync(file_id: int, image_path: str):
    db_session = SessionLocal()
    try:
        process_image_with_ai(file_id, image_path, db_session)
    finally:
        db_session.close()


async def ai_background_worker(file_id: int, image_path: str):
    try:
        # 1. Cât timp e pe pauză, firul de execuție așteaptă liniștit
        while ai_state.status == "paused":
            await asyncio.sleep(2)
            
        # 2. Dacă a fost oprit (stop), anulăm task-ul complet
        if ai_state.status == "stopped":
            return
            
        filename = os.path.basename(image_path)
        ai_state.log(f"AI ENGINE: A preluat '{filename}'. Procesare...", "warning")
        
        # Procesarea reală
        await asyncio.to_thread(ai_worker_sync, file_id, image_path)
        
        ai_state.log(f"AI ENGINE: Analiză completă pentru '{filename}'.", "success")
    except Exception as e:
        ai_state.log(f"EROARE AI: {str(e)}", "error")
    finally:
        # Când termină, scade numărul din coadă, dar să nu scadă sub 0
        ai_state.queue_count = max(0, ai_state.queue_count - 1)


@router.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    target_path: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if target_path.startswith("Shared with me"):
        raise HTTPException(status_code=400, detail="Nu poți încărca fișiere direct în folderul 'Shared with me'.")

    user_root = get_user_path(current_user.username)
    target_dir = safe_join_user_path(user_root, target_path, create=True)

    current_size_bytes = get_dir_size(user_root)
    incoming_size_bytes = 0
    for f in files:
        f.file.seek(0, os.SEEK_END)
        incoming_size_bytes += f.file.tell()
        f.file.seek(0)

    if (current_size_bytes + incoming_size_bytes) > (current_user.storage_quota_mb * 1024 * 1024):
        raise HTTPException(status_code=400, detail="Cotă depășită!")

    # Aici vom ține minte dacă a picat vreun fișier
    errors = []
    files_uploaded = False

    for file in files:
        file_location = target_dir / file.filename
        
        # 🚨 PROTECȚIA NOUĂ: Verificăm dacă fișierul fizic există deja pe disc!
        if file_location.exists():
            errors.append(f"Fișierul '{file.filename}' există deja.")
            continue # Sărim peste el, nu îl salvăm pe disc și nu îl punem în DB

        # 1. Salvăm fizic pe disc
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Adăugăm în baza de date o singură dată
        new_file_index = FileIndex(
            filename=file.filename,
            folder_path=target_path,
            size_kb=round(file_location.stat().st_size / 1024, 2),
            owner_id=current_user.id,
        )
        db.add(new_file_index)
        db.flush()
        db.refresh(new_file_index)
        
        # 3. Trimitem la AI
        background_tasks.add_task(ai_background_worker, new_file_index.id, str(file_location))
        files_uploaded = True

        ai_state.queue_count += 1
        ai_state.log(f"UPLOAD: '{file.filename}' salvat.", "info")

    db.commit()
    
    if files_uploaded:
        await manager.broadcast({"type": "REFRESH_FILES", "message": "New upload"})
        
    # Dacă au fost erori (fișiere dublate), trimitem la Frontend ca să îți arate pop-up
    if errors:
        raise HTTPException(status_code=400, detail=" | ".join(errors))

    return {"status": "ok"}

@router.post("/sync-db")
def sync_database(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_root = get_user_path(current_user.username)

    db_files = db.query(FileIndex).filter(FileIndex.owner_id == current_user.id).all()
    db_file_map = {}
    for f in db_files:
        rel_path = os.path.normpath(os.path.join(getattr(f, 'folder_path', '') or "", f.filename))
        db_file_map[rel_path] = f

    disk_files_set = set()
    added_count = 0
    removed_count = 0

    for dirpath, _, filenames in os.walk(user_root):
        for fname in filenames:
            file_path = os.path.join(dirpath, fname)
            rel_dir = os.path.relpath(dirpath, user_root)
            if rel_dir == ".":
                rel_dir = ""
            rel_full_path = os.path.normpath(os.path.join(rel_dir, fname))
            disk_files_set.add(rel_full_path)
            if rel_full_path not in db_file_map:
                size_kb = round(os.path.getsize(file_path) / 1024, 1)
                new_idx = FileIndex(
                    filename=fname,
                    folder_path=rel_dir,
                    size_kb=size_kb,
                    owner_id=current_user.id,
                    ai_tags=""
                )
                db.add(new_idx)
                added_count += 1

    for rel_full_path, db_record in db_file_map.items():
        if rel_full_path not in disk_files_set:
            db.delete(db_record)
            removed_count += 1

    db.commit()
    return {"message": "Sincronizare completă!", "added": added_count, "removed": removed_count}


@router.get("/download/{file_path:path}")
def download_file(file_path: str, current_user: User = Depends(get_current_user)):
    user_root = get_user_path(current_user.username)
    full_path = safe_join_user_path(user_root, file_path)

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="Fișierul nu a fost găsit.")

    return FileResponse(path=str(full_path), filename=full_path.name, media_type='application/octet-stream')


@router.delete("/delete/{file_path:path}")
async def delete_file(file_path: str, current_user: User = Depends(get_current_user)):
    user_root = get_user_path(current_user.username)
    full_path = safe_join_user_path(user_root, file_path)

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Fișier negăsit")

    try:
        if full_path.is_dir():
            shutil.rmtree(full_path)
        else:
            full_path.unlink()
        await manager.broadcast({"type": "REFRESH_FILES", "message": "Deleted"})
        return {"message": "Șters cu succes"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete-multiple")
async def delete_multiple(data: DeleteMultipleRequest, current_user: User = Depends(get_current_user)):
    user_root = get_user_path(current_user.username)
    deleted = []
    errors = []

    for filename in data.filenames:
        try:
            file_path = safe_join_user_path(user_root, filename)
        except ValueError:
            errors.append(f"Cale invalidă: {filename}")
            continue

        if file_path.exists():
            try:
                if file_path.is_dir():
                    shutil.rmtree(file_path)
                else:
                    file_path.unlink()
                deleted.append(filename)
            except Exception as e:
                errors.append(f"Eroare la {filename}: {e}")

    if deleted:
        await manager.broadcast({"type": "REFRESH_FILES", "message": f"Files deleted: {', '.join(deleted)}"})

    return {"message": "Proces finalizat", "deleted": deleted, "errors": errors}


# --- FUNCȚIE AJUTĂTOARE (Pusă deasupra rutei de dashboard) ---
def _calculate_storage_stats(current_user: User, user_root: Path) -> dict:
    """Calculează statisticile de stocare o singură dată pentru a păstra codul curat."""
    user_quota_mb = current_user.storage_quota_mb
    used_mb = get_dir_size(user_root) / (1024 * 1024)
    free_mb = max(0, user_quota_mb - used_mb)
    percent_used = (used_mb / user_quota_mb) * 100 if user_quota_mb > 0 else 100

    return {
        "total_gb": round(user_quota_mb / 1024, 2),
        "used_gb": round(used_mb / 1024, 2),
        "free_gb": round(free_mb / 1024, 2),
        "app_usage_mb": round(used_mb, 2),
        "percent_used": round(percent_used, 1),
        "user_role": current_user.role
    }


@router.get("/dashboard")
def get_dashboard_data(path: str = "", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    media_exts = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.avi', '.mkv']
    user_root = Path(get_user_path(current_user.username))
    categories = {"folders": [], "media": [], "documents": []}

    # ==========================================
    # 1. SCENARIUL A: FOLDERUL VIRTUAL DE SHARE
    # ==========================================
    if path.startswith("Shared with me"):
        parts = path.split("/")
        
        # NIVELUL 1: Rădăcina "Shared with me" (Arată Userii)
        if len(parts) == 1:
            shared_records = db.query(SharedFile).filter(SharedFile.shared_with_id == current_user.id).all()
            unique_owners = {r.owner_id for r in shared_records if not r.expires_at or r.expires_at > datetime.utcnow()}
            
            for owner_id in unique_owners:
                owner = db.query(User).filter(User.id == owner_id).first()
                if owner:
                    categories["folders"].append({
                        "name": owner.username,
                        "path": f"Shared with me/{owner.username}",
                        "type": "folder",
                        "is_virtual": True
                    })

        # NIVELUL 2: Conținutul unui user specific
        elif len(parts) == 2:
            target_user = db.query(User).filter(User.username == parts[1]).first()
            if target_user:
                shared_records = db.query(SharedFile).filter(
                    SharedFile.shared_with_id == current_user.id,
                    SharedFile.owner_id == target_user.id
                ).all()
                
                for record in shared_records:
                    if record.expires_at and record.expires_at < datetime.utcnow():
                        continue
                    ext = Path(record.filename).suffix.lower()
                    file_info = {
                        "name": record.filename,
                        "path": record.file_path,
                        "size": 0,
                        "username": target_user.username,
                        "is_shared": True
                    }
                    if ext in media_exts:
                        categories["media"].append(file_info)
                    else:
                        categories["documents"].append(file_info)

        return {
            "categories": categories,
            "storage_stats": _calculate_storage_stats(current_user, user_root)
        }

    # ==========================================
    # 2. SCENARIUL B: FOLDERE FIZICE NORMALE
    # ==========================================
    try:
        target_dir = safe_join_user_path(str(user_root), path)
        if isinstance(target_dir, str):
            target_dir = Path(target_dir)
    except ValueError:
        target_dir = user_root

    # 🚨 REPARAȚIA AICI: Fără fallback ascuns la Root!
    if not target_dir.exists():
        if path in ("", "."):
            target_dir = user_root
        else:
            # Auto-reparare: creăm folderul dacă React crede că suntem în el, dar discul e desincronizat
            target_dir.mkdir(parents=True, exist_ok=True)

    # Injectăm manual folderul "Shared with me" doar dacă suntem în rădăcină (HOME)
    if path in ("", "."):
        categories["folders"].append({
            "name": "Shared with me",
            "path": "Shared with me",
            "type": "folder",
            "is_virtual": True,
        })

    # Scanăm fișierele reale de pe disc
    if target_dir.exists() and target_dir.is_dir():
        for full_path in target_dir.iterdir():
            if full_path.name in (".", "..") or (path in ("", ".") and full_path.name == "Shared with me"):
                continue
                
            rel_path = full_path.relative_to(user_root).as_posix()
            if full_path.is_dir():
                categories["folders"].append({"name": full_path.name, "path": rel_path, "type": "folder"})
            elif full_path.is_file():
                size = full_path.stat().st_size
                ext = full_path.suffix.lower()
                file_info = {
                    "name": full_path.name,
                    "path": rel_path,
                    "size": round(size / 1024, 2),
                    "username": current_user.username
                }
                if ext in media_exts:
                    categories["media"].append(file_info)
                else:
                    categories["documents"].append(file_info)

    # Returnăm datele finale
    return {
        "categories": categories,
        "storage_stats": _calculate_storage_stats(current_user, user_root)
    }


@router.get("/file-details/{file_path:path}")
def get_file_details(file_path: str, current_user: User = Depends(get_current_user)):
    user_root = get_user_path(current_user.username)
    full_path = safe_join_user_path(user_root, file_path)

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Fișier negăsit")

    stats = full_path.stat()
    mod_date = datetime.fromtimestamp(stats.st_mtime).strftime('%d %B %Y, %H:%M')
    return {
        "name": full_path.name,
        "modified": mod_date,
        "full_url": f"/media/{current_user.username}/{full_path.relative_to(user_root).as_posix()}"
    }


@router.post("/download-zip")
def download_zip(filenames: List[str], current_user: User = Depends(get_current_user)):
    user_root = get_user_path(current_user.username)
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for fname in filenames:
            clean_fname = fname.replace("\\", "/").strip("/")
            try:
                fpath = safe_join_user_path(user_root, clean_fname)
            except ValueError:
                continue
            if fpath.exists() and fpath.is_file():
                zip_file.write(str(fpath), arcname=clean_fname)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="Aether_Files.zip"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

class AIControlRequest(BaseModel):
    action: str

@router.post("/ai/control")
def control_ai(data: AIControlRequest, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Fără acces.")
        
    if data.action == "play":
        ai_state.status = "running"
        ai_state.log("Sistem AI REPORNIT de către admin.", "success")
    elif data.action == "pause":
        ai_state.status = "paused"
        ai_state.log("Sistem AI pus în PAUZĂ.", "warning")
    elif data.action == "stop":
        ai_state.status = "stopped"
        ai_state.queue_count = 0
        ai_state.log("Sistem AI OPRIT. Coada a fost golită forțat.", "error")
        
    return {"status": ai_state.status}