import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parent.parent


async def main():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "backend.mcp_server"],
        cwd=str(PROJECT_ROOT)
    )

    print("Connecting to Opportunity OS MCP server...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            await session.initialize()

            print("\nMCP connection established successfully.")

            tools_response = await session.list_tools()

            print("\nAvailable MCP tools:")

            for tool in tools_response.tools:
                print(f"- {tool.name}: {tool.description}")

            print("\nTesting internship research tool...")

            result = await session.call_tool(
                "research_internships",
                arguments={
                    "degree": "Computer Science",
                    "year": 3,
                    "skills": [
                        "Python",
                        "Machine Learning",
                        "SQL"
                    ],
                    "location": "India",
                    "work_mode": "Remote"
                }
            )

            print("\nMCP tool response:")

            for content in result.content:
                if hasattr(content, "text"):
                    print(content.text)

            if result.isError:
                print("\nThe MCP tool returned an error.")
            else:
                print("\nMCP tool call completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())