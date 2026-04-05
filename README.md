# Friday — Tony Stark Demo MCP Server

A Model Context Protocol (MCP) server built with [FastMCP](https://github.com/jlowin/fastmcp).

## Project Structure

```
friday-tony-stark-demo/
├── server.py                  # Entry point — creates & runs the MCP server
├── pyproject.toml
├── .env.example               # Copy to .env and fill in keys
│
└── friday/                    # Main package
    ├── config.py              # Loads env vars and app-wide settings
    │
    ├── tools/                 # MCP Tools (callable by the LLM)
    │   ├── __init__.py        # register_all_tools()
    │   ├── web.py             # search_web, fetch_url
    │   ├── system.py          # get_current_time, get_system_info
    │   └── utils.py           # format_json, word_count
    │
    ├── prompts/               # MCP Prompts (reusable templates)
    │   ├── __init__.py        # register_all_prompts()
    │   └── templates.py       # summarize, explain_code
    │
    └── resources/             # MCP Resources (data exposed to the client)
        ├── __init__.py        # register_all_resources()
        └── data.py            # friday://info
```

## Getting Started

```bash
# 1. Install dependencies
pip install -e .

# 2. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run the server (stdio transport — for use with Claude Desktop etc.)
python server.py

# 4. Or run with SSE transport (for HTTP clients)
python server.py --transport sse
```

## Adding a New Tool

1. Create or open a file in `friday/tools/`
2. Define a `register(mcp)` function and decorate your tools with `@mcp.tool()`
3. Import and call `register(mcp)` inside `friday/tools/__init__.py`

## Transport Modes

| Mode | Use case |
|------|----------|
| `stdio` (default) | Claude Desktop, local LLM clients |
| `sse` | HTTP-based clients, web integrations |
