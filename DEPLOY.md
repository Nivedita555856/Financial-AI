# Deployment Guide — Financial Insights Copilot

## Architecture

```
GitHub repo
    ├── Backend (FastAPI)  ──► Render  (https://your-api.onrender.com)
    └── Frontend (React)   ──► Vercel  (https://your-app.vercel.app)
```

Both services connect to:
- **Neo4j Aura** — graph database (already configured)
- **Weaviate Cloud** — vector store (already configured)
- **Groq** — LLM inference (already configured)

---

## Step 1 — Push to GitHub

```bash
cd financial-insight-copilot

git init                         # (skip if already a git repo)
git add .
git commit -m "Add React frontend + deployment config"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

> **Important:** The `.gitignore` excludes `venv/`, `node_modules/`, and `.env` files.  
> Credentials in `graph_rag.py` are used as fallback defaults — you can override them via environment variables on Render.

---

## Step 2 — Deploy Backend on Render

### 2a. Create a new Web Service

1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect your GitHub repository
3. Fill in the settings:

| Setting | Value |
|---------|-------|
| **Name** | `financial-insight-copilot-api` |
| **Root Directory** | *(leave blank — project root)* |
| **Environment** | `Python 3` |
| **Build Command** | `pip install -r requirements_deploy.txt` |
| **Start Command** | `uvicorn api:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free |

### 2b. Environment Variables (optional — fall back to code defaults)

In the Render dashboard → **Environment** tab, add these if you want to override the defaults:

```
NEO4J_URI        = neo4j+s://b1babcdd.databases.neo4j.io
NEO4J_USER       = b1babcdd
NEO4J_PASSWORD   = <your password>
WEAVIATE_URL     = https://7nas0soyqaos5ww8wb35tq.c0.asia-southeast1.gcp.weaviate.cloud
WEAVIATE_API_KEY = <your key>
GROQ_API_KEY     = <your key>
```

> **Note:** Without setting these, Render will use the hardcoded defaults in `graph_rag.py` — your existing credentials will work out of the box.

### 2c. Deploy

Click **Create Web Service**. Render will:
- Install Python deps (~30 seconds — `requirements_deploy.txt` is very lean)
- Start `uvicorn api:app`
- Show a green "Live" badge

**Your backend URL will be:** `https://financial-insight-copilot-api.onrender.com`

> ⚠️ On the free tier, the service sleeps after 15 min of inactivity. The first request wakes it up (~30s). The React frontend shows a friendly "Backend offline" warning and has a **Retry** button.

---

## Step 3 — Deploy Frontend on Vercel

### 3a. Import project

1. Go to [vercel.com](https://vercel.com) → **New Project** → Import your GitHub repo
2. Set the configuration:

| Setting | Value |
|---------|-------|
| **Root Directory** | `frontend` |
| **Framework Preset** | Vite |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm install` |

### 3b. Environment Variable

In the Vercel project settings → **Environment Variables**:

```
VITE_API_URL = https://financial-insight-copilot-api.onrender.com
```

Replace `financial-insight-copilot-api` with your actual Render service name if different.

### 3c. Deploy

Click **Deploy**. Vercel builds in ~30 seconds.

**Your frontend URL will be:** `https://financial-insight-copilot.vercel.app`

---

## Step 4 — Verify Everything Works

### Check backend health
```
GET https://financial-insight-copilot-api.onrender.com/health
```
Should return: `{"status":"healthy","service":"Financial Insights Copilot"}`

### Check CORS
The backend uses `allow_origins=["*"]` so the Vercel frontend can call it freely.

### Test the API
```bash
curl -X POST https://financial-insight-copilot-api.onrender.com/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Apple revenue?", "ticker": "AAPL"}'
```

---

## Local Development

### Backend
```bash
cd financial-insight-copilot
pip install -r requirements_deploy.txt   # lean install
uvicorn api:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev      # starts on http://localhost:3000
                 # Vite proxy forwards /api/* → localhost:8000 automatically
```

Open [http://localhost:3000](http://localhost:3000) — no CORS issues, no env vars needed in dev.

---

## Project Structure Summary

```
financial-insight-copilot/
├── api.py                   # FastAPI backend (unchanged)
├── graph_rag.py             # GraphRAG core (env vars added, same logic)
├── streamlit_app.py         # Original Streamlit UI (untouched)
├── requirements.txt         # Full dev requirements (local use)
├── requirements_deploy.txt  # Lean Render requirements ← USE THIS for deploy
├── render.yaml              # Render auto-deploy config
├── Procfile                 # Start command fallback
├── .env.example             # Backend env var template
├── .gitignore
│
└── frontend/                # React app → deploy to Vercel
    ├── package.json
    ├── vite.config.js
    ├── vercel.json
    ├── .env.example         # VITE_API_URL template
    ├── index.html
    └── src/
        ├── main.jsx
        ├── index.css        # Full dark financial theme
        ├── App.jsx
        ├── api/
        │   └── client.js    # All API calls with timeout handling
        └── components/
            ├── Sidebar.jsx        # Company selector + nav
            ├── TopBar.jsx         # Breadcrumb + status + clock
            ├── ChatPanel.jsx      # AI chat with typing indicator
            ├── FinancialsPanel.jsx# Area + bar charts (Recharts)
            ├── NewsPanel.jsx      # Weaviate news cards
            └── ImpactPanel.jsx    # Impact analysis form + result
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Backend shows "offline" on Vercel | Wait 30s and click Retry — Render free tier is sleeping |
| `CORS error` in browser | Confirm `VITE_API_URL` in Vercel env vars has no trailing slash |
| Neo4j connection fails on Render | Check `NEO4J_URI` / `NEO4J_PASSWORD` env vars in Render dashboard |
| Build fails on Render | Make sure `requirements_deploy.txt` is used, not `requirements.txt` |
| Vercel build error | Confirm Root Directory is set to `frontend` in Vercel project settings |
| Empty financials chart | Neo4j graph may need data — run `db_connection.py` locally to populate |
| Empty news panel | Weaviate collection needs documents — run `db_connection.py` locally |
