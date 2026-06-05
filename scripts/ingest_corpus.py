"""
CasePilot — Law Corpus Ingestion Script (Turbo Edition)
Optimized batching, hyper-fast resume logic, and MongoDB bulk inserts.
"""

import os
import json
import time
import fitz  # PyMuPDF
from pathlib import Path
from pymongo import MongoClient
from google import genai
from google.genai import types
from rich.console import Console
from rich.progress import track
from dotenv import load_dotenv

load_dotenv()
console = Console()

# --- Config ---
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "casepilot")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")
CORPUS_DIR = Path("corpus/raw")
COLLECTION_NAME = "law_corpus"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
BATCH_SIZE = 50
EMBED_BATCH_DELAY = 1.0

# --- Clients ---
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]
collection = db[COLLECTION_NAME]
genai_client = genai.Client(api_key=GOOGLE_API_KEY)

def chunk_text(text: str, source_meta: dict) -> list[dict]:
    chunks = []
    start = 0
    chunk_index = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk_text_content = text[start:end]
        if chunk_text_content.strip():
            chunks.append({
                **source_meta,
                "chunk_index": chunk_index,
                "text": chunk_text_content.strip(),
            })
            chunk_index += 1
        start = end - CHUNK_OVERLAP
    return chunks

def embed_batch(texts: list[str]) -> list[list[float]]:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = genai_client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            return [emb.values for emb in response.embeddings]
        except Exception as e:
            if "429" in str(e):
                wait_time = (attempt + 1) * 5
                console.print(f"[yellow]Rate limit hit. Waiting {wait_time}s...[/yellow]")
                time.sleep(wait_time)
            else:
                console.print(f"[red]Batch embedding failed: {e}[/red]")
                break
    return []

def process_all_chunks(all_chunks: list[dict]) -> int:
    if not all_chunks:
        return 0
    
    total_inserted = 0
    console.print(f"  Embedding [bold]{len(all_chunks)}[/bold] chunks in batches of {BATCH_SIZE}...")
    
    for i in track(range(0, len(all_chunks), BATCH_SIZE), description="  Progress"):
        batch = all_chunks[i : i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        embeddings = embed_batch(texts)
        
        if not embeddings:
            continue

        for chunk, emb in zip(batch, embeddings):
            chunk["embedding"] = emb
        
        try:
            collection.insert_many(batch)
            total_inserted += len(batch)
        except Exception as e:
            console.print(f"[red]MongoDB Insert failed: {e}[/red]")
        
        time.sleep(EMBED_BATCH_DELAY)
    return total_inserted

def get_existing_sections(act_name: str) -> set:
    """Fetch all ingested section numbers for an act in one query."""
    cursor = collection.find({"act": act_name}, {"section_number": 1})
    return {doc["section_number"] for doc in cursor}

def ingest_json_law(filepath: Path) -> int:
    act_name = filepath.stem.upper()
    console.print(f"\n[cyan]JSON:[/cyan] {filepath.name}")

    existing_sections = get_existing_sections(act_name)
    if existing_sections:
        console.print(f"  Skipping {len(existing_sections)} already ingested sections.")

    with open(filepath, "r", encoding="utf-8") as f:
        sections = json.load(f)

    file_chunks = []
    for section in sections:
        section_num = str(section.get("Section", section.get("section", "")))
        if section_num in existing_sections:
            continue

        section_title = section.get("section_title", section.get("title", ""))
        section_desc = section.get("section_desc", section.get("description", section.get("desc", "")))
        if not section_desc or not str(section_desc).strip():
            continue

        full_text = f"{act_name} Section {section_num}: {section_title}\n{section_desc}"
        source_meta = {
            "act": act_name,
            "source_file": filepath.name,
            "section_number": section_num,
            "section_title": section_title,
            "chapter": str(section.get("chapter", "")),
            "chapter_title": section.get("chapter_title", ""),
            "source_type": "json",
        }
        file_chunks.extend(chunk_text(full_text, source_meta))

    return process_all_chunks(file_chunks)

def ingest_pdf_law(filepath: Path) -> int:
    act_name = filepath.stem.replace("_", " ").title()
    console.print(f"\n[cyan]PDF:[/cyan] {filepath.name}")

    existing_pages = get_existing_sections(act_name)
    if existing_pages:
        console.print(f"  Skipping {len(existing_pages)} already ingested pages.")

    doc = fitz.open(str(filepath))
    file_chunks = []

    for page_num in range(len(doc)):
        page_id = f"page_{page_num + 1}"
        if page_id in existing_pages:
            continue

        page_text = doc[page_num].get_text().strip()
        if not page_text or len(page_text) < 50:
            continue

        source_meta = {
            "act": act_name,
            "source_file": filepath.name,
            "section_number": page_id,
            "section_title": f"Page {page_num + 1}",
            "chapter": "",
            "chapter_title": "",
            "source_type": "pdf",
        }
        file_chunks.extend(chunk_text(page_text, source_meta))

    doc.close()
    return process_all_chunks(file_chunks)

def main():
    console.print("[bold green]CasePilot — Law Corpus Ingestion (Turbo Edition)[/bold green]")
    
    # Process JSON
    for json_file in CORPUS_DIR.glob("*.json"):
        ingest_json_law(json_file)

    # Process PDF
    for pdf_file in CORPUS_DIR.glob("*.pdf"):
        ingest_pdf_law(pdf_file)

    console.print(f"\n[bold green]✅ Ingestion complete![/bold green]")

if __name__ == "__main__":
    main()
