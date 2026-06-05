from pymongo import MongoClient
from google import genai
from google.genai import types
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import os, json
from dotenv import load_dotenv

load_dotenv()
console = Console()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "casepilot")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[MONGODB_DB]
cases_col = db["cases"]
genai_client = genai.Client(api_key=GOOGLE_API_KEY)

CITATION_PROMPT = """You are a senior Indian Supreme Court advocate.

Based on the case facts, law references, and evidence analysis, generate:

1. citations: list of 3-5 most relevant legal citations, each with:
   - act: full act name
   - section: section number
   - title: section title
   - relevance: why this section applies to this case (1 sentence)
   - strength: HIGH / MEDIUM / LOW

2. justice_score: object with:
   - overall: integer 0-100 (overall case strength)
   - legal_basis: integer 0-100 (how strong the legal foundation is)
   - evidence_strength: integer 0-100 (how strong the evidence is)
   - procedural_compliance: integer 0-100 (how well legal procedures have been followed)
   - verdict: one sentence overall assessment

3. winning_argument: the single strongest legal argument in 2-3 sentences

Respond ONLY with valid JSON. No markdown.

Case summary: {summary}
Dispute type: {dispute_type}
Amount: Rs. {amount}
Law references found: {law_refs}
Evidence analysis: {evidence_analysis}
Violations: {violations}"""


def run_citation(case_doc: dict) -> dict:
    console.print("\n[bold cyan]Agent — Citation & Justice Score[/bold cyan]")

    law_analysis = case_doc.get("law_analysis", {})
    evidence_analysis = case_doc.get("evidence_analysis", {})

    response = genai_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=CITATION_PROMPT.format(
            summary=case_doc.get("summary", ""),
            dispute_type=case_doc.get("dispute_type", ""),
            amount=case_doc.get("amount_involved", 0),
            law_refs=json.dumps(case_doc.get("law_references", [])[:6]),
            evidence_analysis=json.dumps(evidence_analysis),
            violations=json.dumps(law_analysis.get("violations", []))
        ),
        config=types.GenerateContentConfig(temperature=0.1)
    )

    raw = response.text.strip().replace("```json","").replace("```","").strip()
    result = json.loads(raw)

    citations = result.get("citations", [])
    justice_score = result.get("justice_score", {})

    console.print("\n[bold]Legal Citations:[/bold]")
    table = Table(show_header=True, header_style="bold", box=None, padding=(0,1))
    table.add_column("Act", style="yellow", max_width=30)
    table.add_column("Section", max_width=8)
    table.add_column("Strength", max_width=8)
    table.add_column("Relevance", max_width=50)
    for c in citations:
        color = "green" if c.get("strength") == "HIGH" else "yellow" if c.get("strength") == "MEDIUM" else "red"
        table.add_row(
            str(c.get("act",""))[:30],
            str(c.get("section","")),
            f"[{color}]{c.get('strength','')}[/{color}]",
            str(c.get("relevance",""))[:50]
        )
    console.print(table)

    score = justice_score.get("overall", 0)
    score_color = "green" if score >= 70 else "yellow" if score >= 40 else "red"
    console.print(Panel(
        f"[bold]Overall: [{score_color}]{score}/100[/{score_color}][/bold]\n"
        f"Legal basis: {justice_score.get('legal_basis',0)}/100  |  "
        f"Evidence: {justice_score.get('evidence_strength',0)}/100  |  "
        f"Procedure: {justice_score.get('procedural_compliance',0)}/100\n\n"
        f"[italic]{justice_score.get('verdict','')}[/italic]\n\n"
        f"[bold]Winning argument:[/bold] {result.get('winning_argument','')}",
        title="[bold]Justice Score[/bold]",
        border_style=score_color
    ))

    cases_col.update_one(
        {"case_id": case_doc["case_id"]},
        {"$set": {"citations": citations, "justice_score": justice_score}}
    )

    case_doc["citations"] = citations
    case_doc["justice_score"] = justice_score
    return case_doc
