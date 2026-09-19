"""
Prompt building for the narrative summary.
The LLM is now tasked with summarizing the macro news context of the day.
It does NOT need to state the index price or % change, as that is rendered
in the visual components of the brief.
"""

from src.config.markets_loader import CountryConfig
from src.fetch.resilience import ResolvedSnapshot

SYSTEM_PROMPT = """You are writing a focused macro summary of a country's stock market session for a professional investor.
Rules, no exceptions:
- DO NOT write an introductory or concluding sentence (e.g., "The Nikkei faced headwinds today."). Dive straight into the facts.
- DO NOT restate the index's closing price, daily percentage change, or YTD return.
- Structure: Exactly 2 paragraphs. Total length: ~150 words.
- Paragraph 1: The overarching macro drivers (central bank policy, economic data, global sentiment, commodities).
- Paragraph 2: Specific sector movements and notable big companies mentioned in the headlines.
- Every company mentioned must include its Bloomberg-format ticker in parentheses, e.g. Tencent (700 HK Equity).
- Do not invent a cause or mention companies not found in the headlines. If the headlines lack sector detail, keep it brief rather than hallucinating.
"""


def build_country_prompt(country_cfg: CountryConfig, snapshot: ResolvedSnapshot) -> str:
    lines = [
        f"Country: {country_cfg.name}",
        f"Index: {country_cfg.index_name} ({country_cfg.bloomberg})",
        "",
        "News Headlines from the last 24 hours:",
    ]
    
    if not snapshot.news_headlines:
        lines.append("- (No recent headlines available)")
    else:
        # Pass all headlines, LLM will synthesize them
        for h in snapshot.news_headlines:
            lines.append(f"- {h}")
            
    if snapshot.stale:
        lines.append("\nData freshness note: This market's data is stale (from a previous session).")

    lines.append("\nWrite the narrative summary now, based on these headlines.")
    return "\n".join(lines)
