# Aether NAS - Raspberry Pi Edition

NAS personal pe Raspberry Pi 5 (8GB) cu FastAPI + React și indexare AI a imaginilor.
Modelul de viziune rulează local prin **llama.cpp / llama-server** (GGUF), complet offline.

## Arhitectură

Trei procese rulează în paralel:
- **Server AI** (`llama-vision`, systemd) — ține modelul GGUF cald în RAM și răspunde
  pe `127.0.0.1:8080` printr-un API compatibil OpenAI. Pornește automat la boot.
- **Backend FastAPI** — API-ul aplicației; trimite pozele la serverul AI prin HTTP local.
- **Frontend Vite (React)** — interfața web.

Serverul AI ascultă doar pe localhost (fără autentificare), deci nu e expus pe rețea.

## Setup server AI (llama.cpp)

1. Dependențe de sistem:
   ```bash
   sudo apt install -y build-essential cmake git wget libcurl4-openssl-dev jq
   ```
2. Compilează llama.cpp:
   ```bash
   cd ~ && git clone https://github.com/ggerganov/llama.cpp.git
   cd llama.cpp && cmake -B build
   cmake --build build -j4 --target llama-server llama-mtmd-cli
   ```
3. Creează serviciul `/etc/systemd/system/llama-vision.service`:
   ```ini
   [Unit]
   Description=llama.cpp server (vision) pentru NAS
   After=network.target

   [Service]
   Type=simple
   User=nas
   WorkingDirectory=/home/nas/llama.cpp
   ExecStart=/home/nas/llama.cpp/build/bin/llama-server -hf ggml-org/SmolVLM2-500M-Video-Instruct-GGUF -c 4096 -t 4 --host 127.0.0.1 --port 8080
   Restart=on-failure
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
4. Activează-l:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now llama-vision
   sudo systemctl status llama-vision
   ```

Modelul (`SmolVLM2-500M`, GGUF de la ggml-org) se descarcă automat la prima pornire.
Comenzi utile: `journalctl -u llama-vision -f` (loguri), `sudo systemctl restart llama-vision`.

## Setup backend

1. Creează și activează un mediu virtual Python (specific Linux/Pi):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Instalează dependențele:
   ```bash
   pip install -r requirements.txt
   ```
   > `bcrypt` trebuie fixat la `4.0.1` (versiunile mai noi rup passlib → 500 la login).
   > PyTorch/transformers NU mai sunt necesare; inferența se face prin llama-server.
3. Creează un utilizator (din rădăcină, cu venv activ; parola < 72 bytes):
   ```bash
   python3 -m app.create_user
   ```
4. Rulează serverul FastAPI din rădăcina proiectului (deschis către rețea pentru Tailscale/WiFi):
   ```bash
   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## Setup frontend

```bash
cd frontend
npm install
```
- Modul Dezvoltare (Dev):
  ```bash
  npm run dev -- --host
  ```
- Modul Producție (Optimizat pentru telefon - Port 4173):
  ```bash
  npm run build
  npm run preview -- --host
  ```

## Ce am schimbat (Optimizări & Arhitectură Pi)

- **Motor AI prin llama.cpp:** Moondream2 în PyTorch (bfloat16 emulat pe ARM) făcea
  ~5 min/poză, din care 291s doar encoderul de viziune. Mutarea pe GGUF + llama-server
  a adus timpul la ~6s/poză și a eliminat problema de RAM (modelul nu mai e încărcat
  în procesul FastAPI, ci într-un server izolat).
- **Server AI izolat (systemd):** modelul se încarcă o singură dată și stă cald;
  pornirea backend-ului devine instantă, iar dacă inferența crapă, restul aplicației
  rămâne funcțional.
- **Coadă cu un singur worker:** pozele se procesează una câte una printr-o coadă
  (`ai_queue` + `ai_worker_loop`), cu control running/paused/stopped, în loc să
  pornească câte un thread per imagine (cauza vechilor crash-uri de memorie).
  Input redus la 378x378 pentru transfer și encode rapid.
- **Suport Multi-Port CORS:** Suport asigurat în backend prin Regex pentru portul de
  dezvoltare (5173) și portul optimizat de producție (4173).
- **Reziliență Mobile (WebSockets):** Algoritm de auto-reconectare asincron pe
  evenimentul onclose pentru telefoanele iOS/Android.
- **SECRET_KEY** și setările fundamentale au fost mutate în `.env`.
- `app/main.py` a fost restructurat în module separate pentru rute și servicii.
- Validarea căilor de fișiere (download, delete, create-folder, move) folosește acum
  un helper sigur (anti path-traversal), iar servirea fișierelor se face printr-un
  endpoint securizat cu verificare de proprietar/share (nu mount public StaticFiles).
- `share_multiple` folosește un client HTTP asincron (`httpx.AsyncClient`) în loc de
  `requests` blocant.
- Am introdus un endpoint batch de ștergere: `/delete-multiple`.
- Am actualizat frontend-ul să folosească endpointul de ștergere batch.