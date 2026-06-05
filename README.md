# CasePilot — India's AI Legal Case Worker

> *Not a legal chatbot. A legal case worker that fights alongside you.*

[![Live Demo](https://img.shields.io/badge/Live%20Demo-casepilot.run.app-gold)](https://casepilot-34309631370.us-central1.run.app)
[![MongoDB Atlas](https://img.shields.io/badge/MongoDB-Atlas%20Vector%20Search-green)](https://mongodb.com)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Cloud%20Run-blue)](https://cloud.google.com)
[![Gemini](https://img.shields.io/badge/Gemini-3.1%20Flash%20Lite-orange)](https://deepmind.google/gemini)

Built for the **Google Cloud Rapid Agent Hackathon — MongoDB Track**

---

## The Problem

1.3 billion Indians. Less than 1 lawyer per 1,000 people outside major cities. Legal fees that cost more than the dispute is worth. Complex processes designed for people who already understand the system.

When a landlord steals a deposit, when an employer withholds wages, when a government office ignores an RTI — most Indians have no idea what to do next.

**CasePilot changes that.**

---

## What It Does

Describe your legal problem in plain language. CasePilot's 7 AI agents investigate your case, search 3,310 sections across 11 Indian laws, score your evidence, map your legal path, and generate a ready-to-send legal notice — in minutes, for free.

### The 7-Agent Pipeline

| Agent | Role |
|---|---|
| 🔍 Intake Agent | Classifies dispute type, identifies applicable jurisdiction |
| ⚖️ Law Research Agent | Semantic search across 3,310 law chunks via MongoDB Atlas Vector Search |
| 📋 Evidence Agent | Analyses uploaded documents, outputs Justice Score |
| 🗺️ Strategy Agent | Maps optimal legal path (notice → forum → court) |
| 📝 Drafting Agent | Generates ready-to-send legal notice pre-filled with case facts |
| ✅ Citation Agent | Attaches statute references with Atlas confidence scores |
| 💾 Memory Agent | Persists case record, tracks action timeline in MongoDB |

---

## Justice Score

Every investigation produces a Justice Score — a deterministic case strength metric:

```json
{
  "case_strength": 82,
  "evidence_completeness": 75,
  "missing_items": ["vacating proof", "formal written notice"],
  "verdict": "Strong case — 2 critical gaps. Address before filing."
}
```

---

## Knowledge Base

| Act | Chunks |
|---|---|
| Motor Vehicles Act | 690 |
| Indian Penal Code | 617 |
| Code of Criminal Procedure | 525 |
| Code of Civil Procedure | 252 |
| Transfer of Property Act 1882 | 250 |
| Consumer Protection Act 2019 | 214 |
| Information Technology Act 2000 | 211 |
| Negotiable Instruments Act | 190 |
| Indian Evidence Act | 184 |
| Right to Information Act 2005 | 113 |
| Industrial Disputes Act | 64 |
| **Total** | **3,310** |

---

## MongoDB Stack

| Layer | Collection | Purpose |
|---|---|---|
| Operational | `cases`, `documents`, `timelines` | Case management, generated docs |
| Vector Search | `law_corpus` | Semantic law retrieval (3,072 dims) |
| Vector Search | `evidence` | Per-user document embeddings |

Vector index: `law_vector_index` — cosine similarity, 3,072 dimensions (gemini-embedding-2)

---

## Tech Stack

- **Agents:** Google ADK (Agent Development Kit)
- **LLM:** Gemini 3.1 Flash-Lite
- **Embeddings:** gemini-embedding-2 (3,072 dimensions)
- **Database:** MongoDB Atlas (Operational + Vector Search)
- **Deployment:** Google Cloud Run
- **Frontend:** Vanilla HTML/CSS/JS (dark luxury theme)

---

## Setup

```bash
git clone https://github.com/ssurekumar01111-hue/casepilot.git
cd casepilot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Fill in MONGODB_URI and GOOGLE_API_KEY in .env
python main.py  # connection test
python scripts/ingest_corpus.py  # ingest law corpus
python app.py  # start API server
```
