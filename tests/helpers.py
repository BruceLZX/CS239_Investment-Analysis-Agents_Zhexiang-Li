"""Shared test helpers: recorded responses and an in-process MCP client."""
import asyncio
import json
from pathlib import Path

from mcp.client.client import Client

FIXTURES = Path(__file__).parent / 'fixtures'


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def call_tool(server, name: str, arguments: dict | None = None):
    async def run():
        async with Client(server) as client:
            return await client.call_tool(name, arguments or {})
    return asyncio.run(run())


def list_tools(server):
    async def run():
        async with Client(server) as client:
            return (await client.list_tools()).tools
    return asyncio.run(run())


def result_text(result) -> str:
    return ' '.join(item.text for item in result.content if item.type == 'text')
