from pymongo import MongoClient
from google import genai
from google.genai import types
from rich.console import Console
from datetime import datetime, timedelta
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

STRATEGY_PROMPT = """You are a senior Indian legal strategist.

Based on the case details and legal analysis, generate a 5-step action timeline.

For each step provide:
- step: number (1-5)
- action: what to do (short, clear)
- document_needed: legal_notice / consumer_complaint / rti_application / police_complaint / affidavit / none
- deadline_days: days from today to complete this step (integer)
- instructions: 1-2 sentence practical instruction
- law_basis: specific act and section this step is based on

Also provide:
- recommended_path: one sentence describing the overall legal strategy
- success_probability: LOW / MEDIUM / HIGH based on evidence and violations

Respond ONLY with valid JSON. No markdown.

Case summary: {summary}
Dispute type: {dispute_type}
Amount involved: {amount}
Violations found: {violations}
Remedies available: {remedies}"""


def run_strategy(case_doc: dict) -> dict:
    console.print("\n[bold cyan]Agent 3 — Strategy[/bold cyan]")

    law_analysis = case_doc.get("law_analysis", {})
    violations = law_analysis.get("violations", [])
    remedies = law_analysis.get("remedies", [])

    response = genai_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=STRATEGY_PROMPT.format(
            summary=case_doc.get("summary", ""),
            dispute_type=case_doc.get("dispute_type", ""),
            amount=case_doc.get("amount_involved", 0),
            violations=json.dumps(violations),
            remedies=json.dumps(remedies)
        ),
        config=types.GenerateContentConfig(temperature=0.2)
    )

    text = response.text.strip().replace("```json","").replace("```","").strip()
    strategy = json.loads(text)

    today = datetime.utcnow()
    timeline = []
    for step in strategy.get("steps", []):
        deadline = today + timedelta(days=step.get("deadline_days", 0))
        timeline.append({
            "step": step["step"],
            "action": step["action"],
            "document_needed": step.get("document_needed", "none"),
            "deadline": deadline,
            "deadline_days": step.get("deadline_days", 0),
            "instructions": step.get("instructions", ""),
            "law_basis": step.get("law_basis", ""),
            "status": "PENDING"
        })

    cases_col.update_one(
        {"case_id": case_doc["case_id"]},
        {"$set": {
            "action_timeline": timeline,
            "recommended_path": strategy.get("recommended_path", ""),
            "success_probability": strategy.get("success_probability", "MEDIUM")
        }}
    )

    console.print(f"[green]✅ Strategy: {strategy.get('recommended_path','')[:100]}[/green]")
    console.print(f"   Success probability: {strategy.get('success_probability','MEDIUM')}")
    console.print(f"   Action timeline: {len(timeline)} steps")
    for t in timeline:
        console.print(f"   Step {t['step']}: {t['action']} — due in {t['deadline_days']} days")

    case_doc["action_timeline"] = timeline
    case_doc["recommended_path"] = strategy.get("recommended_path", "")
    case_doc["success_probability"] = strategy.get("success_probability", "MEDIUM")
    return case_doc
