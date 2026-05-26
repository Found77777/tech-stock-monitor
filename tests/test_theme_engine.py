from app.themes.theme_classifier import classify_theme
from app.themes.theme_registry import load_theme_registry
from app.themes.theme_scoring import evaluate_theme


def test_theme_registry_classify():
    df = load_theme_registry()
    assert len(df) >= 17
    c = classify_theme({"sector": "半导体设备", "theme": "国产替代"})
    assert c["primary_theme"]


def test_research_and_innovation_higher_scores():
    high = evaluate_theme({
        "sector": "工业软件",
        "theme": "信创",
        "rd_expense_ratio": 0.16,
        "rd_headcount_ratio": 0.4,
        "rd_master_ratio": 0.3,
        "rd_phd_ratio": 0.05,
        "rd_continuity_years": 4,
        "patent_invention_count": 300,
        "patent_growth_3y": 0.5,
        "theme_revenue_ratio": 0.6,
        "concept_purity": "core",
    })
    low = evaluate_theme({
        "sector": "消费电子",
        "theme": "相关",
        "rd_expense_ratio": 0.01,
        "rd_headcount_ratio": 0.05,
        "rd_continuity_years": 0,
        "patent_invention_count": 10,
        "patent_growth_3y": 0.0,
        "theme_revenue_ratio": 0.02,
        "concept_purity": "hype",
    })
    assert high["research_strength_score"] > low["research_strength_score"]
    assert high["theme_relevance_score"] > low["theme_relevance_score"]
    assert high["purity_score"] > low["purity_score"]


def test_theme_scores_not_nan():
    s = evaluate_theme({"sector": None, "theme": None})
    for k, v in s.items():
        if isinstance(v, (int, float)):
            assert v == v
