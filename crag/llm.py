"""LLM factory so the rest of the code doesn't care which provider is used."""
from functools import lru_cache

from crag import config


@lru_cache(maxsize=8)
def get_llm(provider: str | None = None, temperature: float = 0.0, model: str | None = None):
    provider = (provider or config.LLM_PROVIDER).lower()
    if provider == "groq":
        from langchain_groq import ChatGroq

        # free tier = 8k tokens/min per model; retries wait the limit out
        return ChatGroq(model=model or config.GROQ_MODEL, temperature=temperature, max_retries=8)
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model or config.GEMINI_MODEL, temperature=temperature, max_retries=8)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r} (use 'groq' or 'gemini')")


def get_judge_llm():
    """LLM used to grade answers in evaluation (can differ from the pipeline's LLM)."""
    return get_llm(config.JUDGE_PROVIDER, model=config.JUDGE_MODEL or None)
