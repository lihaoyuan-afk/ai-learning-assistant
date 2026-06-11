# API App

FastAPI backend for the AI Learning Assistant Agent.

## Run

```powershell
cd E:\codex\apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## Current scope

- Health check
- PDF upload endpoint
- Document ingest placeholder
- Document chat placeholder
- Summary generation placeholder
- Quiz generation placeholder

The service boundaries are intentionally explicit so each placeholder can be replaced by real RAG, Qdrant, LangGraph, and LLM implementations later.

