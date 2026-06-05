import os
from flask import Flask, request, jsonify, send_from_directory
from agents.intake_agent import run_intake
from agents.law_research_agent import run_law_research
from agents.evidence_agent import run_evidence
from agents.strategy_agent import run_strategy
from agents.citation_agent import run_citation
from agents.drafting_agent import run_drafting
from agents.memory_agent import run_memory, resume_session

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return send_from_directory("webapp", "index.html")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "CasePilot", "version": "1.0"})

@app.route("/case/new", methods=["POST"])
def new_case():
    data = request.json
    user_id = data.get("user_id", "USR-DEMO")
    situation = data.get("situation", data.get("description", ""))
    if not situation:
        return jsonify({"error": "situation is required"}), 400
    try:
        case = run_intake(user_id, situation)
        case = run_law_research(case)
        case = run_evidence(case, [])
        case = run_strategy(case)
        case = run_citation(case)
        case = run_drafting(case)
        case = run_memory(case)
        return jsonify({
            "case_id": case["case_id"],
            "dispute_type": case["dispute_type"],
            "summary": case.get("summary",""),
            "recommended_path": case.get("recommended_path",""),
            "justice_score": case.get("justice_score",{}),
            "citations": case.get("citations",[]),
            "action_timeline": [
                {k: str(v) if hasattr(v,"isoformat") else v
                 for k,v in step.items() if k != "deadline"}
                for step in case.get("action_timeline",[])
            ],
            "documents_generated": [
                {"doc_type": d["doc_type"], "length": len(d["content"]), "content": d["content"]}
                for d in case.get("generated_docs",[])
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/case/resume", methods=["POST"])
def resume():
    data = request.json
    user_id = data.get("user_id", "USR-DEMO")
    cases = resume_session(user_id)
    return jsonify({"active_cases": len(cases), "user_id": user_id})

@app.route("/case/document/<case_id>", methods=["GET"])
def get_document(case_id):
    from pymongo import MongoClient
    import os
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("MONGODB_DB","casepilot")]
    doc = db["generated_documents"].find_one({"case_id": case_id}, {"_id": 0, "embedding": 0})
    if not doc:
        return jsonify({"error": "document not found"}), 404
    doc["generated_at"] = str(doc.get("generated_at",""))
    return jsonify(doc)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
