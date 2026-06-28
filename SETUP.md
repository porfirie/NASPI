# Aether NAS — Raspberry Pi 5 Edition

NAS personal pe Raspberry Pi 5 (8GB) cu FastAPI + React și indexare AI a imaginilor.
Modelul de viziune rulează local prin **llama.cpp / llama-server** (GGUF), complet offline.

---

## Arhitectură

Sistemul are **trei procese** care rulează în paralel:

| Proces | Rol | Cum pornește |
|---|---|---|
| `llama-vision` (systemd) | Server AI: ține modelul GGUF cald în RAM, răspunde prin API compatibil OpenAI pe `127.0.0.1:8080` | automat la boot |
| Backend FastAPI (`uvicorn`) | API-ul aplicației; trimite pozele la serverul AI prin HTTP local | manual / serviciu |
| Frontend Vite (React) | Interfața web | manual / build static |

Serverul AI ascultă **doar pe localhost** (fără autentificare), deci nu e expus pe rețea.

---

## 1. Server AI (llama.cpp)

### Dependențe de sistem
```bash
sudo apt update
sudo apt install -y build-essential cmake git wget libcurl4-openssl-dev jq
```
`libcurl4-openssl-dev` e necesar ca `llama-server -hf` să poată descărca modele.
`jq` e opțional (doar pentru teste cu curl).

### Compilare
```bash
cd ~
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
cmake -B build
cmake --build build -j4 --target llama-server llama-mtmd-cli
```

### Model
`SmolVLM2-500M` (GGUF, de la `ggml-org`) — VLM mic cu template multimodal corect,
descărcat automat la prima pornire cu `-hf`.

> Notă: moondream2 în GGUF a fost testat, dar are un defect de construcție
> (template `vicuna` fără slot pentru imagine → eroare `number of bitmaps does
> not match number of markers` la llama-server), deci s-a ales SmolVLM2.

### Serviciu systemd
Fișier: `/etc/systemd/system/llama-vision.service`
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
Activare:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now llama-vision
sudo systemctl status llama-vision
```

### Comenzi utile
```bash
sudo systemctl restart llama-vision    # repornește
journalctl -u llama-vision -f          # log-uri live
# test direct:
curl -s http://127.0.0.1:8080/health
```

---

## 2. Backend (FastAPI)

### Mediu virtual + dependențe
```bash
cd /home/nas/Licenta_NAS_llama
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Pachete cheie (vezi `requirements.txt`):
`fastapi`, `uvicorn`, `sqlalchemy`, `passlib`, `python-jose`, `Pillow`,
`requests`, `httpx`, `python-multipart`, `bcrypt==4.0.1`.

> **Important:** `bcrypt` trebuie fixat la `4.0.1`. Versiunile 4.1+/4.2+ rup
> `passlib` (eroarea `module 'bcrypt' has no attribute '__about__'` și 500 la login).

> PyTorch / transformers **NU mai sunt necesare** — inferența AI se face prin
> llama-server. Pot fi eliminate din mediu pentru a economisi spațiu.

### Creare utilizator
Din **rădăcina** proiectului (ca importul `app.` să funcționeze), cu venv activ:
```bash
python3 -m app.create_user
```
Parola trebuie să fie sub 72 de bytes (limită bcrypt).

### Pornire
Din rădăcină, cu venv activ:
```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
La pornire ar trebui să apară:
```
 AI Vision: folosim llama-server pe http://127.0.0.1:8080/v1/chat/completions
 AI Vision este GATA!
 [AI] Worker-ul de coadă a pornit.
```

---

## 3. Frontend (React + Vite)

```bash
cd frontend
npm install
```
Mod dezvoltare:
```bash
npm run dev -- --host
```
Mod producție (optimizat mobil, port 4173):
```bash
npm run build
npm run preview -- --host
```

---

## Fluxul de procesare AI

1. Userul urcă o poză → `upload_routes.py` cheamă `enqueue_image()`.
2. Poza intră în coada `ai_queue` (procesare una câte una, fără crash la RAM).
3. Worker-ul permanent `ai_worker_loop()` ia jobul, redimensionează poza la 378px,
   o trimite (base64) la llama-server și primește descrierea.
4. Descrierea se salvează în `FileIndex.ai_tags` și e căutabilă din interfață.

Controlul `running` / `paused` / `stopped` se face prin `ai_state`, păstrat în FastAPI.

---

## Optimizări & decizii de arhitectură

- **Motor AI prin llama.cpp:** moondream2 în PyTorch (bfloat16 emulat pe ARM) făcea
  ~5 min/poză (291s doar encoderul). Mutarea pe GGUF + llama-server a adus timpul la
  ~6s/poză și a eliminat problema de RAM (modelul nu mai stă în procesul FastAPI).
- **Server AI izolat (systemd):** modelul se încarcă o singură dată și stă cald;
  dacă inferența crapă, backend-ul rămâne în picioare; pornirea FastAPI e instantă.
- **Coadă cu un singur worker:** pozele se procesează secvențial, fără a porni
  câte un thread per imagine (cauza vechilor crash-uri de memorie).
- **Suport multi-port CORS:** regex pentru portul de dev (5173) și cel de producție (4173).
- **Reziliență mobilă (WebSockets):** auto-reconectare asincronă pe `onclose` (iOS/Android).
- **Securitate:** `SECRET_KEY` și setările sensibile mutate în `.env`; servirea
  fișierelor se face printr-un endpoint securizat cu verificare de proprietar/share,
  nu prin mount public `StaticFiles`.
- **Modularizare:** `app/main.py` împărțit în rute (`app/routes/`) și servicii (`app/services/`).
- **Validare căi:** download / delete / create-folder / move folosesc un helper
  anti path-traversal.
- **Ștergere batch:** endpoint `/delete-multiple`, folosit din frontend.
- **share_multiple** folosește client HTTP asincron (`httpx.AsyncClient`) în loc de
  `requests` blocant.

---

## Capcane întâlnite (troubleshooting)

| Simptom | Cauză reală | Rezolvare |
|---|---|---|
| `curl: Argument list too long` | base64 prea mare în linia de comandă | scrie payload în fișier, `curl -d @file.json` |
| `ModuleNotFoundError: No module named 'app'` | rulat din interiorul `app/` | rulează din rădăcină: `python3 -m app.create_user` |
| `No module named 'httpx'` la pornire | dependență lipsă din venv | `pip install httpx` |
| `error reading bcrypt version` + 500 la login | bcrypt prea nou pentru passlib | `pip install "bcrypt==4.0.1"`, repornește uvicorn |
| `CORS header missing` la login | de fapt un **500** mascat (bcrypt) | rezolvă 500-ul; CORS e doar simptomul |
| `number of bitmaps != markers` la llama-server | template GGUF fără slot de imagine (moondream) | folosește un model cu template multimodal corect (SmolVLM2) |
