"""Entry point with dual transport (Sormena pattern).

stdio for Claude Desktop; streamable-http / sse for cloud (Render, Railway).
Host/port are set on mcp.settings BEFORE run() — not passed as kwargs.
"""

import os

from .server import mcp


def main() -> None:
    transport = os.environ.get("SWISS_HOUSING_TRANSPORT", "stdio")
    if transport in ("streamable-http", "sse"):
        # Bind to loopback by default (SEC-016 / NeighborJack): the HTTP
        # transports must not expose all interfaces unless a deployment
        # explicitly opts in with HOST=0.0.0.0. stdio does not bind at all.
        mcp.settings.host = os.environ.get("HOST", "127.0.0.1")
        mcp.settings.port = int(os.environ.get("PORT", "8000"))
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
