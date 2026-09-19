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
2. Ban raw vendor tickers (e.g., convert "005930 KS Equity" to "Samsung Electronics (005930 KS)").
3. Eliminate corporate trivia (e.g., small local debt reallocations, routine contracts, CEO health rumors). Include single-stock movers only if they explain significant index delta or represent Tier-1 M&A.
4. Cross-Asset Synthesis: Regional stock movements must explicitly tie back to the core macro drivers established in Section 1 (rates, FX, sovereign yields, and commodity movements).
5. Focus purely on local domestic drivers. Do NOT write a generic global summary unless it explicitly caused a domestic sector to move.

OUTPUT JSON SCHEMA:
{
  "macro_driver": "One sentence summarizing the dominant macro catalyst (central bank action, domestic policy, FX intervention, or sovereign liquidity).",
  "sector_driver": "One sentence summarizing leading and lagging industry factors driving index return.",
  "key_movers": [
    {
      "company": "Company Name",
      "ticker": "Ticker (e.g., 005930 KS)",
      "delta": "1D % Change (if explicitly stated in the headlines, else null)",
      "context": "Material catalyst: M&A, verified earnings beat/miss, regulatory ruling. Limit to names driving index attribution."
    }
  ]
}
If there are no valid key movers in the headlines, return an empty list `[]` for key_movers.
"""


def build_country_prompt(country_cfg: CountryConfig, snapshot: ResolvedSnapshot) -> str:
    lines = [
        f"Country: {country_cfg.name}",
        f"Index: {country_cfg.index_name}",
        f"Daily Delta: {snapshot.change_pct}%",
        "Recent Headlines:"
    ]
    for h in snapshot.news_headlines:
        lines.append(f"- {h}")
        
    lines.append("\nGenerate the JSON output now.")
    return "\n".join(lines)


EXECUTIVE_SUMMARY_PROMPT = """You are a strictly deterministic JSON generator.
Your job is to read the individual country summaries and generate a 3-bullet Executive Summary and a punchy 3-6 word Subject Line.
Output ONLY valid JSON. No markdown blocks.

JSON SCHEMA:
{
  "subject": "Extremely short (3-6 words). e.g. Global Yields Spike on Fed Fears",
  "regime": "One-sentence synthesis defining the prevailing global macro backdrop (e.g., Fed terminal rate expectations, crude price pressures, regional currency divergence).",
  "bullet_1_global_regime": "1 bullet point on the primary equity factor or thematic driver (e.g., mega-cap tech vs. cyclical value).",
  "bullet_2_cross_asset": "1 bullet point on rates, currency transmission, and sovereign debt impact.",
  "bullet_3_catalysts": "1 bullet point on liquidity catalysts, geopolitical developments, or regional policy divergences."
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

CALENDAR_PROMPT = """You are a macro calendar analyst.
I am providing you with a raw list of economic events scheduled for the next 24 hours.
Your job is to synthesize this into a structured JSON list, adding a short 3-6 word "asset_impact" prediction for each event.

JSON SCHEMA:
{
  "events": [
    {
      "time": "HH:MM (Keep original time string)",
      "country": "Country",
      "event": "Event Name",
      "period": "MoM / YoY / Q / etc. (Infer from event name if possible, else leave blank)",
      "consensus": "Consensus Value",
      "prior": "Prior Value",
      "asset_impact": "Short 3-6 word prediction (e.g. 'USD/JPY volatility', 'Broad risk sentiment', 'Local tech stocks')"
    }
  ]
}
"""

def build_calendar_prompt(raw_events: list[dict]) -> str:
    import json
    lines = ["Here are the upcoming economic events:", json.dumps(raw_events, indent=2), "\nGenerate the JSON output now."]
    return "\n".join(lines)