from pymongo import MongoClient
from google import genai
from google.genai import types
from rich.console import Console
from datetime import datetime
import os, json, fitz
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
console = Console()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "casepilot")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")

mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[MONGODB_DB]
cases_col = db["cases"]
evidence_col = db["evidence"]
genai_client = genai.Client(api_key=GOOGLE_API_KEY)

EVIDENCE_EXTRACT_PROMPT = """You are a legal evidence analyst specializing in Indian law.

Analyze this document text and extract:
1. doc_type: what kind of document is this (lease_agreement / payment_receipt / whatsapp_chat / invoice / bank_statement / notice / other)
2. parties: list of people/entities mentioned (names, roles)
3. dates: list of all dates found with context (e.g. "2024-03-01: deposit paid")
4. amounts: list of all monetary amounts with context
5. key_clauses: list of important clauses or statements (max 5)
6. summary: 2-sentence summary of what this document proves

Respond ONLY with valid JSON. No markdown.

Document text:
{text}"""

EVIDENCE_GAP_PROMPT = """You are a senior Indian legal analyst.

Given the case details and the evidence documents provided, identify:
1. evidence_have: list of what evidence the user has (with document reference)
2. evidence_missing: list of critical evidence still needed to strengthen the case
3. chronology: list of events in date order extracted from all documents
4. case_strength: integer 0-100 rating of how strong the evidence is
5. recommendation: 1-2 sentence advice on what to do next based on evidence gaps

Respond ONLY with valid JSON. No markdown.

Case summary: {summary}
Dispute type: {dispute_type}
Evidence documents analyzed:
{evidence_summary}"""


def extract_text_from_file(filepath: str) -> str:
    path = Path(filepath)
    if not path.exists():
        return ""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        doc = fitz.open(str(path))
        text = "\n".join([page.get_text() for page in doc])
        doc.close()
        return text.strip()
    elif suffix in [".txt", ".md"]:
        return path.read_text(encoding="utf-8").strip()
    else:
        return ""


def embed_text(text: str) -> list[float]:
    response = genai_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text[:2000],
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
    )
    return response.embeddings[0].values


def analyze_single_document(filepath: str, case_id: str) -> dict:
    text = extract_text_from_file(filepath)
    if not text:
        return {"error": f"Could not extract text from {filepath}"}

    response = genai_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=EVIDENCE_EXTRACT_PROMPT.format(text=text[:3000]),
        config=types.GenerateContentConfig(temperature=0.1)
    )
    raw = response.text.strip().replace("```json","").replace("```","").strip()
    extracted = json.loads(raw)

    embedding = embed_text(text)

    doc_record = {
        "evidence_id": f"EV-{case_id}-{Path(filepath).stem}",
        "case_id": case_id,
        "filename": Path(filepath).name,
        "doc_type": extracted.get("doc_type", "other"),
        "raw_text": text[:5000],
        "embedding": embedding,
        "parties": extracted.get("parties", []),
        "dates": extracted.get("dates", []),
        "amounts": extracted.get("amounts", []),
        "key_clauses": extracted.get("key_clauses", []),
        "summary": extracted.get("summary", ""),
        "uploaded_at": datetime.utcnow()
    }
    evidence_col.insert_one(doc_record)
    return doc_record


def run_evidence(case_doc: dict, file_paths: list[str]) -> dict:
    console.print("\n[bold cyan]Agent — Evidence Analysis[/bold cyan]")

    if not file_paths:
        console.print("[yellow]   No documents provided — skipping evidence analysis[/yellow]")
        case_doc["evidence_analysis"] = {"case_strength": 40, "evidence_missing": ["No documents uploaded yet"]}
        return case_doc

    analyzed_docs = []
    for fp in file_paths:
        console.print(f"   Analyzing: {Path(fp).name}...")
        doc = analyze_single_document(fp, case_doc["case_id"])
        if "error" not in doc:
            analyzed_docs.append(doc)
            console.print(f"[green]   ✅ {doc['doc_type']} — {doc['summary'][:80]}[/green]")
            console.print(f"      Parties: {doc['parties']}")
            console.print(f"      Dates: {doc['dates'][:3]}")
            console.print(f"      Amounts: {doc['amounts'][:3]}")

    if not analyzed_docs:
        return case_doc

    evidence_summary = "\n".join([
        f"Document {i+1} ({d['doc_type']}): {d['summary']} | Dates: {d['dates']} | Amounts: {d['amounts']} | Key clauses: {d['key_clauses']}"
        for i, d in enumerate(analyzed_docs)
    ])

    gap_response = genai_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=EVIDENCE_GAP_PROMPT.format(
            summary=case_doc.get("summary", ""),
            dispute_type=case_doc.get("dispute_type", ""),
            evidence_summary=evidence_summary
        ),
        config=types.GenerateContentConfig(temperature=0.1)
    )
    gap_raw = gap_response.text.strip().replace("```json","").replace("```","").strip()
    gap_analysis = json.loads(gap_raw)

    console.print(f"\n[bold]Evidence Map:[/bold]")
    for item in gap_analysis.get("evidence_have", []):
        console.print(f"  [green]✅ HAVE:[/green] {item}")
    for item in gap_analysis.get("evidence_missing", []):
        console.print(f"  [red]❌ MISSING:[/red] {item}")
    console.print(f"\n  Case strength: [bold]{gap_analysis.get('case_strength', 0)}/100[/bold]")
    console.print(f"  Recommendation: {gap_analysis.get('recommendation','')[:150]}")

    cases_col.update_one(
        {"case_id": case_doc["case_id"]},
        {"$set": {
            "evidence_ids": [d["evidence_id"] for d in analyzed_docs],
            "evidence_analysis": gap_analysis
        }}
    )

    case_doc["evidence_analysis"] = gap_analysis
    case_doc["analyzed_docs"] = analyzed_docs
    return case_doc
