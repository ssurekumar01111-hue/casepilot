"""
CasePilot — Multi-Document Drafting Agent
Generates all required documents based on dispute type
"""

import os
from google import genai
from google.genai import types
from agents.document_templates import DISPUTE_DOCUMENTS, DOCUMENT_PROMPTS
from datetime import datetime

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def run_drafting_agent(case_facts: dict, law_research: dict, strategy: dict) -> list[dict]:
    """
    Generate all required documents for the dispute type.
    Returns list of generated documents.
    """
    genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    dispute_type = case_facts.get("dispute_type", "default")
    doc_types = DISPUTE_DOCUMENTS.get(dispute_type, DISPUTE_DOCUMENTS["default"])
    
    # Build context from case facts
    case_context = f"""
CASE FACTS:
- Dispute Type: {dispute_type}
- Summary: {case_facts.get('summary', '')}
- Key Facts: {case_facts.get('facts', {})}
- Evidence Available: {case_facts.get('evidence_summary', 'None uploaded')}

APPLICABLE LAWS:
{chr(10).join([f"- {law['act']} {law.get('section_number', '')}: {law.get('relevance', '')}" 
               for law in law_research.get('laws_found', [])])}

RECOMMENDED STRATEGY:
{strategy.get('recommended_path', '')}
"""
    
    generated_documents = []
    
    for doc_type in doc_types:
        prompt = DOCUMENT_PROMPTS.get(doc_type, DOCUMENT_PROMPTS["legal_notice"])
        
        full_prompt = f"""You are CasePilot's expert legal document drafter.

{case_context}

TASK: {prompt}

Generate the complete document now. Use [PLACEHOLDER] for information not available in the case facts.
Do not add any preamble or explanation — output only the document itself."""

        response = genai_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt
        )
        
        content = response.text.strip()
        
        generated_documents.append({
            "doc_type": doc_type,
            "doc_title": doc_type.replace("_", " ").title(),
            "content": content,
            "length": len(content),
            "generated_at": datetime.utcnow().isoformat()
        })
    
    return generated_documents
