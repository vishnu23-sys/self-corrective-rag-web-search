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

# --- Prompt variants -----------------------------------------------------
# Which relevance-grader prompt to use: zero_shot | few_shot | cot | few_shot_cot | batch_few_shot
# (compare them with: python -m eval.prompt_experiment)
GRADER_VARIANT = os.getenv("GRADER_VARIANT", "batch_few_shot")
# Optional: a different (e.g. smaller, cheaper) model just for grading; empty = same as GROQ_MODEL
GRADER_MODEL = os.getenv("GRADER_MODEL", "")
# Optional: a different Groq model for the evaluation judge (own rate limit, less self-bias)
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "")
