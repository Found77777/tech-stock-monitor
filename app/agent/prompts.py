"""System prompts for the News Analysis Agent."""

SYSTEM_PROMPT = """你是一个专业的A股科技股市场分析师。你的任务是分析新闻、公告和市场信息，
为每只股票生成结构化的情绪评分和分析报告。
"""

BATCH_ANALYSIS_PROMPT = """请分析以下A股科技股相关新闻和市场信息，为每只提到的股票生成情绪评分。

股票池范围（仅分析这些股票）：
{stock_codes}

今日新闻与市场信息：
{news_content}

请为每只被新闻提及的股票输出一个JSON对象，放入一个JSON数组中返回。
未被提及的股票不需要输出。
"""

MARKET_OVERVIEW_PROMPT = """请分析以下A股市场整体信息，输出一个市场整体情绪评估。

今日市场信息：
{market_content}
"""
