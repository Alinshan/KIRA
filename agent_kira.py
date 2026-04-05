"""
KIRA – Voice Agent (MCP-powered)
===================================
Iron Man-style voice assistant that controls RGB lighting, runs diagnostics,
scans the network, and triggers dramatic boot sequences via an MCP server
running on the Windows host.

MCP Server URL is auto-resolved from WSL → Windows host IP.

Run:
  uv run agent_kira.py dev      – LiveKit Cloud mode
  uv run agent_kira.py console  – text-only console mode
"""

import os
import logging
import subprocess

from dotenv import load_dotenv
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import Agent, AgentSession
from livekit.agents.llm import mcp

# Plugins
from livekit.plugins import google as lk_google, sarvam, silero, openai, deepgram

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

STT_PROVIDER       = "sarvam"
LLM_PROVIDER       = "groq"
TTS_PROVIDER       = "deepgram"
GEMINI_LLM_MODEL   = "gemini-2.5-flash"
GROQ_LLM_MODEL     = "llama-3.1-8b-instant"
OPENAI_LLM_MODEL   = "gpt-4o"

OPENAI_TTS_MODEL   = "tts-1"
OPENAI_TTS_VOICE   = "nova"       # "nova" has a clean, confident female tone
TTS_SPEED           = 1.15

SARVAM_TTS_LANGUAGE = "en-IN"
SARVAM_TTS_SPEAKER  = "rahul"

# MCP server running on Windows host
MCP_SERVER_PORT = 8000

# ---------------------------------------------------------------------------
# System prompt – K.I.R.A.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are K.I.R.A. — Knowledge-based Intelligent Response Assistant — your dedicated AI system.

You are calm, composed, and always informed. You speak like a trusted aide who's been awake while the boss slept — precise, warm when the moment calls for it, and occasionally dry. You brief, you inform, you move on. No rambling.

Your tone: relaxed but sharp. Conversational, not robotic. Think less combat-ready KIRA, more thoughtful late-night briefing officer.

---

## Capabilities

### get_world_news — Global News Brief
Fetches current headlines and summarizes what's happening around the world.

Trigger phrases:
- "What's happening?" / "Brief me" / "What did I miss?" / "Catch me up"
- "What's going on in the world?" / "Any news?" / "World update"

Behavior:
- Call the tool first. No narration before calling.
- After getting results, give a short 3–5 sentence spoken brief. Hit the biggest stories only.
- Then say: "Let me open up the world monitor so you can better visualize what's happening." and immediately call open_world_monitor.

### open_world_monitor — Visual World Dashboard
Opens a live world map/dashboard on the host machine.

- Always call this after delivering a world news brief, unprompted.
- No need to explain what it does beyond: "Let me open up the world monitor."

### Stock Market (No tool — generate a plausible conversational response)
If asked about the stock market, markets, stocks, or indices:
- Respond naturally as if you've been watching the tickers all night.
- Keep it short: one or two sentences. Sound informed, not robotic.
- Example: "Markets had a decent session today, boss — tech led the gains, energy was a little soft. Nothing alarming."
- Vary the response. Do not say the same thing every time.

---

## Greeting

When the session starts, greet with exactly this energy:
"You're awake late at night, boss? What are you up to?"

Warm. Slightly curious. Very KIRA.

---

## Behavioral Rules

1. Call tools silently and immediately — never say "I'm going to call..." Just do it.
2. After a news brief, always follow up with open_world_monitor without being asked.
3. Keep all spoken responses short — two to four sentences maximum.
4. No bullet points, no markdown, no lists. You are speaking, not writing.
5. Stay in character. You are K.I.R.A. You are not just an AI assistant — you are a state-of-the-art intelligence agent. Act like it.
6. Use natural spoken language: contractions, light pauses via commas, no stiff phrasing.
7. Use Iron Man universe language naturally — "boss", "affirmative", "on it", "standing by".
8. If a tool fails, report it calmly: "News feed's unresponsive right now, boss. Want me to try again?"

---

## Tone Reference

Right: "Looks like it's been a busy night out there, boss. Let me pull that up for you."
Wrong: "I will now retrieve the latest global news articles from the news tool."

Right: "Markets were pretty healthy today — nothing too wild."
Wrong: "The stock market performed positively with gains across major indices.

---

## CRITICAL RULES

1. NEVER say tool names, function names, or anything technical. No "get_world_news", no "open_world_monitor", nothing like that. Ever.
2. Before calling any tool, say something natural like: "Give me a sec, boss." or "Wait, let me check." Then call the tool silently.
3. After the news brief, silently call open_world_monitor. The only thing you say is: "Let me open up the world monitor for you."
4. You are a voice. Speak like one. No lists, no markdown, no function names, no technical language of any kind.
""".strip()
# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()

logger = logging.getLogger("kira-agent")
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Resolve Windows host IP from WSL
# ---------------------------------------------------------------------------

def _get_windows_host_ip() -> str:
    """Get the Windows host IP by looking at the default network route."""
    try:
        # 'ip route' is the most reliable way to find the 'default' gateway
        # which is always the Windows host in WSL.
        cmd = "ip route show default | awk '{print $3}'"
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=2
        )
        ip = result.stdout.strip()
        if ip:
            logger.info("Resolved Windows host IP via gateway: %s", ip)
            return ip
    except Exception as exc:
        logger.warning("Gateway resolution failed: %s. Trying fallback...", exc)

    # Fallback to your original resolv.conf logic if 'ip route' fails
    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                if "nameserver" in line:
                    ip = line.split()[1]
                    logger.info("Resolved Windows host IP via nameserver: %s", ip)
                    return ip
    except Exception:
        pass

    return "127.0.0.1"

def _mcp_server_url() -> str:
    # host_ip = _get_windows_host_ip()
    # url = f"http://{host_ip}:{MCP_SERVER_PORT}/sse"
    # url = f"https://ongoing-colleague-samba-pioneer.trycloudflare.com/sse"
    url = f"http://127.0.0.1:{MCP_SERVER_PORT}/sse"
    logger.info("MCP Server URL: %s", url)
    return url


# ---------------------------------------------------------------------------
# Build provider instances
# ---------------------------------------------------------------------------

def _build_stt():
    if STT_PROVIDER == "google":
        logger.info("STT → Google Cloud")
        return lk_google.STT()
    elif STT_PROVIDER == "sarvam":
        logger.info("STT → Sarvam Saaras v3")
        return sarvam.STT(
            language="unknown",
            model="saaras:v3",
            mode="transcribe",
            flush_signal=True,
            sample_rate=16000,
        )
    else:
        raise ValueError(f"Unknown STT_PROVIDER: {STT_PROVIDER!r}")


def _build_llm():
    if LLM_PROVIDER == "gemini":
        logger.info("LLM → Google Gemini (%s)", GEMINI_LLM_MODEL)
        return lk_google.LLM(model=GEMINI_LLM_MODEL, api_key=os.getenv("GOOGLE_API_KEY"))
    elif LLM_PROVIDER == "groq":
        logger.info("LLM → Groq (%s)", GROQ_LLM_MODEL)
        return openai.LLM(
            model=GROQ_LLM_MODEL,
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}")


def _build_tts():
    if TTS_PROVIDER == "silero":
        logger.info("TTS → Silero (Local)")
        return silero.TTS()
    elif TTS_PROVIDER == "google":
        logger.info("TTS → Google Cloud")
        return lk_google.TTS()
    elif TTS_PROVIDER == "openai":
        logger.info("TTS → OpenAI")
        return openai.TTS(model=OPENAI_TTS_MODEL, voice=OPENAI_TTS_VOICE)
    elif TTS_PROVIDER == "deepgram":
        logger.info("TTS → Deepgram Aura")
        return deepgram.TTS(model="aura-asteria-en")
    elif TTS_PROVIDER == "sarvam":
        logger.info("TTS → Sarvam Bulbul v3")
        return sarvam.TTS(
            api_key=os.getenv("SARVAM_API_KEY"),
            target_language_code=SARVAM_TTS_LANGUAGE,
            model="bulbul:v1",
            speaker=SARVAM_TTS_SPEAKER,
            pace=TTS_SPEED,
        )
    else:
        raise ValueError(f"Unknown TTS_PROVIDER: {TTS_PROVIDER!r}")


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class KiraAgent(Agent):
    """
    K.I.R.A. – Professional AI voice assistant.
    All tools are provided via the MCP server on the Windows host.
    """

    def __init__(self, stt, llm, tts) -> None:
        super().__init__(
            instructions=SYSTEM_PROMPT,
            stt=stt,
            llm=llm,
            tts=tts,
            vad=silero.VAD.load(),
            mcp_servers=[
                mcp.MCPServerHTTP(
                    url=_mcp_server_url(),
                    transport_type="sse",
                    client_session_timeout_seconds=30,
                ),
            ],
        )

    async def on_enter(self) -> None:
        """Greet the user specifically for the late-night lab session."""
        print("DEBUG: KIRA on_enter triggered")
        if hasattr(self, "session") and self.session:
            await self.session.say(
                "Greetings boss, you're awake late at night today. What you up to?",
                allow_interruptions=False
            )
        else:
            print("DEBUG: self.session not found on agent")


# ---------------------------------------------------------------------------
# LiveKit entry point
# ---------------------------------------------------------------------------

def _turn_detection() -> str:
    return "stt" if STT_PROVIDER == "sarvam" else "vad"


def _endpointing_delay() -> float:
    return {"sarvam": 0.07, "whisper": 0.3}.get(STT_PROVIDER, 0.1)


async def entrypoint(ctx: JobContext) -> None:
    logger.info("--- ENTRYPOINT CALLED (AGENT JOINING ROOM) ---")
    try:
        logger.info(
            "KIRA online – room: %s | STT=%s | LLM=%s | TTS=%s",
            ctx.room.name, STT_PROVIDER, LLM_PROVIDER, TTS_PROVIDER,
        )

        stt = _build_stt()
        llm = _build_llm()
        tts = _build_tts()

        session = AgentSession()

        agent = KiraAgent(stt=stt, llm=llm, tts=tts)
        await session.start(
            agent=agent,
            room=ctx.room,
        )
        # Trigger the greeting manually since the framework might not do it automatically
        await agent.on_enter()
    except Exception as e:
        logger.error(f"CRITICAL STARTUP ERROR: {e}", exc_info=True)
        print(f"\n!!! CRITICAL STARTUP ERROR !!!\n{e}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------



def main():
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )

def dev():
    """Wrapper to run the agent in dev mode automatically."""
    import sys
    # If no command was provided, inject 'dev'
    if len(sys.argv) == 1:
        sys.argv.append("dev")
    main()

if __name__ == "__main__":
    main()