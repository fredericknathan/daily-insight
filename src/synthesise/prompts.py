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


SUBJECT_SYSTEM_PROMPT = """You are writing a short, punchy email subject line for a daily macro market brief.
Rules:
- Extremely short (3 to 6 words maximum).
- Capture the dominant global macro theme based on the provided country summaries.
- No punctuation at the end.
- Do not use quotes.
- Example: Tech Selloff Drags Asian Markets
- Example: Global Yields Spike on Fed Fears
"""

def build_subject_prompt(country_summaries: list[str]) -> str:
    lines = ["Here are the market summaries for today:", ""]
    for s in country_summaries:
        if s and "A narrative summary could not be generated" not in s:
            lines.append(s)
            lines.append("---")
    
    if len(lines) <= 2:
        return "Write a generic subject line like 'Mixed Global Markets'"
        
    lines.append("\nWrite the extremely short subject line now.")
    return "\n".join(lines)
