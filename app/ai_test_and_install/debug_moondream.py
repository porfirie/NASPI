"""
Script de debug — rulează cu:
    python debug_moondream.py C:\cat.jpg
"""
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

import sys
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "local_moondream")

print(f"Model path: {MODEL_PATH}", flush=True)
print(f"Fișiere în model folder:", flush=True)
for f in os.listdir(MODEL_PATH):
    print(f"  {f}", flush=True)

print("\nVersiune moondream:", flush=True)
import moondream as md
print(f"  {md.__version__ if hasattr(md, '__version__') else 'necunoscută'}", flush=True)

print("\nÎncărcare model...", flush=True)
model = md.vl(model=MODEL_PATH)
print("Model încărcat.", flush=True)

image_path = sys.argv[1] if len(sys.argv) > 1 else None
if not image_path or not os.path.exists(image_path):
    print("Dă o imagine ca argument: python debug_moondream.py C:\\cat.jpg")
    sys.exit(1)

from PIL import Image
image = Image.open(image_path).convert("RGB")
image = image.resize((512, 512), Image.LANCZOS)
print(f"\nImaginea {image_path} deschisă cu succes.", flush=True)

print("\nTest encode_image...", flush=True)
try:
    encoded = model.encode_image(image)
    print(f"encode_image OK — tip rezultat: {type(encoded)}", flush=True)
except Exception as e:
    print(f"EROARE la encode_image: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

print("\nTest query...", flush=True)
try:
    result = model.query(encoded, "What is in this image?")
    print(f"query OK — rezultat: {result}", flush=True)
except Exception as e:
    print(f"EROARE la query: {e}", flush=True)
    traceback.print_exc()

print("\nTest caption...", flush=True)
try:
    result = model.caption(image)
    print(f"caption OK — rezultat: {result}", flush=True)
except Exception as e:
    print(f"EROARE la caption: {e}", flush=True)
    traceback.print_exc()