"""
CasePilot — MCP-Powered Memory Agent
Uses MongoDB MCP Server to persist case records via ADK McpToolset
"""

from google.adk.agents import Agent
from tools.mcp_tools import get_mongodb_mcp_toolset
import os

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")


def create_mcp_memory_agent() -> Agent:
    """
    Memory Agent powered by MongoDB MCP Server.
    Persists case records and retrieves previous sessions.
    """
    return Agent(
        model=GEMINI_MODEL,
        name="mcp_memory_agent",
        instruction="""You are CasePilot's Memory Agent with direct access to MongoDB Atlas
        via the MongoDB MCP Server.

        Your job:
        1. Save complete case records to the 'cases' collection in the 'casepilot' database
        2. Retrieve previous case sessions by case_id
        3. Update case status and action timelines
        4. Flag upcoming deadlines

        When saving a case, insert a document into the 'cases' collection with these fields:
        - case_id (string)
        - dispute_type (string)
        - status (string: open/in_progress/closed)
        - facts (object)
        - justice_score (object)
        - recommended_path (string)
        - action_timeline (array)
        - created_at (ISO timestamp)
        - updated_at (ISO timestamp)

        Confirm every save operation with the inserted case_id.""",
        tools=[get_mongodb_mcp_toolset()],
    )
