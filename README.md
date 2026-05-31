Markdown

# Aether NAS - Raspberry Pi Edition

## Setup backend

1. Creează și activează un mediu virtual Python (specific Linux/Pi):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate

    Instalează dependențele:
    Bash

    pip install -r requirements.txt

    Rulează serverul FastAPI din rădăcina proiectului (deschis către rețea pentru Tailscale/WiFi):
    Bash

    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

Setup frontend

    Deschide și rulează interfața (Frontend):
    Bash

    cd frontend
    npm install

        Pentru Modul Dezvoltare (Dev):
        Bash

        npm run dev -- --host

        Pentru Modul Producție (Optimizat pentru telefon - Port 4173):
        Bash

        npm run build
        npm run preview -- --host

Ce am schimbat (Optimizări & Arhitectură Pi)

    Optimizare Memorie AI: Încărcarea modelului Moondream în format torch.bfloat16 pentru a reduce consumul RAM de la 6.2GB la ~3.5GB.

    Optimizare Performanță CPU: Deblocarea celor 4 nuclee ale procesorului prin torch.set_num_threads(4) și reducerea rezoluției de input la 378x378 pentru o inferență rapidă (~30-45s).

    Suport Multi-Port CORS: Suport asigurat în backend prin Regex pentru portul de dezvoltare (5173) și portul optimizat de producție (4173).

    Reziliență Mobile (WebSockets): Algoritm de auto-reconectare asincron pe evenimentul onclose pentru telefoanele iOS/Android.

    SECRET_KEY și setările fundamentale au fost mutate în .env.

    app/main.py a fost restructurat în module separate pentru rute și servicii.

    Validarea căilor de fișiere (download, delete, create-folder, move) folosește acum un helper sigur.

    share_multiple folosește un client HTTP asincron (httpx.AsyncClient) în loc de requests blocant.

    Am introdus un endpoint batch de ștergere: /delete-multiple.

    Am actualizat frontend-ul să folosească endpointul de ștergere batch.