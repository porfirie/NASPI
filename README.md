# NAS Project

## Setup backend

1. Creează un mediu virtual Python:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Instalează dependențele:

   ```powershell
   pip install -r requirements.txt
   ```

3. Rulează serverul FastAPI din rădăcina proiectului:

   ```powershell
   uvicorn app.main:app --reload
   ```

4. Deschide frontendul:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

## Ce am schimbat

- `SECRET_KEY` și setările fundamentale au fost mutate în `.env`.
- `app/main.py` a fost restructurat în module separate pentru rute și servicii.
- Validarea căilor de fișiere (`download`, `delete`, `create-folder`, `move`) folosește acum un helper sigur.
- `share_multiple` folosește un client HTTP asincron (`httpx.AsyncClient`) în loc de `requests` blocant.
- Am introdus un endpoint batch de ștergere: `/delete-multiple`.
- Am actualizat frontend-ul să folosească endpointul de ștergere batch.

## Notă

Dacă rulezi serverul din directorul `app`, comanda trebuie să fie:

```powershell
cd app
uvicorn main:app --reload
```

Dacă rulezi din directorul principal al proiectului, folosește:

```powershell
uvicorn app.main:app --reload
```
