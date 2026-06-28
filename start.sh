#!/usr/bin/env bash
#
# start.sh — pornește tot NAS-ul Aether cu o singură comandă.
#
#   1. verifică serverul AI (llama-vision) și îl pornește dacă e oprit
#   2. așteaptă ca serverul AI să răspundă
#   3. pornește backend-ul FastAPI (uvicorn)
#   4. pornește frontend-ul (Vite)
#   5. la Ctrl+C, oprește curat backend + frontend
#
# Folosire:  ./start.sh
#

set -euo pipefail

# --- Configurare -----------------------------------------------------------
# Rădăcina proiectului = folderul în care stă acest script (oriunde l-ai pune).
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT_DIR/venv"
FRONTEND_DIR="$PROJECT_DIR/frontend"

AI_SERVICE="llama-vision"
AI_HEALTH_URL="http://127.0.0.1:8080/health"

BACKEND_HOST="0.0.0.0"
BACKEND_PORT="8000"
# ---------------------------------------------------------------------------

green() { printf "\033[0;32m%s\033[0m\n" "$1"; }
yellow() { printf "\033[0;33m%s\033[0m\n" "$1"; }
red() { printf "\033[0;31m%s\033[0m\n" "$1"; }

echo "=================================================="
echo " Pornire Aether NAS"
echo "=================================================="

# --- 1. Serverul AI --------------------------------------------------------
if systemctl is-active --quiet "$AI_SERVICE"; then
    green " [OK] Serverul AI ($AI_SERVICE) rulează deja."
else
    yellow " [..] Serverul AI nu rulează. Îl pornesc (poate cere parola sudo)..."
    if sudo systemctl start "$AI_SERVICE"; then
        green " [OK] Serverul AI a fost pornit."
    else
        red " [EROARE] Nu am putut porni $AI_SERVICE. Verifică: sudo systemctl status $AI_SERVICE"
        exit 1
    fi
fi

# --- 2. Așteptăm ca serverul AI să răspundă --------------------------------
yellow " [..] Aștept ca serverul AI să fie gata..."
for i in $(seq 1 30); do
    if curl -s -o /dev/null "$AI_HEALTH_URL"; then
        green " [OK] Serverul AI răspunde."
        break
    fi
    if [ "$i" -eq 30 ]; then
        red " [EROARE] Serverul AI nu răspunde după 30s. Verifică: journalctl -u $AI_SERVICE -e"
        exit 1
    fi
    sleep 1
done

# --- Funcție de oprire curată ----------------------------------------------
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    yellow " Opresc procesele..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
    # Notă: serverul AI (systemd) rămâne pornit intenționat — e serviciu permanent.
    green " Gata. (Serverul AI rămâne activ ca serviciu.)"
    exit 0
}
trap cleanup INT TERM

# --- 3. Backend FastAPI ----------------------------------------------------
if [ ! -d "$VENV" ]; then
    red " [EROARE] Nu găsesc venv-ul la $VENV. Creează-l: python3 -m venv venv"
    exit 1
fi

green " [..] Pornesc backend-ul FastAPI pe $BACKEND_HOST:$BACKEND_PORT ..."
cd "$PROJECT_DIR"
"$VENV/bin/python" -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
BACKEND_PID=$!

# --- 4. Frontend Vite ------------------------------------------------------
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    yellow " [..] node_modules lipsește, rulez 'npm install'..."
    (cd "$FRONTEND_DIR" && npm install)
fi

green " [..] Pornesc frontend-ul (Vite)..."
(cd "$FRONTEND_DIR" && npm run dev -- --host) &
FRONTEND_PID=$!

echo "=================================================="
green " Totul rulează."
echo "   Backend:  http://localhost:$BACKEND_PORT"
echo "   Frontend: vezi URL-ul afișat de Vite mai sus (de obicei :5173)"
echo "   Oprește tot cu Ctrl+C."
echo "=================================================="

# --- 5. Așteptăm (ține scriptul viu până la Ctrl+C) ------------------------
wait
