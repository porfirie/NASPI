from fastapi import WebSocket
from collections import deque
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


class AIStateManager:
    def __init__(self):
        self.status = "running"  # poate fi: 'running', 'paused', 'stopped'
        self.queue_count = 0
        self.logs = deque(maxlen=50) # Păstrează ultimele 50 de log-uri în memorie

    def log(self, message: str, level: str = "info"):
        t = datetime.now().strftime("%H:%M:%S")
        self.logs.append({"time": t, "message": message, "level": level})

# Instanța globală pe care o vom folosi în toată aplicația
ai_state = AIStateManager()
ai_state.log("Aether NAS inițializat cu succes.", "success")