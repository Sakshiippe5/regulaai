import asyncio
from pathlib import Path

from regulaai.mcp_tools.client import open_tools


async def main():
    env = {
        "REGULAAI_OUTPUT_DIR": str(Path("outputs").resolve()),
        "REGULAAI_POLICY_DIR": str(Path("data/policies").resolve()),
    }
    async with open_tools(env) as tools:
        print("Tools offered by the server:", await tools.list_names())

        print("\nSearching policies...")
        for h in await tools.call("retrieve_internal_policies", timeout=60, query="how often is vulnerability assessment done", top_k=2):
            print(f"  {h['score']:.2f}  {h['source']} | {h['section']}")

        print("\nLast audit entries:")
        for row in await tools.call("retrieve_audit_history", limit=3):
            print(" ", row)


asyncio.run(main())