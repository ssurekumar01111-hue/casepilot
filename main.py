from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from agents.intake_agent import run_intake
from agents.law_research_agent import run_law_research
from agents.evidence_agent import run_evidence
from agents.strategy_agent import run_strategy
from agents.citation_agent import run_citation
from agents.drafting_agent import run_drafting
from agents.memory_agent import run_memory, resume_session
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
console = Console()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "casepilot")
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[MONGODB_DB]
docs_col = db["generated_documents"]


def show_welcome():
    console.print(Panel.fit(
        "[bold green]CasePilot[/bold green] — India's AI Legal Case Worker\n"
        "[dim]Not a legal chatbot. A legal case worker that fights alongside you.[/dim]\n\n"
        "[dim]⚠ Disclaimer: CasePilot provides legal information only, not legal advice.[/dim]",
        border_style="green"
    ))


def show_case_summary(case: dict):
    console.print("\n[bold]━━━ CASE SUMMARY ━━━[/bold]")
    console.print(f"[cyan]Case ID:[/cyan]        {case['case_id']}")
    console.print(f"[cyan]Type:[/cyan]           {case['dispute_type'].replace('_',' ').title()}")
    console.print(f"[cyan]Summary:[/cyan]        {case.get('summary','')[:120]}")
    console.print(f"[cyan]Strategy:[/cyan]       {case.get('recommended_path','')[:120]}")

    js = case.get("justice_score", {})
    score = js.get("overall", 0)
    score_color = "green" if score >= 70 else "yellow" if score >= 40 else "red"
    console.print(f"[cyan]Justice Score:[/cyan]  [{score_color}]{score}/100[/{score_color}] — {js.get('verdict','')[:80]}")

    citations = case.get("citations", [])
    if citations:
        console.print(f"\n[bold]Key Citations:[/bold]")
        for c in citations[:3]:
            strength_color = "green" if c.get("strength") == "HIGH" else "yellow"
            console.print(
                f"  [{strength_color}]{c.get('strength','')}[/{strength_color}] "
                f"{c.get('act','')} S.{c.get('section','')} — {c.get('relevance','')[:70]}"
            )

    ev = case.get("evidence_analysis", {})
    if ev:
        console.print(f"\n[bold]Evidence Map:[/bold]")
        for item in ev.get("evidence_have", []):
            console.print(f"  [green]✅ HAVE:[/green]    {item}")
        for item in ev.get("evidence_missing", []):
            console.print(f"  [red]❌ MISSING:[/red] {item}")

    console.print(f"\n[bold]Action Timeline:[/bold]")
    for step in case.get("action_timeline", []):
        icon = "✅" if step["status"] == "DONE" else "⏳"
        console.print(
            f"  {icon} Step {step['step']}: {step['action']} "
            f"[dim](due in {step.get('deadline_days', 0)} days)[/dim]"
        )

    docs = case.get("generated_docs", [])
    if docs:
        console.print(f"\n[bold]Documents Generated:[/bold]")
        for doc in docs:
            console.print(f"  📄 {doc['doc_type'].replace('_',' ').title()} ({len(doc['content'])} chars)")
        console.print("\n[dim]Type 'show document' to view the full generated document.[/dim]")


def show_document(case: dict):
    docs = case.get("generated_docs", [])
    if not docs:
        console.print("[yellow]No documents generated yet.[/yellow]")
        return
    for doc in docs:
        console.print(Panel(
            doc["content"],
            title=f"[bold]{doc['doc_type'].replace('_',' ').title()}[/bold]",
            border_style="cyan"
        ))


def collect_evidence_files() -> list[str]:
    console.print("\n[bold]Evidence Documents[/bold]")
    console.print("[dim]Enter file paths to analyze (PDFs or text files). Press Enter to skip.[/dim]")
    files = []
    while True:
        path = Prompt.ask("[green]File path[/green] [dim](or Enter to continue)[/dim]", default="").strip()
        if not path:
            break
        import os
        if os.path.exists(path):
            files.append(path)
            console.print(f"[green]   Added: {path}[/green]")
        else:
            console.print(f"[red]   File not found: {path}[/red]")
    return files


def run_new_case(user_id: str):
    console.print("\n[bold]Describe your legal situation in detail:[/bold]")
    console.print("[dim](Include: what happened, amounts involved, how long ago, which state)[/dim]\n")
    situation = Prompt.ask("[green]Your situation[/green]")

    if not situation.strip():
        console.print("[red]No situation provided.[/red]")
        return

    file_paths = collect_evidence_files()

    console.print("\n[yellow]Running CasePilot — 7 agents working...[/yellow]\n")

    case = run_intake(user_id, situation)
    case = run_law_research(case)
    case = run_evidence(case, file_paths)
    case = run_strategy(case)
    case = run_citation(case)
    case = run_drafting(case)
    case = run_memory(case)

    show_case_summary(case)

    while True:
        console.print()
        action = Prompt.ask(
            "[green]What next?[/green] [dim](show document / new case / exit)[/dim]"
        ).strip().lower()

        if "show" in action or "document" in action:
            show_document(case)
        elif "new" in action:
            run_new_case(user_id)
            break
        elif "exit" in action or "quit" in action:
            break
        else:
            console.print("[dim]Options: 'show document', 'new case', 'exit'[/dim]")


def main():
    show_welcome()

    user_id = Prompt.ask(
        "\n[green]Enter your user ID[/green] [dim](or press Enter for demo)[/dim]",
        default="USR-DEMO"
    )

    active_cases = resume_session(user_id)

    if active_cases:
        console.print(f"\n[yellow]Welcome back! You have {len(active_cases)} active case(s).[/yellow]")
        action = Prompt.ask(
            "[green]What would you like to do?[/green] [dim](new case / exit)[/dim]",
            default="new case"
        ).strip().lower()
        if "new" in action:
            run_new_case(user_id)
    else:
        console.print("\n[dim]No active cases found. Starting a new case...[/dim]")
        run_new_case(user_id)


if __name__ == "__main__":
    main()
