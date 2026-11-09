"""Central settings. Everything can be overridden in the .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# --- LLM ---------------------------------------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()  # "groq" or "gemini"
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# Optional: a different model for the LLM-as-judge in evaluation (reduces self-bias)
JUDGE_PROVIDER = os.getenv("JUDGE_PROVIDER", LLM_PROVIDER).lower()

# --- Retrieval ---------------------------------------------------------
DOCS_DIR = ROOT / "data" / "docs"
CHROMA_DIR = ROOT / "data" / "chroma"
COLLECTION = os.getenv("COLLECTION", "knowledge_base")
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K = int(os.getenv("TOP_K", "4"))

# --- Web search --------------------------------------------------------
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
WEB_RESULTS = int(os.getenv("WEB_RESULTS", "3"))
