from __future__ import annotations

EVENT_TYPES = {
    "policy_catalyst": ["政策", "国务院", "工信部", "补贴", "subsidy"],
    "company_order": ["中标", "订单", "合同"],
    "earnings": ["业绩", "财报", "预增", "预亏"],
    "product_launch": ["发布", "新品", "量产"],
    "capex": ["扩产", "产能", "资本开支"],
    "financing": ["定增", "融资", "股权激励"],
    "governance": ["高管", "董事会"],
    "risk_event": ["处罚", "减持", "爆雷"],
    "litigation": ["诉讼", "仲裁"],
    "export_control": ["出口管制", "禁令"],
    "subsidy": ["补贴", "财政支持"],
    "market_noise": ["异动", "传闻", "短线"],
}


def classify_event(text: str) -> str:
    t = (text or "").lower()
    for k, kws in EVENT_TYPES.items():
        if any(x.lower() in t for x in kws):
            return k
    return "unknown"
