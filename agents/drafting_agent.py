from pymongo import MongoClient
from google import genai
from google.genai import types
from rich.console import Console
from datetime import datetime
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
docs_col = db["documents"]
genai_client = genai.Client(api_key=GOOGLE_API_KEY)

LEGAL_NOTICE_PROMPT = """You are a senior Indian advocate drafting a formal legal notice.

Draft a complete, professional legal notice in English based on these case facts.
The notice must:
- Have proper heading: LEGAL NOTICE
- Include To: address block
- Include Date
- Include Subject line with relevant act sections
- Have numbered paragraphs stating facts clearly
- State the specific relief demanded
- Give a 15-day compliance deadline
- End with consequences of non-compliance
- Include a note to send via registered post

Case facts:
Summary: {summary}
Complainant: {complainant}
Opponent type: {opponent_type}
Amount involved: Rs. {amount}
Key facts: {key_facts}
Violations: {violations}
Relevant acts: {acts}

Respond with ONLY the legal notice text. No JSON, no explanation."""

RTI_PROMPT = """You are drafting an RTI application under the Right to Information Act 2005.

Draft a complete RTI application based on:
Subject: {summary}
Applicant state: {state}
Key facts: {key_facts}

The application must include:
- Proper header: APPLICATION UNDER SECTION 6(1) OF THE RTI ACT 2005
- To: The Public Information Officer block (leave department blank with [DEPARTMENT])
- Date
- Subject line
- Numbered information requests (specific, clear)
- Fee note: Rs. 10 enclosed
- Applicant signature block

Respond with ONLY the RTI application text. No JSON, no explanation."""

CONSUMER_COMPLAINT_PROMPT = """You are drafting a consumer complaint for the District Consumer Disputes Redressal Commission.

Draft a complete consumer complaint based on:
Summary: {summary}
Amount: Rs. {amount}
Key facts: {key_facts}
Violations: {violations}

The complaint must include:
- Proper heading with commission name
- Complainant and Opposite Party details
- Numbered facts of the case
- Legal grounds (Consumer Protection Act 2019 sections)
- Relief sought (refund + compensation + litigation costs)
- Verification declaration

Respond with ONLY the complaint text. No JSON, no explanation."""


def generate_document(case_doc: dict, doc_type: str) -> str:
    summary = case_doc.get("summary", "")
    key_facts = json.dumps(case_doc.get("key_facts", {}))
    violations = json.dumps(case_doc.get("law_analysis", {}).get("violations", []))
    amount = case_doc.get("amount_involved", 0)
    acts = ", ".join(case_doc.get("relevant_acts", []))

    if doc_type == "legal_notice":
        prompt = LEGAL_NOTICE_PROMPT.format(
            summary=summary,
            complainant=f"User {case_doc.get('user_id','')} ({case_doc.get('complainant_state','India')})",
            opponent_type=case_doc.get("opponent_type", "opponent"),
            amount=amount,
            key_facts=key_facts,
            violations=violations,
            acts=acts
        )
    elif doc_type == "rti_application":
        prompt = RTI_PROMPT.format(
            summary=summary,
            state=case_doc.get("complainant_state", "India"),
            key_facts=key_facts
        )
    elif doc_type == "consumer_complaint":
        prompt = CONSUMER_COMPLAINT_PROMPT.format(
            summary=summary,
            amount=amount,
            key_facts=key_facts,
            violations=violations
        )
    else:
        return f"Document type '{doc_type}' not yet implemented."

    response = genai_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3)
    )
    return response.text.strip()


def run_drafting(case_doc: dict) -> dict:
    console.print("\n[bold cyan]Agent 4 — Drafting[/bold cyan]")

    timeline = case_doc.get("action_timeline", [])
    docs_needed = [
        step["document_needed"]
        for step in timeline
        if step.get("document_needed") and step["document_needed"] != "none"
    ]

    if not docs_needed:
        docs_needed = ["legal_notice"]

    generated = []
    for doc_type in docs_needed[:2]:
        console.print(f"   Generating: {doc_type}...")
        content = generate_document(case_doc, doc_type)

        doc_record = {
            "doc_id": f"DOC-{case_doc['case_id']}-{doc_type}",
            "case_id": case_doc["case_id"],
            "doc_type": doc_type,
            "content": content,
            "generated_at": datetime.utcnow(),
            "status": "DRAFT",
            "sent": False
        }
        docs_col.insert_one(doc_record)
        generated.append(doc_record)
        console.print(f"[green]   ✅ {doc_type} generated ({len(content)} chars)[/green]")

    cases_col.update_one(
        {"case_id": case_doc["case_id"]},
        {"$set": {"generated_documents": [d["doc_id"] for d in generated]}}
    )

    case_doc["generated_docs"] = generated
    return case_doc
