import os
from pathlib import Path

import asyncio

import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoTokenizer

try:
    from app.models import FileIndex
    from app.config import HF_HOME, MODEL_ID
    from app.events import ai_state
    from app.database import SessionLocal
except ImportError:
    from app.models import FileIndex
    from app.config import HF_HOME, MODEL_ID
    from app.events import ai_state
    from app.database import SessionLocal

os.environ["HF_HOME"] = str(HF_HOME)
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

torch.set_num_threads(4)

print("=" * 50, flush=True)
print(" Încărcăm modelul AI în memorie...", flush=True)

try:
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
        revision="2024-08-26",
        torch_dtype=torch.bfloat16  # <--- ACEST PARAMETRU SALVEAZĂ MEMORIA!
    ).to("cpu")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision="2024-08-26")
    model.eval()
    print(" AI Vision este GATA!", flush=True)
except Exception as e:
    print(f" EROARE CRITICĂ la încărcare: {e}", flush=True)
    import traceback
    traceback.print_exc()
    raise


def process_image_with_ai(file_id: int, image_path: str, db_session):
    print(f"\n [AI] START: {Path(image_path).name}", flush=True)
    try:
        # VERIFICARE 1: Dacă s-a dat STOP între timp, ieșim instant
        if ai_state.status == "stopped":
            print("[AI] Oprit forțat înainte de procesare.", flush=True)
            return

        image = Image.open(image_path).convert("RGB")
        image.thumbnail((378, 378))

        print(" [AI] Procesez pixelii...", flush=True)
        
        # VERIFICARE 2: Imediat înainte de codul greu de PyTorch
        if ai_state.status == "stopped":
            return

        with torch.no_grad():
            enc_image = model.encode_image(image)
            
            # Din nou, verificare de siguranță
            if ai_state.status == "stopped": return
            
            prompt = "Describe this image in about 10 words, including objects, colors, and any notable features."
            
            # Aici este operația masivă de 100% CPU:
            answer = model.answer_question(enc_image, prompt, tokenizer)

        # VERIFICARE 3: După ce a terminat matematica, verificăm dacă mai salvăm în DB
        if ai_state.status == "stopped":
            print("[AI] Procesat, dar aruncat la gunoi pentru că sistemul e STOPPED.", flush=True)
            return

        print(f" [AI] REZULTAT: {answer}", flush=True)

        file_record = db_session.query(FileIndex).filter(FileIndex.id == file_id).first()
        if file_record:
            file_record.ai_tags = answer
            db_session.commit()
            print(" [AI] Totul a fost salvat cu succes!", flush=True)
            
    except Exception as e:
        print(f"[AI] Eroare la procesare: {e}", flush=True)
        import traceback
        traceback.print_exc()
        

def ai_worker_sync(file_id: int, image_path: str):
    # Deschidem o conexiune sigură cu baza de date
    db_session = SessionLocal()
    try:
        process_image_with_ai(file_id, image_path, db_session)
    finally:
        # E CRUCIAL să o închidem, altfel Pi-ul rămâne fără memorie!
        db_session.close()




async def ai_background_worker(file_id: int, image_path: str):
    try:
        while ai_state.status == "paused":
            await asyncio.sleep(2)
            
        if ai_state.status == "stopped":
            return
            
        filename = os.path.basename(image_path)
        ai_state.log(f"AI ENGINE: A preluat '{filename}'. Procesare...", "warning")
        
        # Apelăm funcția de mai sus care gestionează baza de date corect
        await asyncio.to_thread(ai_worker_sync, file_id, image_path)
        
        ai_state.log(f"AI ENGINE: Analiză completă pentru '{filename}'.", "success")
    except Exception as e:
        ai_state.log(f"EROARE AI: {str(e)}", "error")
        print(f"Eroare severă la AI Worker: {e}")
    finally:
        ai_state.queue_count = max(0, ai_state.queue_count - 1)