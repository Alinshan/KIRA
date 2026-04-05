"""
Kira MCP Server — Entry Point
Run with: python server.py
"""

import logging
from starlette.responses import HTMLResponse, Response
from mcp.server.fastmcp import FastMCP
from kira.tools import register_all_tools
from kira.prompts import register_all_prompts
from kira.resources import register_all_resources
from kira.config import config

# Create the MCP server instance
mcp = FastMCP(
    name=config.SERVER_NAME,
    instructions=(
        "You are Kira, a Tony Stark-style AI assistant. "
        "You have access to a set of tools to help the user. "
        "Be concise, accurate, and a little witty."
    ),
)

# Register tools, prompts, and resources
register_all_tools(mcp)
register_all_prompts(mcp)
register_all_resources(mcp)

# --- UI Enhancement: Professional Landing Page ---

LANDING_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>K.I.R.A. | Intelligence Engine</title>
    <style>
        :root {
            --primary: #e0a96d;
            --bg: #0a0a0a;
            --text: #ffffff;
            --accent: #2c2c2c;
        }
        body {
            margin: 0;
            padding: 0;
            font-family: 'Inter', -apple-system, system-ui, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            overflow: hidden;
        }
        .container {
            text-align: center;
            animation: fadeIn 1.5s ease-out;
            padding: 3rem;
            border: 1px solid var(--accent);
            border-radius: 24px;
            background: rgba(44, 44, 44, 0.2);
            backdrop-filter: blur(12px);
            box-shadow: 0 0 40px rgba(224, 169, 109, 0.15);
        }
        h1 {
            font-size: 4.5rem;
            font-weight: 800;
            letter-spacing: -3px;
            margin: 0;
            background: linear-gradient(45deg, #e0a96d, #ffffff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        p {
            color: #aaa;
            font-size: 1.25rem;
            margin: 1.2rem 0;
            max-width: 450px;
            line-height: 1.6;
            font-weight: 300;
        }
        .status {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            padding: 12px 24px;
            border-radius: 50px;
            background: rgba(0, 255, 127, 0.08);
            border: 1px solid rgba(0, 255, 127, 0.2);
            color: #00ff7f;
            font-size: 1.1rem;
            font-weight: 600;
            margin-top: 3rem;
        }
        .dot {
            width: 10px;
            height: 10px;
            background-color: #00ff7f;
            border-radius: 50%;
            box-shadow: 0 0 15px #00ff7f;
            animation: pulse 2.5s infinite;
        }
        .endpoint {
            margin-top: 2.5rem;
            font-family: 'Fira Code', monospace;
            font-size: 0.9rem;
            color: var(--primary);
            opacity: 0.5;
            letter-spacing: 1px;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(40px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.6); opacity: 0.4; }
            100% { transform: scale(1); opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>K.I.R.A.</h1>
        <p>Knowledge-based Intelligent Response Assistant</p>
        <div class="status">
            <div class="dot"></div>
            Intelligence Engine Online
        </div>
        <div class="endpoint">MCP Protocol Active: /sse</div>
    </div>
</body>
</html>
"""

async def root(request):
    return HTMLResponse(content=LANDING_PAGE)

async def favicon(request):
    return Response(status_code=204)

# Monkey patch FastMCP to include the custom landing page on the SSE app
_original_sse_app = mcp.sse_app
def patched_sse_app(*args, **kwargs):
    app = _original_sse_app(*args, **kwargs)
    app.add_route("/", root)
    app.add_route("/favicon.ico", favicon)
    return app
mcp.sse_app = patched_sse_app

def main():
    mcp.run(transport='sse')

if __name__ == "__main__":
    main()