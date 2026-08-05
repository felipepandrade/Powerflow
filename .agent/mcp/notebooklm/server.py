from mcp.server.fastmcp import FastMCP
from notebooklm import NotebookLM
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize MCP Server
mcp = FastMCP("NotebookLM")

def get_client():
    """Authenticates and returns a NotebookLM client."""
    session_token = os.getenv("GOOGLE_SESSION_TOKEN")
    token_p0 = os.getenv("GOOGLE_TOKEN_P0")
    
    if not session_token or not token_p0:
        raise ValueError("Missing GOOGLE_SESSION_TOKEN or GOOGLE_TOKEN_P0 in .env file.")
        
    # NOTE: notebooklm-py uses these specific cookie names for auth
    return NotebookLM(cookie=f"Secure-1PSID={session_token}; Secure-1PSIDTS={token_p0}")

@mcp.tool()
async def list_notebooks() -> str:
    """Lists all available notebooks in the connected Google NotebookLM account."""
    try:
        client = get_client()
        notebooks = client.list_notebooks()
        if not notebooks:
            return "No notebooks found."
        
        # Format the output clearly
        result = "Found the following notebooks:\n\n"
        for nb in notebooks:
            result += f"- **{nb.title}** (ID: `{nb.id}`)\n"
        return result
    except Exception as e:
        return f"Error listing notebooks: {str(e)}"

@mcp.tool()
async def query_notebook(notebook_id: str, query: str) -> str:
    """
    Sends a query to a specific notebook and returns the answer with citations.
    
    Args:
        notebook_id: The ID of the notebook to query (use list_notebooks to find IDs).
        query: The question or instruction to send to the notebook.
    """
    try:
        client = get_client()
        answer = client.query(notebook_id, query)
        
        return f"**Answer:**\n{answer.content}\n\n**Citations:**\n{answer.citations}"
    except Exception as e:
        return f"Error querying notebook: {str(e)}"

@mcp.tool()
async def get_notebook_summary(notebook_id: str) -> str:
    """Retrieves the summary or overview of a specific notebook."""
    # Note: notebooklm-py might not have a direct 'summary' method, 
    # so we simulate it by asking for a summary.
    return await query_notebook(notebook_id, "Please provide a comprehensive summary of this notebook.")

if __name__ == "__main__":
    mcp.run()
