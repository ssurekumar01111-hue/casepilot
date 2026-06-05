"""
CasePilot — MongoDB MCP Server Integration
Connects ADK agents to MongoDB Atlas via official MongoDB MCP Server
"""

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")


def get_mongodb_mcp_toolset() -> McpToolset:
    """
    Returns an ADK McpToolset connected to MongoDB Atlas
    via the official MongoDB MCP Server (npx mongodb-mcp-server).
    
    This gives CasePilot agents native MCP access to:
    - Query law_corpus collection via natural language
    - Store and retrieve case records
    - Run aggregations on evidence collection
    - Manage case timelines
    """
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=[
                    "-y",
                    "mongodb-mcp-server",
                ],
                env={
                    "MDB_MCP_CONNECTION_STRING": MONGODB_URI,
                },
            ),
            timeout=30,
        ),
    )
