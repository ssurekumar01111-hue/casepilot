from pymongo import MongoClient
from rich.console import Console
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
console = Console()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "casepilot")

mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[MONGODB_DB]
cases_col = db["cases"]
docs_col = db["generated_documents"]


def run_memory(case_doc: dict) -> dict:
    console.print("\n[bold cyan]Agent 5 — Memory[/bold cyan]")

    cases_col.update_one(
        {"case_id": case_doc["case_id"]},
        {"$set": {"updated_at": datetime.utcnow(), "status": "ACTIVE"}}
    )
    console.print(f"[green]✅ Case {case_doc['case_id']} saved to MongoDB[/green]")
    return case_doc


def resume_session(user_id: str) -> list[dict]:
    active_cases = list(cases_col.find({"user_id": user_id, "status": "ACTIVE"}))
    today = datetime.utcnow()
    alerts = []

    for case in active_cases:
        for step in case.get("action_timeline", []):
            if step.get("status") == "PENDING":
                deadline = step.get("deadline")
                if deadline:
                    days_left = (deadline - today).days
                    if days_left < 0:
                        alerts.append({"case_id": case["case_id"], "type": "OVERDUE", "step": step["step"], "action": step["action"]})
                    elif days_left <= 3:
                        alerts.append({"case_id": case["case_id"], "type": "UPCOMING", "step": step["step"], "action": step["action"], "days_left": days_left})

    console.print(f"\n[bold cyan]Agent 5 — Memory (Session Resume)[/bold cyan]")
    console.print(f"   Active cases for {user_id}: {len(active_cases)}")

    for alert in alerts:
        if alert["type"] == "OVERDUE":
            console.print(f"[red]   ⚠ OVERDUE: Case {alert['case_id']} — Step {alert['step']}: {alert['action']}[/red]")
        else:
            console.print(f"[yellow]   📅 UPCOMING: Case {alert['case_id']} — Step {alert['step']}: {alert['action']} (in {alert['days_left']} days)[/yellow]")

    return active_cases
