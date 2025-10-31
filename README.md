# CARES MVP

This workspace contains an MVP for CARES using the requested stack:

- Backend: FastAPI (Python) in `server/`
- Frontend: React + Vite in `client/`
- No DB: `server/reports.json` stores reports
- OpenRouter model: `tngtech/deepseek-r1t2-chimera:free` (requires API key)

Quick start

1. Backend

 - Create `.env` in `server/` (copy from `.env.example`) and set `OPENROUTER_API_KEY`.
 - From the `server/` folder create a virtualenv and install requirements:

```powershell
cd server
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

 - Run server:

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

2. Frontend

```powershell
cd client
npm install
npm run dev
```

Open http://localhost:5173 (vite default) and use the app. The client expects the backend at `http://localhost:8000`.

Notes

- The OpenRouter API key must be provided. If missing, the server will return an error.
- The Download PDF button is a stub.
- This MVP saves raw request/response objects into `server/reports.json`.
