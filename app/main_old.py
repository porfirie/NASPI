import os
import shutil
import platform 
import psutil
import asyncio 
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status
from fastapi.responses import FileResponse 
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import zipfile
import tempfile
from fastapi import BackgroundTasks
from pydantic import BaseModel
from typing import List
from fastapi import WebSocket, WebSocketDisconnect
from fastapi import Form

from fastapi import BackgroundTasks

from sqlalchemy import or_, cast, String

import os

from sqlalchemy.orm import Session
from fastapi import Depends


from app.database import SessionLocal # Importăm "fabrica" de conexiuni la DB
from vision import process_image_with_ai # Importăm funcția noastră AI

import traceback 

# Importurile tale locale
import app.auth
import app.models
from app.database import engine, Base, get_db



from pydantic import BaseModel
from typing import List
import requests
import uuid


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()
# Adăugăm variabile globale pentru a reține valorile anterioare de rețea
# --- CODUL CORECTAT PENTRU MONITORIZARE ---
prev_net_sent = psutil.net_io_counters().bytes_sent
prev_net_recv = psutil.net_io_counters().bytes_recv

async def monitor_system():
    global prev_net_sent, prev_net_recv
    while True:
        try:
            # 1. CPU
            cpu = psutil.cpu_percent(interval=None)
            
            # 2. RAM (Corectat)
            ram_info = psutil.virtual_memory()
            # Calculăm clar și rotunjim la 2 zecimale
            ram_total_gb = round(ram_info.total / (1024 ** 3), 2)
            ram_used_gb = round(ram_info.used / (1024 ** 3), 2)
            # Ne asigurăm că procentul este corect raportat
            ram_percent = ram_info.percent
            
            # 3. DISK (Corectat pentru siguranță)
            disk = shutil.disk_usage("/")
            disk_total_gb = round(disk.total / (1024 ** 3), 2)
            disk_used_gb = round(disk.used / (1024 ** 3), 2)
            disk_percent = round((disk.used / disk.total) * 100, 1)
            
            # 4. NETWORK (Viteză în KB/s)
            curr_net = psutil.net_io_counters()
            up_speed = round((curr_net.bytes_sent - prev_net_sent) / (2 * 1024), 1)
            down_speed = round((curr_net.bytes_recv - prev_net_recv) / (2 * 1024), 1)
            
            prev_net_sent = curr_net.bytes_sent
            prev_net_recv = curr_net.bytes_recv

            # 5. TEMPERATURĂ (Ignorăm în siguranță dacă eșuează pe Windows)
            temp = 0
            try:
                temps = psutil.sensors_temperatures()
                if 'cpu_thermal' in temps: temp = temps['cpu_thermal'][0].current
                elif 'coretemp' in temps: temp = temps['coretemp'][0].current # Pe unele sisteme Linux
            except: 
                pass

            # 6. Trimitem datele
            stats = {
                "type": "SYSTEM_STATS",
                "cpu": cpu,
                "ram_percent": ram_percent,
                "ram_used_gb": ram_used_gb,
                "ram_total_gb": ram_total_gb,
                "disk_percent": disk_percent,
                "disk_used_gb": disk_used_gb,
                "disk_total_gb": disk_total_gb,
                "up_speed": up_speed,
                "down_speed": down_speed,
                "temp": temp,
                "active_connections": len(manager.active_connections)
            }
            await manager.broadcast(stats)
            
        except Exception as e:
            print(f"Eroare monitorizare: {e}")
            
        await asyncio.sleep(2)
# ----------------------------------------
def get_dir_size(start_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

class FolderCreate(BaseModel):
    path: str
    folder_name: str

class UsernameChange(BaseModel):
    new_username: str

class UserEdit(BaseModel):
    role: str
    storage_quota_mb: int

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"
    storage_quota_mb: int = 5000

class MoveRequest(BaseModel):
    source_paths: List[str] # Lista de fișiere/foldere de mutat
    destination_folder: str

# 1. DEFINEȘTE CALEA GLOBALĂ
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_PATH = os.path.join(BASE_DIR, "simulated_storage")

# 2. CREEAZĂ FOLDERUL GLOBAL
if not os.path.exists(STORAGE_PATH):
    os.makedirs(STORAGE_PATH)

# --- FUNCȚIA MAGICĂ PENTRU IZOLAREA USERILOR ---
def get_user_path(username: str):
    # Construim calea: simulated_storage/admin sau simulated_storage/george
    user_folder = os.path.join(STORAGE_PATH, username)
    # Dacă folderul nu există (user nou), îl creăm pe loc
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    return user_folder
# -----------------------------------------------

app = FastAPI(title="NAS Pi Project API")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# 3. MOUNTEAZĂ FOLDERUL GLOBAL (dar URL-urile vor avea username-ul în ele)
app.mount("/media", StaticFiles(directory=STORAGE_PATH), name="media")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor_system())
# ----------------------------------------

# 4. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|100\.\d+\.\d+\.\d+):5173",  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/search")
def search_files(q: str, use_ai: bool = False, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    from app.models import FileIndex
    import datetime

    if not q or q.strip() == "":
        return []

    # Caută doar în pozele userului curent
    base_query = db.query(FileIndex).filter(FileIndex.owner_id == current_user.id)

    if use_ai:
        # Căutare inteligentă după tag-uri AI
        results = base_query.filter(FileIndex.ai_tags.ilike(f"%{q}%")).all()
    else:
        # Căutare normală în nume
        # (Adaptează FileIndex.filename dacă la tine e FileIndex.name)
        results = base_query.filter(
            or_(
                FileIndex.filename.ilike(f"%{q}%"),
                cast(FileIndex.size_kb, String).ilike(f"%{q}%")
            )
        ).all()

    formatted_results = []
    
    # Formatăm frumos pentru React
    for f in results:
        fname = getattr(f, 'filename', getattr(f, 'name', 'Unknown'))
        folder = getattr(f, 'folder_path', '') or "Root"
        
        formatted_results.append({
            "id": str(f.id),
            "name": fname,
            "path": folder,
            "size": f.size_kb,
            "date": "Sincronizat" # Datele vor fi statice din DB pentru super viteză
        })

    return formatted_results

@app.post("/create-folder")
async def create_folder(data: FolderCreate, current_user: models.User = Depends(auth.get_current_user)):
    user_root = get_user_path(current_user.username)
    # Construim calea sigură
    target_dir = os.path.normpath(os.path.join(user_root, data.path, data.folder_name))
    
    if not target_dir.startswith(user_root):
        raise HTTPException(status_code=400, detail="Cale invalidă")
        
    if os.path.exists(target_dir):
        raise HTTPException(status_code=400, detail="Folderul există deja")
        
    os.makedirs(target_dir)
    await manager.broadcast({"type": "REFRESH_FILES", "message": "Folder creat"})
    return {"message": "Folder creat cu succes!"}

@app.post("/move")
async def move_files(data: MoveRequest, current_user: models.User = Depends(auth.get_current_user)):
    user_root = get_user_path(current_user.username)
    
    # Construim calea folderului destinație
    dest_dir = os.path.normpath(os.path.join(user_root, data.destination_folder))
    
    # Siguranță: nu lăsăm userul să iasă din rădăcina lui
    if not dest_dir.startswith(user_root):
        raise HTTPException(status_code=400, detail="Destinație invalidă")

    errors = []
    for rel_path in data.source_paths:
        source_full_path = os.path.normpath(os.path.join(user_root, rel_path))
        
        if os.path.exists(source_full_path) and source_full_path.startswith(user_root):
            try:
                # Numele fișierului rămâne același
                filename = os.path.basename(source_full_path)
                final_dest = os.path.join(dest_dir, filename)
                
                if os.path.exists(final_dest):
                    errors.append(f"Fișierul {filename} există deja la destinație.")
                    continue
                    
                shutil.move(source_full_path, final_dest)
            except Exception as e:
                errors.append(f"Eroare la mutarea {rel_path}: {str(e)}")
    
    await manager.broadcast({"type": "REFRESH_FILES", "message": "Files moved"})
    return {"status": "ok", "errors": errors}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
def read_root():
    return {"message": "Server NAS activat!", "system": platform.system()}

def ai_worker_sync(file_id: int, image_path: str):
    print(f"[DEBUG] Thread started for: {os.path.basename(image_path)}")
    try:
        db_session = SessionLocal()
        try:
            process_image_with_ai(file_id, image_path, db_session)
        finally:
            db_session.close()
            print("[DEBUG] Thread finished")
    except Exception as e:
        print(f"[FATAL ERROR IN THREAD]: {e}")
        traceback.print_exc() # Asta ne va printa linia EXACTĂ unde crapă codul

async def ai_background_worker(file_id: int, image_path: str):
    """
    Această funcție e apelată de FastAPI, dar aruncă munca grea pe un fir separat (Thread)
    ca să nu blocheze serverul și să evite înghețarea silențioasă.
    """
    print("[DEBUG] Sending image to AI background worker...")
    await asyncio.to_thread(ai_worker_sync, file_id, image_path)

@app.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks, 
    files: List[UploadFile] = File(...), 
    target_path: str = Form(""), 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    user_root = get_user_path(current_user.username)
    target_dir = os.path.normpath(os.path.join(user_root, target_path))
    
    if not target_dir.startswith(user_root):
        target_dir = user_root

    current_size_bytes = get_dir_size(user_root)
    
    incoming_size_bytes = 0
    for f in files:
        f.file.seek(0, os.SEEK_END)
        incoming_size_bytes += f.file.tell()
        f.file.seek(0)
        
    if (current_size_bytes + incoming_size_bytes) > (current_user.storage_quota_mb * 1024 * 1024):
        raise HTTPException(status_code=400, detail="Cotă depășită!")

    for file in files:
        file_location = os.path.join(target_dir, file.filename)
        
        # 1. Salvăm fișierul fizic
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Îl înregistrăm în Baza de Date
        new_file_index = models.FileIndex(
            filename=file.filename,
            folder_path=target_path,
            size_kb=round(os.path.getsize(file_location) / 1024, 2),
            owner_id=current_user.id
        )
        db.add(new_file_index)
        db.commit()
        db.refresh(new_file_index)
        
        # 3. Trimitem poza la AI în fundal! (ASTA LIPSEA!)
        background_tasks.add_task(ai_background_worker, new_file_index.id, file_location)

    await manager.broadcast({"type": "REFRESH_FILES", "message": "New upload"})
    return {"status": "ok"}

@app.post("/sync-db")
def sync_database(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    from app.models import FileIndex
    import os

    user_root = get_user_path(current_user.username)
    
    # 1. Luăm toate fișierele pe care Baza de Date "crede" că le ai
    db_files = db.query(FileIndex).filter(FileIndex.owner_id == current_user.id).all()
    
    # Creăm un "catalog" temporar pentru a căuta instant în ele
    db_file_map = {}
    for f in db_files:
        # Folosim getattr în caz că tu ai numit coloana 'name' sau 'filename'
        fname = getattr(f, 'filename', getattr(f, 'name', ''))
        folder = getattr(f, 'folder_path', '') or ""
        
        # Cheia va fi calea relativă, ex: "vacanta\poza1.jpg" sau doar "poza1.jpg"
        rel_path = os.path.normpath(os.path.join(folder, fname))
        db_file_map[rel_path] = f

    # 2. Scanăm fizic Hard Disk-ul (Realitatea)
    disk_files_set = set()
    added_count = 0
    removed_count = 0

    for dirpath, dirnames, filenames in os.walk(user_root):
        for fname in filenames:
            file_path = os.path.join(dirpath, fname)
            
            # Calculăm folderul relativ (dacă e în root, va fi "")
            rel_dir = os.path.relpath(dirpath, user_root)
            if rel_dir == ".":
                rel_dir = ""
            
            rel_full_path = os.path.normpath(os.path.join(rel_dir, fname))
            disk_files_set.add(rel_full_path)

            # Dacă fișierul e pe DISC, dar NU e în Baza de Date -> Îl adăugăm!
            if rel_full_path not in db_file_map:
                size_kb = round(os.path.getsize(file_path) / 1024, 1)
                
                # Aici asigurate că folosești coloanele tale corecte din models.py
                new_idx = FileIndex(
                    filename=fname, # Schimbă cu 'name=fname' dacă așa e la tine în models
                    folder_path=rel_dir,
                    size_kb=size_kb,
                    owner_id=current_user.id,
                    ai_tags="" # Va fi procesat de AI mai târziu, sau va rămâne gol
                )
                db.add(new_idx)
                added_count += 1

    # 3. Ștergem "Fantomele" (sunt în Baza de Date, dar au fost șterse de pe disc)
    for rel_full_path, db_record in db_file_map.items():
        if rel_full_path not in disk_files_set:
            db.delete(db_record)
            removed_count += 1

    # Salvăm modificările
    db.commit()

    return {
        "message": "Sincronizare completă!", 
        "added": added_count, 
        "removed": removed_count
    }


@app.get("/download/{filename}")
async def download_file(filename: str, current_user: models.User = Depends(auth.get_current_user)):
    user_path = get_user_path(current_user.username)
    file_path = os.path.join(user_path, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Fișierul nu a fost găsit.")
        
    return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')


@app.delete("/delete/{file_path:path}")
async def delete_file(file_path: str, current_user: models.User = Depends(auth.get_current_user)):
    user_root = get_user_path(current_user.username)
    full_path = os.path.normpath(os.path.join(user_root, file_path))
    
    if not full_path.startswith(user_root) or not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Fișier negăsit")
        
    try:
        if os.path.isdir(full_path):
            shutil.rmtree(full_path) # Ștergem folderul cu tot cu ce are in el
        else:
            os.remove(full_path)
        await manager.broadcast({"type": "REFRESH_FILES", "message": "Deleted"})
        return {"message": "Șters cu succes"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/delete-multiple")
async def delete_multiple(filenames: list[str], current_user: models.User = Depends(auth.get_current_user)):
    user_path = get_user_path(current_user.username)
    deleted = []
    errors = []
    
    for filename in filenames:
        file_path = os.path.join(user_path, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                deleted.append(filename)
            except Exception as e:
                errors.append(f"Eroare la {filename}: {str(e)}")
                
    if deleted:
        await manager.broadcast({
            "type": "REFRESH_FILES", 
            "message": f"Files deleted: {', '.join(deleted)}"
        })
                
    return {"message": "Proces finalizat", "deleted": deleted, "errors": errors}

import datetime
@app.get("/dashboard")
async def get_dashboard_data(
    path: str = "", 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    import datetime
    media_exts = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.avi', '.mkv']

    # ==========================================
    # MAGIA 1: DACĂ SUNTEM ÎN ZONA DE SHARE
    # ==========================================
    if path.startswith("Shared with me"):
        categories = { "folders": [], "media": [], "documents": [] }
        parts = path.split("/") 
        
        # NIVELUL 1: Suntem în rădăcina "Shared with me" -> Desenăm foldere cu useri
        if len(parts) == 1:
            shared_records = db.query(models.SharedFile).filter(models.SharedFile.shared_with_id == current_user.id).all()
            unique_owners = set()
            for record in shared_records:
                if not record.expires_at or record.expires_at > datetime.datetime.utcnow():
                    unique_owners.add(record.owner_id)
            
            for owner_id in unique_owners:
                owner = db.query(models.User).filter(models.User.id == owner_id).first()
                if owner:
                    categories["folders"].append({
                        "name": owner.username, 
                        "path": f"Shared with me/{owner.username}",
                        "type": "folder",
                        "is_virtual": True 
                    })

        # NIVELUL 2: Ai intrat în folderul unui user (ex: "Shared with me/george")
        elif len(parts) == 2:
            target_username = parts[1]
            target_user = db.query(models.User).filter(models.User.username == target_username).first()
            
            if target_user:
                shared_records = db.query(models.SharedFile).filter(
                    models.SharedFile.shared_with_id == current_user.id,
                    models.SharedFile.owner_id == target_user.id
                ).all()
                
                for record in shared_records:
                    if record.expires_at and record.expires_at < datetime.datetime.utcnow():
                        continue 
                        
                    ext = os.path.splitext(record.filename)[1].lower()
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

        user_quota_mb = current_user.storage_quota_mb
        used_mb = get_dir_size(get_user_path(current_user.username)) / (1024 * 1024)
        free_mb = max(0, user_quota_mb - used_mb)
        percent_used = (used_mb / user_quota_mb) * 100 if user_quota_mb > 0 else 100

        return {
            "categories": categories,
            "storage_stats": {
                "total_gb": round(user_quota_mb / 1024, 2),
                "used_gb": round(used_mb / 1024, 2),
                "free_gb": round(free_mb / 1024, 2),
                "app_usage_mb": round(used_mb, 2),
                "percent_used": round(percent_used, 1),
                "user_role": current_user.role
            }
        }

    # ==========================================
    # LOGICA NORMALĂ PENTRU FOLDERELE TALE
    # ==========================================
    user_root = get_user_path(current_user.username)
    target_dir = os.path.normpath(os.path.join(user_root, path))
    
    if not target_dir.startswith(user_root) or not os.path.exists(target_dir):
        target_dir = user_root

    files_list = os.listdir(target_dir)
    categories = { "folders": [], "media": [], "documents": [] }
    
    if path == "" or path == ".":
        categories["folders"].append({
            "name": "Shared with me",
            "path": "Shared with me",
            "type": "folder",
            "is_virtual": True
        })

    for name in files_list:
        full_path = os.path.join(target_dir, name)
        rel_path = os.path.relpath(full_path, user_root).replace('\\', '/')
        
        if os.path.isdir(full_path):
            categories["folders"].append({"name": name, "path": rel_path, "type": "folder"})
        elif os.path.isfile(full_path):
            size = os.path.getsize(full_path)
            ext = os.path.splitext(name)[1].lower()
            file_info = {"name": name, "path": rel_path, "size": round(size / 1024, 2), "username": current_user.username} 
            if ext in media_exts:
                categories["media"].append(file_info)
            else:
                categories["documents"].append(file_info)

    user_quota_mb = current_user.storage_quota_mb
    used_mb = get_dir_size(user_root) / (1024 * 1024)
    free_mb = max(0, user_quota_mb - used_mb)
    percent_used = (used_mb / user_quota_mb) * 100 if user_quota_mb > 0 else 100

    return {
        "categories": categories,
        "storage_stats": {
            "total_gb": round(user_quota_mb / 1024, 2),
            "used_gb": round(used_mb / 1024, 2),
            "free_gb": round(free_mb / 1024, 2),
            "app_usage_mb": round(used_mb, 2),
            "percent_used": round(percent_used, 1),
            "user_role": current_user.role
        }
    }

@app.get("/file-details/{filename}")
async def get_file_details(filename: str, current_user: models.User = Depends(auth.get_current_user)):
    user_path = get_user_path(current_user.username)
    path = os.path.join(user_path, filename)
    
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Fișier negăsit")
    
    stats = os.stat(path)
    mod_date = datetime.fromtimestamp(stats.st_mtime).strftime('%d %B %Y, %H:%M')
    
    return {
        "name": filename,
        "modified": mod_date,
        "full_url": f"/media/{current_user.username}/{filename}"
    }

@app.post("/download-zip")
async def download_zip(filenames: list[str], current_user: models.User = Depends(auth.get_current_user)):
    # Importăm local tot ce avem nevoie ca să nu ne mai lovim de NameError
    import io
    import zipfile
    import os
    from fastapi.responses import StreamingResponse
    from fastapi import HTTPException

    try:
        user_path = get_user_path(current_user.username)
        
        # Creăm un fișier virtual direct în memoria RAM!
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for fname in filenames:
                # Curățăm numele pentru a fi compatibil și cu Windows și cu Linux
                clean_fname = fname.replace("\\", "/").strip("/")
                fpath = os.path.normpath(os.path.join(user_path, clean_fname))
                
                # Verificăm de două ori dacă fișierul chiar există pe disc
                if os.path.exists(fpath) and fpath.startswith(user_path) and os.path.isfile(fpath):
                    zip_file.write(fpath, arcname=clean_fname)
                else:
                    print(f"[Atenție] Fișier omis (nu a fost găsit): {fpath}")

        # Resetăm "cursorul" memoriei înapoi la începutul fișierului ZIP
        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer, 
            media_type="application/zip", 
            headers={
                "Content-Disposition": 'attachment; filename="Aether_Files.zip"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        print(f"[EROARE CRITICĂ LA ZIP]: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# --- RUTELE DE AUTENTIFICARE ȘI ADMIN RĂMÂN NESCHIMBATE ---

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilizator sau parolă incorectă",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/change-password")
async def change_password(
    data: PasswordChange, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    if not auth.verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Parola veche este incorectă")
    
    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not db_user:
        raise HTTPException(status_code=500, detail="Utilizatorul nu poate fi găsit")

    db_user.hashed_password = auth.get_password_hash(data.new_password)
    db.commit()
    return {"message": "Parola a fost schimbată cu succes!"}

@app.post("/change-username")
async def change_username(data: UsernameChange, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    existing = db.query(models.User).filter(models.User.username == data.new_username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Acest nume de utilizator este deja folosit.")
    
    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    db_user.username = data.new_username
    db.commit()
    
    # Generăm un token nou deoarece numele s-a schimbat
    new_token = auth.create_access_token(data={"sub": db_user.username})
    return {"message": "Numele a fost schimbat cu succes!", "new_token": new_token}

@app.put("/admin/users/{user_id}")
async def edit_user(user_id: int, data: UserEdit, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="DOAR ADMINUL ARE ACCES")
        
    user_to_edit = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_to_edit:
        raise HTTPException(status_code=404, detail="Utilizatorul nu există.")
        
    user_to_edit.role = data.role
    user_to_edit.storage_quota_mb = data.storage_quota_mb
    db.commit()
    return {"message": "Utilizator actualizat."}

@app.get("/admin/users")
async def get_users(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="DOAR ADMINUL ARE ACCES")
    users = db.query(models.User).all()
    return [{"id": u.id, "username": u.username, "role": u.role, "storage_quota_mb": u.storage_quota_mb} for u in users]

@app.post("/admin/users")
async def create_user(user_data: UserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="DOAR ADMINUL ARE ACCES")
    
    if db.query(models.User).filter(models.User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="UTILIZATORUL EXISTĂ DEJA")
    
    new_user = models.User(
        username=user_data.username,
        hashed_password=auth.get_password_hash(user_data.password),
        role=user_data.role,
        storage_quota_mb=user_data.storage_quota_mb
    )
    db.add(new_user)
    db.commit()
    return {"message": "Utilizator creat"}

@app.delete("/admin/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="DOAR ADMINUL ARE ACCES")
    
    user_to_delete = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="USERUL NU EXISTĂ")
    
    if user_to_delete.id == current_user.id:
        raise HTTPException(status_code=400, detail="NU TE POȚI ȘTERGE SINGUR")

    db.delete(user_to_delete)
    db.commit()
    return {"message": "Utilizator șters"}



# Definim cum arată "pachetul" de date pe care îl trimite React
class ShareRequest(BaseModel):
    file_paths: List[str]
    expiration: str = "24h" # Default 24 de ore

@app.post("/share-multiple")
async def share_multiple_files(request: ShareRequest, current_user: models.User = Depends(auth.get_current_user)):
    user_root = get_user_path(current_user.username)
    
    if not request.file_paths:
        raise HTTPException(status_code=400, detail="Nu ai selectat niciun fișier.")

    # Generăm UN SINGUR coș (bin) pentru toate fișierele
    bin_id = str(uuid.uuid4())
    
    uploaded_count = 0
    errors = []

    for rel_path in request.file_paths:
        full_path = os.path.normpath(os.path.join(user_root, rel_path))
        
        # Siguranță: să nu iasă din folderul lui
        if os.path.exists(full_path) and full_path.startswith(user_root) and os.path.isfile(full_path):
            filename = os.path.basename(full_path)
            url = f"https://filebin.net/{bin_id}/{filename}"
            
            try:
                with open(full_path, 'rb') as f:
                    headers = {'Expiration': request.expiration}
                    # Urcăm fișierul curent în coș
                    response = requests.put(url, data=f, headers=headers)
                    if response.status_code == 201:
                        uploaded_count += 1
                    else:
                        errors.append(f"Eroare la {filename}")
            except Exception as e:
                errors.append(f"Eroare locală la {filename}: {str(e)}")

    if uploaded_count == 0:
        raise HTTPException(status_code=500, detail="Niciun fișier nu a putut fi încărcat.")

    # Returnăm link-ul către tot coșul
    return {
        "link": f"https://filebin.net/{bin_id}",
        "uploaded": uploaded_count,
        "errors": errors
    }

class InternalShareRequest(BaseModel):
    file_paths: List[str]
    target_username: str
    expiration_hours: int = 24

# 2. RUTA CARE CREEAZĂ SHARE-UL
@app.post("/share-internal")
async def share_internal(data: InternalShareRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Verificăm dacă prietenul (userul țintă) există
    target_user = db.query(models.User).filter(models.User.username == data.target_username).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilizatorul nu a fost găsit în Aether.")
        
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Nu îți poți da share singur!")

    # Calculăm când expiră
    exp_date = datetime.datetime.utcnow() + datetime.timedelta(hours=data.expiration_hours)
    
    for filepath in data.file_paths:
        filename = os.path.basename(filepath)
        new_share = models.SharedFile(
            owner_id=current_user.id,
            shared_with_id=target_user.id,
            file_path=filepath,
            filename=filename,
            expires_at=exp_date
        )
        db.add(new_share)
        
    db.commit()
    # Trimitem un semnal ca prietenului să i se dea refresh la ecran instant!
    await manager.broadcast({"type": "REFRESH_FILES", "message": "Ai primit un fișier nou!"})
    
    return {"message": f"Fișiere partajate cu succes cu {data.target_username}!"}