"""LLM factory so the rest of the code doesn't care which provider is used."""
from functools import lru_cache

from crag import config


@lru_cache(maxsize=4)
def get_llm(provider: str | None = None, temperature: float = 0.0):
    provider = (provider or config.LLM_PROVIDER).lower()
    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(model=config.GROQ_MODEL, temperature=temperature, max_retries=8)  # free tier = 8k tokens/min; retries wait it out
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=config.GEMINI_MODEL, temperature=temperature, max_retries=8)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r} (use 'groq' or 'gemini')")
