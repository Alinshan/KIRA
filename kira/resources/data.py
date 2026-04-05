"""
Data resources — expose static content or dynamic data via MCP resources.
"""


def register(mcp):

    @mcp.resource("kira://info")
    def server_info() -> str:
        """Returns basic info about this MCP server."""
        return (
            "Kira MCP Server\n"
            "A Tony Stark-inspired AI assistant.\n"
            "Built with FastMCP."
        )
