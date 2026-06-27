import os
import warnings
warnings.filterwarnings("ignore", message=".*mkldnn_matmul.*")
from pathlib import Path

try:
    from app.config import HF_HOME, MODEL_ID
except ImportError:
    from app.config import HF_HOME, MODEL_ID

# IMPORTANT: env-ul TREBUIE setat înainte de importul transformers/torch
os.environ["HF_HOME"] = str(HF_HOME)
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

import asyncio
import time
import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoTokenizer

try:
    from app.models import FileIndex
    from app.events import ai_state
    from app.database import SessionLocal
except ImportError:
    from app.models import FileIndex
    from app.events import ai_state
    from app.database import SessionLocal

torch.set_num_threads(4)

print("=" * 50, flush=True)
print(" Încărcăm modelul AI în memorie...", flush=True)

try:
    # NOTĂ: moondream2 e un model QUANTIZAT (greutățile sunt dequantizate în
    # bfloat16 la rulare). NU forța .float() sau .half() — strică quantizarea
    # sau sparge RAM-ul. Bfloat16 e singura variantă coerentă pentru acest model.
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16
    ).to("cpu")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model.eval()
    print(f" [DEBUG] dtype real al modelului: {next(model.parameters()).dtype}", flush=True)
    print(" AI Vision este GATA!", flush=True)
except Exception as e:
    print(f" EROARE CRITICĂ la încărcare: {e}", flush=True)
    import traceback
    traceback.print_exc()
    raise


# ============================================================================
# COADĂ CU UN SINGUR WORKER
# Pozele nu mai pornesc câte un thread fiecare (cauza crash-ului la RAM).
# Intră într-o coadă și sunt procesate UNA CÂTE UNA de un singur worker permanent.
# ============================================================================

# Coada globală de joburi. Fiecare job = (file_id, image_path).
ai_queue: "asyncio.Queue" = asyncio.Queue()


def _process_one(file_id: int, image_path: str, db_session):
    """Procesarea efectivă a unei singure imagini (cod sincron, greu de CPU)."""
    print(f"\n [AI] START: {Path(image_path).name}", flush=True)
    try:
        image = Image.open(image_path).convert("RGB")
        image.thumbnail((378, 378))

        with torch.no_grad():
            t0 = time.time()
            enc_image = model.encode_image(image)
            t1 = time.time()

            prompt = "Describe this image in about 10 words, including objects, colors, and any notable features."
            # max_new_tokens limitează cât text generează -> mai puține tokenuri = mai rapid.
            # Pentru tag-uri de căutare, 40 e suficient.
            answer = model.answer_question(
                enc_image, prompt, tokenizer, max_new_tokens=40
            )
            t2 = time.time()
            print(f" [TIMP] encode_image: {t1-t0:.1f}s | answer: {t2-t1:.1f}s", flush=True)

        print(f" [AI] REZULTAT: {answer}", flush=True)

        file_record = db_session.query(FileIndex).filter(FileIndex.id == file_id).first()
        if file_record:
            file_record.ai_tags = answer
            db_session.commit()
            print(" [AI] Salvat cu succes!", flush=True)

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
            # Rulează inferența pe un thread (ca să nu blocheze event-loop-ul),
            # dar UNUL SINGUR pe rând, fiindcă worker-ul așteaptă aici până termină.
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