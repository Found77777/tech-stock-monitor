"""Validation helpers for AI agent configuration."""
from __future__ import annotations

from typing import Any

SUPPORTED_NEWS_SOURCES = {"sina", "eastmoney", "cninfo", "baidu", "rss"}


def validate_agent_config(settings: Any) -> dict:
    """Return structured validation details without raising on recoverable issues."""
    raw_sources = str(getattr(settings, "agent_news_sources", "") or "")
    requested = [x.strip().lower() for x in raw_sources.split(",") if x.strip()]
    unsupported = sorted({x for x in requested if x not in SUPPORTED_NEWS_SOURCES})
    enabled = [x for x in requested if x in SUPPORTED_NEWS_SOURCES]
    warnings: list[str] = []
    errors: list[str] = []

    if unsupported:
        warnings.append(f"unsupported news sources ignored: {', '.join(unsupported)}")
    if not enabled:
        errors.append("no supported news sources configured")

    llm_api_key = str(getattr(settings, "llm_api_key", "") or "")
    llm_base_url = str(getattr(settings, "llm_base_url", "") or "")
    if llm_api_key and not llm_base_url:
        errors.append("llm_api_key is set but llm_base_url is empty")
    if not llm_api_key:
        warnings.append("llm_api_key is empty; agent will use rule-based fallback")

    return {
        "ok": not errors,
        "enabled_news_sources": enabled,
        "unsupported_news_sources": unsupported,
        "llm_configured": bool(llm_api_key),
        "llm_proxy_configured": bool(str(getattr(settings, "llm_http_proxy", "") or "")),
        "warnings": warnings,
        "errors": errors,
    }
