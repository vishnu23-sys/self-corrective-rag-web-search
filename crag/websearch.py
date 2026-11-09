"""Web search fallback via Tavily (free tier: https://tavily.com)."""
from crag import config


def web_search(query: str) -> list[dict]:
    if not config.TAVILY_API_KEY:
        return []
    from tavily import TavilyClient

    client = TavilyClient(api_key=config.TAVILY_API_KEY)
    resp = client.search(query, max_results=config.WEB_RESULTS)
    return [
        {"content": r.get("content", ""), "source": r.get("url", "web"), "score": r.get("score")}
        for r in resp.get("results", [])
    ]
