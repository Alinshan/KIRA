"""
Web tools — search, fetch pages, etc.
"""

import httpx


def register(mcp):

    @mcp.tool()
    async def search_web(query: str) -> str:
        """Search the web for a given query and return a summary of results."""
        # TODO: replace with your preferred search API (e.g. Brave, Tavily, SerpAPI)
        return f"[stub] Search results for: {query}"

    @mcp.tool()
    async def fetch_url(url: str) -> str:
        """Fetch the raw text content of a URL."""
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text[:4000]  # truncate to avoid token overflow
