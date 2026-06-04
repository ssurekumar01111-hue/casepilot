from rich.console import Console
from rich.panel import Panel
from config import MONGODB_URI, GOOGLE_API_KEY

console = Console()

def main():
    console.print(Panel.fit(
        "[bold green]CasePilot[/bold green] — India's AI Legal Case Worker\n"
        "[dim]Not a legal chatbot. A legal case worker that fights alongside you.[/dim]",
        border_style="green"
    ))
    console.print("[yellow]Starting connection checks...[/yellow]")

    # MongoDB check
    try:
        from pymongo import MongoClient
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        version = client.server_info()["version"]
        console.print(f"[green]✅ MongoDB Atlas connected — version {version}[/green]")
    except Exception as e:
        console.print(f"[red]❌ MongoDB connection failed: {e}[/red]")

    # Gemini check
    try:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")
        r = model.generate_content("reply with ok only")
        console.print(f"[green]✅ Gemini connected — response: {r.text.strip()}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Gemini connection failed: {e}[/red]")

    # Embedding check
    try:
        import google.generativeai as genai
        result = genai.embed_content(model="models/text-embedding-004", content="test legal query")
        dims = len(result["embedding"])
        console.print(f"[green]✅ Embeddings working — {dims} dimensions[/green]")
    except Exception as e:
        console.print(f"[red]❌ Embedding check failed: {e}[/red]")

if __name__ == "__main__":
    main()
