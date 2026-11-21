"""Settings for Agentic AI Training Lab 2. Set values in .env, not in this file."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


def setting(name, default=""):
    """Environment variable (or .env), then Colab Secret, then the default."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        from google.colab import userdata
        return userdata.get(name) or default
    except Exception:
        return default


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MANUALS = DATA / "manuals"
COPILOT = DATA / "copilot"
SUBMISSIONS = ROOT / "submissions"
RUNS = ROOT / "runs"
CACHE = ROOT / ".cache"

# Your ID, used in submission file names: letters and digits only.
PARTICIPANT = setting("PARTICIPANT", "P00")

# Language model: LLM_PROVIDER=anthropic (ANTHROPIC_API_KEY) or openrouter (OPENROUTER_API_KEY)
LLM_PROVIDER = setting("LLM_PROVIDER", "anthropic").lower()
ANTHROPIC_MODEL = setting("ANTHROPIC_MODEL", "claude-sonnet-4-6")
# Leave OPENROUTER_MODEL empty to pick a free model that accepts images automatically.
# Free models change often; `lab check` lists the current ones.
OPENROUTER_MODEL = setting("OPENROUTER_MODEL", "")

# Local embedding model. EMBEDDING_BACKEND=stand-in is an offline lexical stand-in, for testing only.
EMBEDDING_BACKEND = setting("EMBEDDING_BACKEND", "sentence-transformers")
EMBEDDING_MODEL = setting("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
QUERY_PREFIX = setting("QUERY_PREFIX", "")


def model_name():
    return ANTHROPIC_MODEL if LLM_PROVIDER == "anthropic" else OPENROUTER_MODEL
