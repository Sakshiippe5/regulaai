import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class ToolSession:
    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def list_names(self) -> list[str]:
        return [t.name for t in (await self._session.list_tools()).tools]

    async def call(self, name: str, timeout: float = 120, **arguments):
        result = await asyncio.wait_for(
            self._session.call_tool(name, arguments=arguments), timeout=timeout
        )
        text = "".join(getattr(block, "text", "") for block in result.content)
        if result.isError:
            raise RuntimeError(text)
        return json.loads(text)


@asynccontextmanager
async def open_tools(env: dict[str, str] | None = None):
    """Starts the tool server as a subprocess and connects to it over stdio."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "regulaai.mcp_tools.server"],
        env={**os.environ, **(env or {})},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield ToolSession(session)