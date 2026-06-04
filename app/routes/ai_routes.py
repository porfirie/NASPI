from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.models import User
from app.schemas import AIControlRequest
from app.events import ai_state

router = APIRouter()

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