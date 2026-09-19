"""
Prompt building for the narrative summary.
The LLM is now tasked with summarizing the macro news context of the day.
It does NOT need to state the index price or % change, as that is rendered
in the visual components of the brief.
"""

from src.config.markets_loader import CountryConfig
from src.fetch.resilience import ResolvedSnapshot

SYSTEM_PROMPT = """You are a strictly deterministic macro data extraction parser.
Your only job is to extract market drivers from the provided news headlines and output a valid JSON object.
You must NOT output any markdown blocks, conversational text, or anything other than pure JSON.

RULES:
1. Ban transition filler words completely: "meanwhile," "notably," "lingering fatigue," "on the other hand."
2. Ban raw vendor tickers (e.g., convert "005930 KS Equity" to "Samsung Electronics" or format as "Samsung Electronics (005930)").
3. Filter out mid/small-cap company news. Only extract companies if they are specifically cited as driving the broader market index.
4. Focus purely on local domestic drivers (local economic data, local companies). Do NOT write a generic global summary unless it explicitly caused a domestic sector to move.

OUTPUT JSON SCHEMA:
{
  "macro_driver": "1 sentence summarizing the dominant macro catalyst (central bank, FX, liquidity, or global regime transfer).",
  "sector_driver": "1 sentence summarizing which specific domestic sectors drove the index delta.",
  "key_movers": [
    {
      "company": "Company Name",
      "delta": "Price change % (if explicitly stated in the headlines, else null)",
      "context": "1 short sentence explaining why this stock moved and drove the index."
    }
  ]
}
If there are no valid key movers in the headlines, return an empty list `[]` for key_movers.
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


EXECUTIVE_SUMMARY_PROMPT = """You are a strictly deterministic JSON generator.
Your job is to read the individual country summaries and generate a 3-bullet Executive Summary and a punchy 3-6 word Subject Line.
Output ONLY valid JSON. No markdown blocks.

JSON SCHEMA:
{
  "subject": "Extremely short (3-6 words). e.g. Global Yields Spike on Fed Fears",
  "bullet_1_global_regime": "1 bullet point on the overarching global regime or theme today.",
  "bullet_2_cross_asset": "1 bullet point on cross-asset transmission (FX, Rates, Commodities impacting equities).",
  "bullet_3_catalysts": "1 bullet point on key upcoming catalysts or the most dominant idiosyncratic driver."
}
"""

def build_executive_prompt(country_jsons: list[str]) -> str:
    lines = ["Here are the structured JSON summaries for today's markets:", ""]
    for s in country_jsons:
        if s and "fallback" not in s:
            lines.append(s)
            lines.append("---")
            
    lines.append("\nGenerate the JSON output now.")
    return "\n".join(lines)
