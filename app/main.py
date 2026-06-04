import asyncio
import platform
import psutil
import shutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.events import manager, ai_state

try:
    from app.config import CORS_ALLOW_ORIGIN_REGEX, STORAGE_PATH
except ImportError:
    from app.config import CORS_ALLOW_ORIGIN_REGEX, STORAGE_PATH

try:
    from app.events import manager
except ImportError:
    from app.events import manager


try:
    from app.routes.auth_routes import router as auth_router
    from app.routes.file_routes import router as file_router
    from app.routes.admin_routes import router as admin_router
    from app.routes.share_routes import router as share_router
    from app.routes.download_routes import router as download_router
    from app.routes.upload_routes import router as upload_router
    from app.routes.ai_routes import router as ai_router
except ImportError:
    from app.routes.auth_routes import router as auth_router
    from app.routes.file_routes import router as file_router
    from app.routes.admin_routes import router as admin_router
    from app.routes.share_routes import router as share_router
    from app.routes.download_routes import router as download_router
    from app.routes.upload_routes import router as upload_router
    from app.routes.ai_routes import router as ai_router


app = FastAPI(title="NAS Pi Project API")


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/media", StaticFiles(directory=str(STORAGE_PATH)), name="media")
app.router.include_router(auth_router)
app.router.include_router(file_router)
app.router.include_router(admin_router)
app.router.include_router(share_router)
app.router.include_router(download_router)
app.router.include_router(upload_router)
app.router.include_router(ai_router)
prev_net_sent = psutil.net_io_counters().bytes_sent
prev_net_recv = psutil.net_io_counters().bytes_recv


async def monitor_system():
    global prev_net_sent, prev_net_recv
    while True:
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram_info = psutil.virtual_memory()
            ram_total_gb = round(ram_info.total / (1024 ** 3), 2)
            ram_used_gb = round(ram_info.used / (1024 ** 3), 2)
            ram_percent = ram_info.percent
            disk = shutil.disk_usage("/")
            disk_total_gb = round(disk.total / (1024 ** 3), 2)
            disk_used_gb = round(disk.used / (1024 ** 3), 2)
            disk_percent = round((disk.used / disk.total) * 100, 1)

            curr_net = psutil.net_io_counters()
            up_speed = round((curr_net.bytes_sent - prev_net_sent) / (2 * 1024), 1)
            down_speed = round((curr_net.bytes_recv - prev_net_recv) / (2 * 1024), 1)
            prev_net_sent = curr_net.bytes_sent
            prev_net_recv = curr_net.bytes_recv

            temp = 0
            try:
                temps = psutil.sensors_temperatures()
                if 'cpu_thermal' in temps:
                    temp = temps['cpu_thermal'][0].current
                elif 'coretemp' in temps:
                    temp = temps['coretemp'][0].current
            except Exception:
                pass

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
                "active_connections": len(manager.active_connections),

                "ai_status": ai_state.status,
                "ai_queue": ai_state.queue_count,
                "logs": list(ai_state.logs)
            }
            await manager.broadcast(stats)
        except Exception as e:
            print(f"Eroare monitorizare: {e}")
        await asyncio.sleep(2)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor_system())


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
