# Legal Contract Intelligence System (Corrective RAG)

A local-first project that supports:
- Contract upload (PDF/TXT)
- Clause extraction and risk tagging
- Embedding + vector storage (Pinecone / Weaviate / local fallback)
- Metadata persistence in PostgreSQL/SQLite via SQLAlchemy
- Retrieval + Corrective RAG loop (retrieve → evaluate → refine → regenerate)
- Streamlit UI for practical usage

## Architecture

- **FastAPI backend** (`app/main.py`)
- **RAG pipeline service** (`app/services/rag_pipeline.py`)
- **Clause extractor** (`app/services/extractor.py`)
- **Vector backend adapter** (`app/services/vector_store.py`)
- **Streamlit UI** (`streamlit_app.py`)

## 1) Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

Update `.env` values (at minimum set backend and optionally OpenAI/API keys).

## 2) Run backend

```bash
uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs`

## 3) Run Streamlit UI

```bash
streamlit run streamlit_app.py
```

UI URL usually: `http://localhost:8501`

## 4) Test

```bash
pytest
```

## Important notes

- If `OPENAI_API_KEY` is missing, pipeline uses deterministic local fallback for embeddings/answers.
- For production legal workflows, set OpenAI key and real vector backend credentials.
- Default DB is SQLite for easy local setup; switch `DATABASE_URL` to PostgreSQL as needed.
