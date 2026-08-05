import asyncio
import sys
import subprocess
import os
import certifi

# Set SSL_CERT_FILE to use certifi's bundle
os.environ["SSL_CERT_FILE"] = certifi.where()

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Path to the executable (adjust if necessary)
SERVER_PATH = r"c:\users\wn6241\appdata\local\programs\python\python311\Scripts\notebooklm-mcp.exe"

async def run():
    print(f"Using SSL Cert File: {os.environ['SSL_CERT_FILE']}")
    
    server_params = StdioServerParameters(
        command=SERVER_PATH,
        args=[],
        env=os.environ.copy() # Pass the environment with SSL_CERT_FILE
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()

            # Try to list notebooks (assuming a tool named 'list_notebooks' exists)
            # We search for a relevant tool
            tools = await session.list_tools()
            list_tool = next((t for t in tools.tools if "list" in t.name.lower() and "notebook" in t.name.lower()), None)
            
            if list_tool:
                print(f"\n--- Calling {list_tool.name} ---")
                try:
                    result = await session.call_tool(list_tool.name, arguments={})
                    print(result.content)
                except Exception as e:
                    print(f"Error calling tool: {e}")
            else:
                 print("\nCould not find a tool to list notebooks.")

if __name__ == "__main__":
    asyncio.run(run())
