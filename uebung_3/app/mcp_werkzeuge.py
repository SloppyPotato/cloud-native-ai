"""Werkzeuge von einem MCP-Server holen und als Werkzeug-Objekte anbieten.

Unser Agent ist hier der MCP-Client. Er fragt den Server, welche Werkzeuge
es gibt (tools/list), und ruft sie bei Bedarf auf (tools/call). Der Agent
muss die Werkzeuge nicht kennen, bevor er startet: Was der Server anbietet,
steht ihm zur Verfügung.

Das MCP-SDK arbeitet asynchron. Damit die Agent-Schleife einfach bleibt,
öffnet jeder Aufruf hier eine kurze eigene Verbindung (asyncio.run). Für
eine Übung reicht das, in Produktion hält man eine Sitzung offen.
"""

import asyncio
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from werkzeuge import Werkzeug

MCP_URL = os.environ.get("MCP_URL", "http://campus-mcp:8000/mcp")

# Werkzeuge, deren Name so beginnt, verändern etwas und brauchen eine Bestätigung
SCHREIBEND_PRAEFIXE = ("raum_buchen", "buche", "loesche", "sende")


async def _liste(url: str):
    async with streamablehttp_client(url) as (lesen, schreiben, _):
        async with ClientSession(lesen, schreiben) as sitzung:
            await sitzung.initialize()
            return (await sitzung.list_tools()).tools


async def _aufruf(url: str, name: str, argumente: dict) -> str:
    async with streamablehttp_client(url) as (lesen, schreiben, _):
        async with ClientSession(lesen, schreiben) as sitzung:
            await sitzung.initialize()
            ergebnis = await sitzung.call_tool(name, argumente)
            text = "\n".join(t.text for t in ergebnis.content if hasattr(t, "text"))
            return f"Fehler: {text}" if ergebnis.isError and not text.startswith("Fehler") else text


def mcp_werkzeuge(url: str = MCP_URL) -> list[Werkzeug]:
    """Fragt den MCP-Server nach seinen Werkzeugen."""
    werkzeuge = []
    for tool in asyncio.run(_liste(url)):
        def ausfuehren(_name=tool.name, **argumente) -> str:
            return asyncio.run(_aufruf(url, _name, argumente))

        werkzeuge.append(Werkzeug(
            name=tool.name,
            beschreibung=tool.description or "",
            parameter=tool.inputSchema,
            funktion=ausfuehren,
            schreibend=tool.name.startswith(SCHREIBEND_PRAEFIXE),
        ))
    return werkzeuge


if __name__ == "__main__":
    # Zeigt, was der MCP-Server anbietet, genau so, wie das Modell es sieht:
    #   docker compose run --rm app mcp_werkzeuge.py
    import json
    for w in mcp_werkzeuge():
        print(json.dumps(w.als_tool(), ensure_ascii=False, indent=2))
