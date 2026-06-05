from pymongo import MongoClient
from google import genai
from google.genai import types
from rich.console import Console
from rich.table import Table
import os
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
law_col = db["law_corpus"]
cases_col = db["cases"]
genai_client = genai.Client(api_key=GOOGLE_API_KEY)

VIOLATION_PROMPT = """You are a senior Indian legal expert.

Based on the user's situation and the retrieved law sections below, identify:
1. violations — list of specific legal violations (section, act, what was violated, severity: HIGH/MEDIUM/LOW)
2. remedies — list of available legal remedies with section references
3. summary — 2-sentence plain English explanation of the legal position

Respond ONLY with valid JSON. No markdown.

Situation: {situation}

Retrieved law sections:
{law_sections}"""


def embed_query(text: str) -> list[float]:
    response = genai_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
    )
    return response.embeddings[0].values


def vector_search_law(query: str, relevant_acts: list[str], top_k: int = 6) -> list[dict]:
    embedding = embed_query(query)
    pipeline = [
        {
            "$vectorSearch": {
                "index": "law_vector_index",
                "path": "embedding",
                "queryVector": embedding,
                "numCandidates": 100,
                "limit": top_k,
                "filter": {"act": {"$in": relevant_acts}} if relevant_acts else {}
            }
        },
        {
            "$project": {
                "act": 1, "section_number": 1, "section_title": 1,
                "text": 1, "score": {"$meta": "vectorSearchScore"}, "_id": 0
            }
        }
    ]
    return list(law_col.aggregate(pipeline))


def run_law_research(case_doc: dict) -> dict:
    import json
    console.print("\n[bold cyan]Agent 2 — Law Research[/bold cyan]")

    situation = case_doc["summary"]
    relevant_acts = case_doc.get("relevant_acts", [])

    results = vector_search_law(situation, relevant_acts)

    if not results:
        results = vector_search_law(situation, [], top_k=6)

    table = Table(show_header=True, header_style="bold", box=None, padding=(0,1))
    table.add_column("Act", style="yellow", max_width=35)
    table.add_column("Section", max_width=10)
    table.add_column("Title", max_width=35)
    table.add_column("Score", max_width=6)
    for r in results:
        table.add_row(
            str(r.get("act",""))[:35],
            str(r.get("section_number","")),
            str(r.get("section_title",""))[:35],
            f"{r.get('score',0):.3f}"
        )
    console.print(table)

    law_text = "\n\n".join([
        f"[{r['act']} S.{r['section_number']}] {r.get('section_title','')}: {r.get('text','')[:300]}"
        for r in results
    ])

    response = genai_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=VIOLATION_PROMPT.format(situation=situation, law_sections=law_text),
        config=types.GenerateContentConfig(temperature=0.1)
    )
    text = response.text.strip().replace("```json","").replace("```","").strip()
    analysis = json.loads(text)

    law_refs = [{"act": r["act"], "section": r["section_number"], "title": r.get("section_title",""), "score": r.get("score",0)} for r in results]
    cases_col.update_one(
        {"case_id": case_doc["case_id"]},
        {"$set": {"law_references": law_refs, "law_analysis": analysis}}
    )

    console.print(f"[green]✅ Found {len(analysis.get('violations',[]))} violations, {len(analysis.get('remedies',[]))} remedies[/green]")
    console.print(f"   Legal position: {analysis.get('summary','')[:120]}")

    case_doc["law_references"] = law_refs
    case_doc["law_analysis"] = analysis
    return case_doc
