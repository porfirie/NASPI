import os
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoTokenizer

try:
    from app.models import FileIndex
    from app.config import HF_HOME, MODEL_ID
except ImportError:
    from app.models import FileIndex
    from app.config import HF_HOME, MODEL_ID

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
        image = Image.open(image_path).convert("RGB")
        image.thumbnail((378, 378))

        print(" [AI] Procesez pixelii...", flush=True)
        with torch.no_grad():
            enc_image = model.encode_image(image)
            prompt = "Describe this image in about 20 words, including objects, colors, and any notable features."
            answer = model.answer_question(enc_image, prompt, tokenizer)

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
