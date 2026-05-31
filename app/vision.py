import os
import sys
import torch
from PIL import Image

# 1. SCUTUL ANTI-BLOCAJ PENTRU CPU
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
torch.set_num_threads(1)

# 2. SETĂRI DE CACHE (Modelul este deja salvat pe D: !)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_CACHE_DIR = os.path.join(BASE_DIR, "hf_cache")
os.environ["HF_HOME"] = LOCAL_CACHE_DIR

# 3. ÎNCĂRCAREA MODELULUI AI (Fără petice, funcționează nativ!)
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "vikhyatk/moondream2"

print("=" * 50, flush=True)
print("⏳ Încărcăm modelul AI în memorie...", flush=True)

try:
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, 
        trust_remote_code=True,
        revision="2024-03-06"
    ).to("cpu")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision="2024-03-06")
    model.eval() # Punem modelul în modul de "Gândire"
    print("✅ AI Vision este GATA!", flush=True)
except Exception as e:
    print(f"❌ EROARE CRITICĂ la încărcare: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
print("=" * 50, flush=True)

# 4. FUNCȚIA PRINCIPALĂ
def process_image_with_ai(file_id: int, image_path: str, db_session):
    print(f"\n🔍 [AI] START: {os.path.basename(image_path)}", flush=True)
    try:
        # Redimensionare pentru viteză
        image = Image.open(image_path).convert("RGB")
        image.thumbnail((600, 600)) 
        
        print("⚙️ [AI] Procesez pixelii...", flush=True)
        with torch.no_grad():
            enc_image = model.encode_image(image)
            prompt = "Return ONLY a comma-separated list of 5-10 keywords describing this image. NO sentences. NO verbs. Example: girl, wall, television, camera."
            answer = model.answer_question(enc_image, prompt, tokenizer)
        
        print(f"✅ [AI] REZULTAT: {answer}", flush=True)
        
        print("💾 [AI] Salvez în baza de date...", flush=True)
        from app.models import FileIndex 
        
        file_record = db_session.query(FileIndex).filter(FileIndex.id == file_id).first()
        if file_record:
            file_record.ai_tags = answer
            db_session.commit()
            print("🎉 [AI] Totul a fost salvat cu succes!", flush=True)
            
    except Exception as e:
        print(f"❌ [AI] Eroare la procesare: {e}", flush=True)

# 5. MODUL TĂU DE TESTARE RAPIDĂ DIN TERMINAL
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Utilizare: python vision.py C:\\cale\\imagine.jpg")
        sys.exit(1)

    test_image_path = sys.argv[1]
    if not os.path.exists(test_image_path):
        print(f"[TEST] Fișierul nu există: {test_image_path}")
        sys.exit(1)

    print(f"\n[TEST] Testez cu: {test_image_path}", flush=True)

    class MockRecord:
        ai_tags = None

    class MockSession:
        _record = MockRecord()
        def query(self, *a): return self
        def filter(self, *a): return self
        def first(self): return self._record
        def commit(self):
            print(f"[TEST] DB commit simulat — ai_tags = '{self._record.ai_tags}'", flush=True)
        def rollback(self):
            print("[TEST] DB rollback.", flush=True)

    process_image_with_ai(file_id=1, image_path=test_image_path, db_session=MockSession())