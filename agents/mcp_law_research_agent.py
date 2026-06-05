"""
CasePilot — MCP-Powered Law Research Agent
Uses MongoDB MCP Server to query law_corpus via ADK McpToolset
"""

from google.adk.agents import Agent
from tools.mcp_tools import get_mongodb_mcp_toolset
import os

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")


def create_mcp_law_research_agent() -> Agent:
    """
    Law Research Agent powered by MongoDB MCP Server.
    Queries the law_corpus collection using natural language via MCP.
    """
    return Agent(
        model=GEMINI_MODEL,
        name="mcp_law_research_agent",
        instruction="""You are CasePilot's Law Research Agent with direct access to MongoDB Atlas 
        via the MongoDB MCP Server.

        Your job:
        1. Use the MongoDB MCP tools to query the 'law_corpus' collection in the 'casepilot' database
        2. Find relevant Indian law sections for the given dispute type
        3. Return structured citations with act name, section number, and relevance

        When querying, use the collection name 'law_corpus' in database 'casepilot'.
        Search for documents where the 'text' field contains relevant legal concepts.
        Always return at minimum 3 relevant law sections with their act, section_number, and text fields.
        
        Format your response as JSON with this structure:
        {
          "laws_found": [
            {
              "act": "act name",
              "section_number": "section number", 
              "section_title": "title",
              "text": "relevant excerpt",
              "relevance": "why this applies"
            }
          ]
        }""",
        tools=[get_mongodb_mcp_toolset()],
    )
