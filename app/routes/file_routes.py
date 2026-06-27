import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import or_, cast, String
from sqlalchemy.orm import Session



from app.events import manager

try:
    from app.auth import get_current_user, get_current_user_media
    from app.database import get_db
    from app.models import FileIndex, SharedFile, User
    from app.utils import get_user_path, safe_join_user_path, _calculate_storage_stats
    from app.schemas import FolderCreate, MoveRequest, CopyFilesRequest, RenameFolderRequest, DeleteMultipleRequest
except ImportError:
    from app.auth import get_current_user, get_current_user_media
    from app.database import get_db
    from app.models import FileIndex, SharedFile, User
    from app.utils import get_user_path, safe_join_user_path, _calculate_storage_stats
    from app.schemas import FolderCreate, MoveRequest, CopyFilesRequest, RenameFolderRequest, DeleteMultipleRequest

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
            "date": "Sincronizat",
            "owner_id": current_user.id
        })

    return formatted_results


@router.post("/create-folder")
async def create_folder(data: FolderCreate, current_user: User = Depends(get_current_user)):
    user_root = get_user_path(current_user.id)
    target_dir = safe_join_user_path(user_root, Path(data.path) / data.folder_name)

    if target_dir.exists():
        raise HTTPException(status_code=400, detail="Folderul există deja")

    target_dir.mkdir(parents=True, exist_ok=False)
    await manager.broadcast({"type": "REFRESH_FILES", "message": "Folder creat"})
    return {"message": "Folder creat cu succes!"}


@router.post("/move")
async def move_files(data: MoveRequest, current_user: User = Depends(get_current_user)):
    user_root = get_user_path(current_user.id)
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

    user_root = get_user_path(current_user.id)
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

    user_root = get_user_path(current_user.id)
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

@router.post("/sync-db")
def sync_database(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_root = get_user_path(current_user.id)

    db_files = db.query(FileIndex).filter(FileIndex.owner_id == current_user.id).all()
    db_file_map = {}
    for f in db_files:
        rel_path = os.path.normpath(os.path.join(getattr(f, 'folder_path', '') or "", f.filename))
        db_file_map[rel_path] = f

    disk_files_set = set()
    added_count = 0
    removed_count = 0

    for dirpath, dirnames, filenames in os.walk(user_root):
        # 1. Nu intra în foldere ascunse (.temp, .temp_uploads, .cache etc.)
        #    Modificarea lui dirnames "pe loc" oprește os.walk să coboare în ele.
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        for fname in filenames:
            # 2. Sări peste fișiere ascunse (.part, .DS_Store etc.)
            if fname.startswith("."):
                continue

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


@router.delete("/delete/{file_path:path}")
async def delete_file(file_path: str, current_user: User = Depends(get_current_user)):
    user_root = get_user_path(current_user.id)
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
    user_root = get_user_path(current_user.id)
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

@router.get("/dashboard")
def get_dashboard_data(path: str = "", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    media_exts = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.avi', '.mkv']

    # 1. MODIFICAT AICI: Folosim ID-ul pentru a afla folderul fizic!
    user_root = Path(get_user_path(current_user.id))

    categories = {"folders": [], "media": [], "documents": []}

    if path.startswith("Shared with me"):
        parts = path.split("/")

        if len(parts) == 1:
            shared_records = db.query(SharedFile).filter(SharedFile.shared_with_id == current_user.id).all()
            unique_owners = {r.owner_id for r in shared_records if not r.expires_at or r.expires_at > datetime.utcnow()}

            for owner_id in unique_owners:
                owner = db.query(User).filter(User.id == owner_id).first()
                if owner:
                    categories["folders"].append({
                        "name": owner.username,  # Aici rămâne username ca să arate frumos pe ecran
                        "path": f"Shared with me/{owner.username}",
                        "type": "folder",
                        "is_virtual": True
                    })

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
                        "owner_id": target_user.id,  # 2. MODIFICAT AICI: Trimitem ID-ul către React
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

    try:
        target_dir = safe_join_user_path(str(user_root), path)
        if isinstance(target_dir, str):
            target_dir = Path(target_dir)
    except ValueError:
        target_dir = user_root

    if not target_dir.exists():
        if path in ("", "."):
            target_dir = user_root
        else:
            target_dir.mkdir(parents=True, exist_ok=True)

    if path in ("", "."):
        categories["folders"].append({
            "name": "Shared with me",
            "path": "Shared with me",
            "type": "folder",
            "is_virtual": True,
        })

    if target_dir.exists() and target_dir.is_dir():
        for full_path in target_dir.iterdir():
            if full_path.name.startswith(".") or (path in ("", ".") and full_path.name == "Shared with me"):
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
                    "username": current_user.username,
                    "owner_id": current_user.id  # 3. MODIFICAT AICI: Trimitem ID-ul către React
                }
                if ext in media_exts:
                    categories["media"].append(file_info)
                else:
                    categories["documents"].append(file_info)

    return {
        "categories": categories,
        "storage_stats": _calculate_storage_stats(current_user, user_root)
    }


@router.get("/file-details/{file_path:path}")
def get_file_details(file_path: str, current_user: User = Depends(get_current_user)):
    user_root = get_user_path(current_user.id)
    full_path = safe_join_user_path(user_root, file_path)

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Fișier negăsit")

    stats = full_path.stat()
    mod_date = datetime.fromtimestamp(stats.st_mtime).strftime('%d %B %Y, %H:%M')
    return {
        "name": full_path.name,
        "modified": mod_date,
        "full_url": f"/media/{current_user.id}/{full_path.relative_to(user_root).as_posix()}"
    }


# ============================================================================
# NOU: Servire SECURIZATĂ a fișierelor (înlocuiește vechiul mount public /media)
# ============================================================================
@router.get("/media/{owner_id}/{file_path:path}")
def serve_media(
    owner_id: int,
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_media),
):
    """
    Servește un fișier fizic verificând permisiunile.
    Reguli de acces:
      - Dacă owner_id == utilizatorul curent -> e fișierul lui, are voie.
      - Altfel -> trebuie să existe un share VALID (neexpirat) către el
        pentru exact acea cale.
    Token-ul vine din ?token=... (sau header Authorization) prin
    dependența get_current_user_media.
    """
    # 1. Autorizare
    if owner_id != current_user.id:
        share = db.query(SharedFile).filter(
            SharedFile.owner_id == owner_id,
            SharedFile.shared_with_id == current_user.id,
            SharedFile.file_path == file_path,
        ).first()

        if not share:
            raise HTTPException(status_code=403, detail="Nu ai acces la acest fișier.")
        if share.expires_at and share.expires_at < datetime.utcnow():
            raise HTTPException(status_code=403, detail="Accesul partajat a expirat.")

    # 2. Rezolvăm calea fizică în siguranță (anti path-traversal)
    owner_root = get_user_path(owner_id)
    try:
        full_path = safe_join_user_path(owner_root, file_path)
    except ValueError:
        raise HTTPException(status_code=400, detail="Cale invalidă.")

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="Fișier negăsit.")

    # FileResponse fără filename => servire inline (bun pentru <img>/<video>)
    return FileResponse(path=str(full_path))