import asyncio
from fastapi.testclient import TestClient

from app.agent.news_agent import NewsAgent
from app.config import Settings
from app.main import app


class RaisingLLMAgent(NewsAgent):
    async def _fetch_all_news(self, stock_codes):
        return [
            {"stock_code": stock_codes[0], "title": f"{stock_codes[0]} 中标重大合同", "summary": "公司签约利好", "source": "test", "publish_time": "2026-06-01"}
        ]

    async def _call_llm(self, user_prompt: str) -> str:
        raise RuntimeError("llm unavailable")


def test_news_agent_llm_failure_uses_rule_fallback():
    agent = RaisingLLMAgent(Settings(_env_file=None, llm_api_key="x"))
    rows = asyncio.run(agent.analyze_stocks(["002465"]))
    assert rows
    assert rows[0]["stock_code"] == "002465"
    assert rows[0]["llm_fallback"] is True
    assert agent.last_llm_status == "call_failed"


def test_agent_health_and_config_validate_endpoints():
    client = TestClient(app)
    health = client.get("/agent/health")
    assert health.status_code == 200
    assert "enabled_news_sources" in health.json()
    cfg = client.get("/agent/config/validate")
    assert cfg.status_code == 200
    assert "ok" in cfg.json()
