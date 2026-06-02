from types import SimpleNamespace

from app.agent.news_agent import NewsAgent


def test_llm_proxy_only_for_llm_client_kwargs():
    agent = NewsAgent(SimpleNamespace(llm_http_proxy="http://127.0.0.1:7890", llm_api_key="", llm_base_url="", llm_model="x", agent_news_sources="sina"))
    llm_kwargs = agent._build_client_kwargs(timeout=10, use_llm_proxy=True)
    data_kwargs = agent._build_client_kwargs(timeout=10, use_llm_proxy=False)
    assert llm_kwargs.get("proxy") == "http://127.0.0.1:7890"
    assert "proxy" not in data_kwargs
    assert llm_kwargs.get("trust_env") is False and data_kwargs.get("trust_env") is False
