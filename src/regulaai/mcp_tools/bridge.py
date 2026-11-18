import asyncio
import threading

from regulaai.mcp_tools.client import ToolSession, open_tools


class McpBridge:
    """Lets ordinary synchronous code call MCP tools.

    A background thread runs an asyncio loop that keeps one MCP session (and one server
    process) open until close() is called.
    """

    def __init__(self, env: dict[str, str] | None = None, startup_timeout: float = 120) -> None:
        self._env = env
        self._startup_timeout = startup_timeout
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._ready = threading.Event()
        self._stop: asyncio.Event | None = None
        self._tools: ToolSession | None = None
        self._error: BaseException | None = None

    def _run(self) -> None:
        self._loop.run_until_complete(self._main())

    async def _main(self) -> None:
        self._stop = asyncio.Event()
        try:
            # entered and exited in this one task, which the MCP client library requires
            async with open_tools(self._env) as tools:
                self._tools = tools
                self._ready.set()
                await self._stop.wait()
        except BaseException as exc:  # reported to the caller by start()
            self._error = exc
        finally:
            self._ready.set()

    def start(self) -> "McpBridge":
        self._thread.start()
        if not self._ready.wait(self._startup_timeout) or self._tools is None:
            self.close()
            raise RuntimeError(f"MCP tool server did not start: {self._error!r}")
        return self

    def call(self, name: str, timeout: float = 120, **arguments):
        if self._tools is None:
            raise RuntimeError("Bridge is not started")
        future = asyncio.run_coroutine_threadsafe(
            self._tools.call(name, timeout=timeout, **arguments), self._loop
        )
        return future.result(timeout=timeout + 5)

    def close(self) -> None:
        if self._stop is not None and self._thread.is_alive():
            self._loop.call_soon_threadsafe(self._stop.set)
        if self._thread.is_alive():
            self._thread.join(timeout=15)
        if not self._thread.is_alive() and not self._loop.is_closed():
            self._loop.close()

    def __enter__(self) -> "McpBridge":
        return self.start()

    def __exit__(self, *exc_info) -> None:
        self.close()