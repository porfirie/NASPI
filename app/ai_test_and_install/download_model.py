# download_model.py — rulează o singură dată
from huggingface_hub import snapshot_download
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
save_path = os.path.join(BASE_DIR, "local_moondream2")

print("Descarcă moondream2...")
snapshot_download(
    repo_id="vikhyatk/moondream2",
    local_dir=save_path,
    ignore_patterns=["*.bin"],  # folosim doar safetensors
)
print(f"Gata! Salvat în: {save_path}")