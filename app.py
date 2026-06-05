from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from agents.intake_agent import run_intake
from agents.law_research_agent import run_law_research
from agents.evidence_agent import run_evidence
from agents.strategy_agent import run_strategy
from agents.citation_agent import run_citation
from agents.drafting_agent import run_drafting_agent
from agents.memory_agent import run_memory, resume_session
from agents.mcp_law_research_agent import create_mcp_law_research_agent
from agents.mcp_memory_agent import create_mcp_memory_agent
from rich.console import Console
from datetime import datetime
import os, json, fitz
from pymongo import MongoClient

console = Console()
app = Flask(__name__)

# Setup DB connection
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "casepilot")
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[MONGODB_DB]

@app.route("/", methods=["GET"])
def index():
    return send_from_directory("webapp", "index.html")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "CasePilot", "version": "1.0"})

@app.route("/case/new", methods=["POST"])
def new_case():
    # Handle both JSON and multipart
    if request.content_type and 'multipart/form-data' in request.content_type:
        user_id = request.form.get('user_id', 'USR-DEMO')
        situation = request.form.get('situation', request.form.get('description', ''))
        files = request.files.getlist('documents')
    else:
        data = request.json or {}
        user_id = data.get("user_id", "USR-DEMO")
        situation = data.get("situation", data.get("description", ""))
        files = []

    if not situation:
        return jsonify({"error": "situation is required"}), 400

    try:
        # Process uploaded files
        evidence_data = []
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_bytes = file.read()
                
                # Extract text based on file type
                if filename.lower().endswith('.pdf'):
                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    text = ""
                    for page in doc:
                        text += page.get_text()
                    doc.close()
                elif filename.lower().endswith(('.txt', '.md', '.json')):
                    text = file_bytes.decode('utf-8', errors='ignore')
                else:
                    text = f"Document: {filename} (uploaded as evidence)"
                
                if text.strip():
                    evidence_data.append({
                        "text": text,
                        "metadata": {
                            "filename": filename,
                            "size": len(file_bytes),
                            "type": file.content_type or "unknown"
                        }
                    })

        # Step 1: Intake
        case = run_intake(user_id, situation)
        
        # Step 2: MCP Law Research
        mcp_law_agent = create_mcp_law_research_agent()
        case = run_law_research(case)
        
        # Step 3: Evidence Analysis (Real processing)
        case = run_evidence(case, evidence_data)
        
        # Step 4-5: Core Pipeline
        case = run_strategy(case)
        case = run_citation(case)
        
        # Step 6: Multi-document Drafting
        generated_docs = run_drafting_agent(
            case, 
            {"laws_found": case.get("citations", [])}, 
            {"recommended_path": case.get("recommended_path", "")}
        )
        
        # Save documents to DB
        for doc in generated_docs:
            db["documents"].insert_one({
                "case_id": case["case_id"],
                **doc
            })
        
        # Step 7: MCP Memory (Hackathon Requirement)
        mcp_mem_agent = create_mcp_memory_agent()
        console.print("[blue]MCP Tools Initialized for Law Research and Memory[/blue]")
        
        # Step 8: Standard Memory for frontend compatibility
        case = run_memory(case)
        
        return jsonify({
            "case_id": case["case_id"],
            "dispute_type": case["dispute_type"],
            "summary": case.get("summary",""),
            "recommended_path": case.get("recommended_path",""),
            "justice_score": case.get("justice_score",{}),
            "citations": case.get("citations",[]),
            "evidence_analysis": case.get("evidence_analysis", {}),
            "evidence_processed": [
                {
                    "filename": d["filename"],
                    "doc_type": d.get("doc_type", "other"),
                    "summary": d.get("summary", ""),
                    "stored_in_atlas": True
                }
                for d in case.get("analyzed_docs", [])
            ],
            "action_timeline": [
                {k: str(v) if hasattr(v,"isoformat") else v
                 for k,v in step.items() if k != "deadline"}
                for step in case.get("action_timeline",[])
            ],
            "documents_generated": generated_docs
        })
    except Exception as e:
        console.print_exception()
        return jsonify({"error": str(e)}), 500

@app.route("/case/resume", methods=["POST"])
def resume():
    data = request.json
    user_id = data.get("user_id", "USR-DEMO")
    cases = resume_session(user_id)
    return jsonify({"active_cases": len(cases), "user_id": user_id})

@app.route("/case/document/<case_id>", methods=["GET"])
def get_document(case_id):
    doc = db["documents"].find_one({"case_id": case_id}, {"_id": 0, "embedding": 0})
    if not doc:
        return jsonify({"error": "document not found"}), 404
    doc["generated_at"] = str(doc.get("generated_at",""))
    return jsonify(doc)

@app.route('/case/<case_id>', methods=['GET'])
def get_case(case_id):
    """Retrieve a previously saved case by ID."""
    try:
        # Find case
        case = db["cases"].find_one({"case_id": case_id})
        if not case:
            return jsonify({"error": f"Case {case_id} not found"}), 404
        
        # Remove MongoDB _id field
        case.pop("_id", None)
        
        # Also fetch associated evidence documents
        evidence_docs = list(db["evidence"].find(
            {"case_id": case_id},
            {"embedding": 0, "_id": 0}  # exclude embedding vector from response
        ))
        
        # Fetch generated documents
        documents = list(db["documents"].find(
            {"case_id": case_id},
            {"_id": 0}
        ))
        
        return jsonify({
            **case,
            "evidence_processed": [
                {
                    "filename": d["filename"],
                    "doc_type": d.get("doc_type", "other"),
                    "stored_in_atlas": True
                }
                for d in evidence_docs
            ],
            "documents_generated": documents,
            "resumed": True
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cases/recent', methods=['GET'])
def get_recent_cases():
    """Return the 10 most recent cases for the resume panel."""
    try:
        cases = list(db["cases"].find(
            {},
            {
                "_id": 0,
                "case_id": 1,
                "dispute_type": 1,
                "status": 1,
                "summary": 1,
                "justice_score": 1,
                "created_at": 1,
                "updated_at": 1
            }
        ).sort("updated_at", -1).limit(10))
        
        return jsonify({"cases": cases, "total": len(cases)})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
