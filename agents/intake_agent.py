from google import genai
from google.genai import types
from pymongo import MongoClient
from datetime import datetime
from rich.console import Console
import os, json
from dotenv import load_dotenv
from schemas.case_schema import Case

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

DISPUTE_TYPES = {
    "landlord_tenant": ["deposit", "eviction", "rent", "repair", "lease", "landlord", "tenant"],
    "consumer_fraud": ["refund", "defective", "fake product", "ecommerce", "warranty", "seller", "amazon", "flipkart"],
    "workplace": ["salary", "harassment", "termination", "pf", "esi", "employer", "fired", "office"],
    "rti_filing": ["government", "information", "public authority", "rti", "ministry", "department"],
    "cyber_crime": ["online fraud", "hacking", "morphed", "fake account", "scam", "upi", "otp"],
    "fir_guidance": ["police", "fir", "theft", "assault", "cheating", "complaint", "crime"],
    "property_dispute": ["ownership", "encroachment", "registry", "mutation", "land", "plot"],
    "matrimonial": ["divorce", "maintenance", "custody", "alimony", "dowry", "marriage"],
}

ACT_MAP = {
    "landlord_tenant": ["Transfer of Property Act, 1882", "Consumer Protection Act, 2019", "CPC"],
    "consumer_fraud": ["Consumer Protection Act, 2019", "IPC", "CRPC"],
    "workplace": ["IDA", "IPC", "CRPC"],
    "rti_filing": ["Right to Information Act, 2005"],
    "cyber_crime": ["Information Technology Act, 2000", "IPC", "CRPC"],
    "fir_guidance": ["IPC", "CRPC", "IEA"],
    "property_dispute": ["Transfer of Property Act, 1882", "CPC", "IPC"],
    "matrimonial": ["HMA", "IPC", "CPC"],
}

CLASSIFY_PROMPT = """You are a legal intake specialist for Indian law.

Analyze the user's situation and extract:
1. dispute_type — one of: landlord_tenant, consumer_fraud, workplace, rti_filing, cyber_crime, fir_guidance, property_dispute, matrimonial
2. summary — one sentence summary of the situation
3. complainant_state — Indian state if mentioned (default: "Unknown")
4. opponent_type — landlord / employer / seller / government / individual / unknown
5. amount_involved — numeric amount in INR if mentioned, else 0
6. key_facts — dict of important facts extracted (e.g. deposit_amount, months_elapsed, product_name)

Respond ONLY with valid JSON. No explanation, no markdown.

User situation: {situation}"""


def classify_situation(situation: str) -> dict:
    response = genai_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=CLASSIFY_PROMPT.format(situation=situation),
        config=types.GenerateContentConfig(temperature=0.1)
    )
    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def generate_case_id() -> str:
    from datetime import datetime
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"CPA-{ts}"


def run_intake(user_id: str, situation: str) -> dict:
    console.print("\n[bold cyan]Agent 1 — Intake[/bold cyan]")
    console.print(f"Situation: {situation[:80]}...")

    classification = classify_situation(situation)
    dispute_type = classification.get("dispute_type", "fir_guidance")
    relevant_acts = ACT_MAP.get(dispute_type, ["IPC"])

    case_id = generate_case_id()
    case_doc = {
        "case_id": case_id,
        "user_id": user_id,
        "dispute_type": dispute_type,
        "status": "ACTIVE",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "summary": classification.get("summary", situation[:100]),
        "complainant_state": classification.get("complain complainant_state", "Unknown"),
        "opponent_type": classification.get("opponent_type", "unknown"),
        "amount_involved": classification.get("amount_involved", 0),
        "key_facts": classification.get("key_facts", {}),
        "relevant_acts": relevant_acts,
        "law_references": [],
        "evidence": [],
        "action_timeline": [],
        "generated_documents": [],
        "session_log": [{"role": "user", "content": situation, "ts": datetime.utcnow()}]
    }

    cases_col.insert_one(case_doc)
    console.print(f"[green]✅ Case opened: {case_id} | Type: {dispute_type}[/green]")
    console.print(f"   Relevant acts: {', '.join(relevant_acts)}")

    return case_doc
