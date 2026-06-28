import os
import io
import base64
import asyncio
import time
from pathlib import Path

import requests
from PIL import Image

from app.models import FileIndex
from app.events import ai_state
from app.database import SessionLocal

# ============================================================================
# Configurare: nu mai încărcăm moondream în PyTorch (bfloat16 emulat = lent).
# Inferența o face acum llama-server (GGUF), care ține modelul cald în RAM
# și răspunde prin endpoint compatibil OpenAI. Vezi serviciul `llama-vision`.
# URL-ul poate fi suprascris din mediu dacă muți serverul pe alt port.
# ============================================================================
LLAMA_SERVER_URL = os.environ.get(
    "LLAMA_SERVER_URL", "http://127.0.0.1:8080/v1/chat/completions"
)

# Același prompt ca în versiunea veche, pentru rezultate comparabile.
AI_PROMPT = (
    "Describe this image in about 20 words, "
    "including objects, colors, and any notable features."
)

# Marjă generoasă: encode + generare durează câteva secunde pe Pi.
REQUEST_TIMEOUT = 180  # secunde

print("=" * 50, flush=True)
print(f" AI Vision: folosim llama-server pe {LLAMA_SERVER_URL}", flush=True)

# Verificare opțională la pornire: răspunde serverul?
try:
    _health_url = LLAMA_SERVER_URL.replace("/v1/chat/completions", "/health")
    if requests.get(_health_url, timeout=5).ok:
        print(" AI Vision este GATA!", flush=True)
    else:
        print(" ATENȚIE: llama-server a răspuns, dar nu cu status OK.", flush=True)
except Exception as e:
    print(f" ATENȚIE: nu pot contacta llama-server încă ({e}).", flush=True)
    print("          Pornește-l: sudo systemctl start llama-vision", flush=True)


# ============================================================================
# COADĂ CU UN SINGUR WORKER
# Pozele nu pornesc câte un thread fiecare (cauza crash-ului la RAM).
# Intră într-o coadă și sunt procesate UNA CÂTE UNA de un singur worker permanent.
# ============================================================================

# Coada globală de joburi. Fiecare job = (file_id, image_path).
ai_queue: "asyncio.Queue" = asyncio.Queue()


def _process_one(file_id: int, image_path: str, db_session):
    """Procesarea efectivă a unei singure imagini.

    Singura schimbare față de versiunea veche: în loc de model.encode_image +
    model.answer_question (PyTorch), redimensionăm poza și o trimitem la
    llama-server. Restul fluxului (DB, log-uri) e identic.
    """
    print(f"\n [AI] START: {Path(image_path).name}", flush=True)
    try:
        # Redimensionăm la 378px ca înainte: encode rapid + payload mic.
        image = Image.open(image_path).convert("RGB")
        image.thumbnail((378, 378))

        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=90)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64}"

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": AI_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "temperature": 0.1,
            # Tag-uri scurte pentru căutare -> puține tokenuri = mai rapid.
            "max_tokens": 80,
        }

        t0 = time.time()
        resp = requests.post(LLAMA_SERVER_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        answer = resp.json()["choices"][0]["message"]["content"].strip()
        t1 = time.time()
        print(f" [TIMP] llama-server: {t1 - t0:.1f}s", flush=True)

        print(f" [AI] REZULTAT: {answer}", flush=True)

        file_record = db_session.query(FileIndex).filter(FileIndex.id == file_id).first()
        if file_record:
            file_record.ai_tags = answer
            db_session.commit()
            print(" [AI] Salvat cu succes!", flush=True)

    except requests.exceptions.RequestException as e:
        # Server picat / timeout / rețea — tratat separat ca să fie clar în log.
        print(f"[AI] Eroare de comunicare cu llama-server: {e}", flush=True)
    except Exception as e:
        print(f"[AI] Eroare la procesare: {e}", flush=True)
        import traceback
        traceback.print_exc()


def _process_one_with_db(file_id: int, image_path: str):
    """Wrapper care deschide și închide corect sesiunea de DB."""
    db_session = SessionLocal()
    try:
        _process_one(file_id, image_path, db_session)
    finally:
        db_session.close()


async def ai_worker_loop():
    """
    Worker-ul PERMANENT. Rulează cât trăiește aplicația.
    - Procesează imaginile din coadă, UNA CÂTE UNA.
    - Dacă status == 'paused': adoarme și NU ia joburi noi (coada se păstrează intactă).
    - Dacă status == 'stopped': golește coada (buton de panică).
    - Dacă status == 'running': reia exact de unde a rămas.
    """
    print(" [AI] Worker-ul de coadă a pornit.", flush=True)
    while True:
        # 1. Dacă suntem pe pauză, dormim până se dă 'play'. Coada NU se atinge.
        if ai_state.status == "paused":
            await asyncio.sleep(1)
            continue

        # 2. Dacă suntem pe 'stopped', golim coada (anulare totală).
        if ai_state.status == "stopped":
            while not ai_queue.empty():
                try:
                    ai_queue.get_nowait()
                    ai_queue.task_done()
                except asyncio.QueueEmpty:
                    break
            ai_state.queue_count = 0
            await asyncio.sleep(1)
            continue

        # 3. status == 'running': luăm un job din coadă (așteptăm max 1s dacă e goală).
        try:
            file_id, image_path = await asyncio.wait_for(ai_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue  # coada goală -> reluăm bucla (ca să re-verificăm statusul)

        # Dublă verificare: dacă între timp s-a dat pauză/stop, repunem jobul în coadă
        # ca să nu-l pierdem, și revenim la începutul buclei.
        if ai_state.status != "running":
            await ai_queue.put((file_id, image_path))
            continue

        filename = os.path.basename(image_path)
        ai_state.log(f"AI ENGINE: Procesez '{filename}'...", "warning")

        try:
            # Rulează cererea pe un thread (ca să nu blocheze event-loop-ul),
            # dar UNA SINGURĂ pe rând, fiindcă worker-ul așteaptă aici până termină.
            await asyncio.to_thread(_process_one_with_db, file_id, image_path)
            ai_state.log(f"AI ENGINE: Gata '{filename}'.", "success")
        except Exception as e:
            ai_state.log(f"EROARE AI: {str(e)}", "error")
            print(f"Eroare severă la AI Worker: {e}", flush=True)
        finally:
            ai_queue.task_done()
            ai_state.queue_count = max(0, ai_state.queue_count - 1)


def enqueue_image(file_id: int, image_path: str):
    """
    Apelat din upload_routes la fiecare poză nouă.
    Pune jobul în coadă și crește contorul. NU pornește niciun thread.
    """
    ai_queue.put_nowait((file_id, image_path))
    ai_state.queue_count += 1