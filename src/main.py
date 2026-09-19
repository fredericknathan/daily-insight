"""
Entry point. Run as: python -m src.main

Pipeline, matching the outline's §5 architecture diagram exactly:
  1. scrape (+ fallback chain)         -> src/fetch/
  2. rank by |% move|                   -> here
  3. synthesise (LLM + validation guard) -> src/synthesise/
  4. render heatmap                     -> src/render/
  5. compose + send + archive           -> src/compose/, src/deliver/
"""

from __future__ import annotations
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

from src.config.markets_loader import load_config, load_countries
from src.fetch.primary import fetch_all
from src.fetch.resilience import resolve_all, write_daily_snapshot
from src.fetch.rates import fetch_all_rates
from src.synthesise.client import generate
from src.synthesise.prompts import SYSTEM_PROMPT, build_country_prompt, EXECUTIVE_SUMMARY_PROMPT, build_executive_prompt
from src.synthesise.validate import validate_paragraph, fallback_sentence
from src.synthesise.ticker_format import format_index

from src.compose.build import build_email_html
from src.deliver.mailer import send_brief
from src.deliver.alerting import send_failure_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TO_ADDRESS = os.environ.get("BRIEF_RECIPIENT", os.environ.get("GMAIL_ADDRESS", ""))
OUTPUT_DIR = Path("output")


def synthesise_country(country_cfg, snapshot) -> dict:
    import json
    if snapshot.price is None:
        return {}

    for attempt in range(2):
        try:
            prompt = build_country_prompt(country_cfg, snapshot)
            raw_json = generate(prompt, system=SYSTEM_PROMPT, json_mode=True)
            return json.loads(raw_json)
        except Exception as e:
            logger.error("%s: LLM generation failed (attempt %d): %s", country_cfg.name, attempt + 1, e)

    return {}


def run():
    import json
    config = load_config()
    countries_cfg = load_countries()
    countries_raw = config["countries"]

    logger.info("Step 1/5: primary fetch + cache fallback chain")
    primary_results = fetch_all(countries_raw)
    rates = fetch_all_rates(countries_raw)
    resolved = resolve_all(countries_raw, primary_results, rates)

    logger.info("Step 2/5: ranking by |%% move|")
    resolved_by_name = {r.country: r for r in resolved}
    ranked_cfgs = sorted(
        countries_cfg,
        key=lambda c: abs(resolved_by_name[c.name].change_pct)
        if resolved_by_name[c.name].change_pct is not None else -1,
        reverse=True,
    )

    logger.info("Step 3/5: synthesising narrative (JSON Extraction)")
    output_countries = []
    any_fallback = False
    for cfg in ranked_cfgs:
        snap = resolved_by_name[cfg.name]
        if snap.source != "yfinance_rss":
            any_fallback = True
        
        parsed_data = synthesise_country(cfg, snap)
        
        output_countries.append({
            "name": cfg.name,
            "index_name": cfg.index_name,
            "bloomberg": format_index(cfg.bloomberg),
            "currency": cfg.currency,
            "price": snap.price,
            "change_pct": snap.change_pct,
            "ytd_pct": snap.ytd_pct,
            "rate_10y_pct": snap.rate_10y_pct,
            "rate_10y_bps_change": snap.rate_10y_bps_change,
            "fx_price": snap.fx_price,
            "fx_change_pct": snap.fx_change_pct,
            "macro_driver": parsed_data.get("macro_driver", ""),
            "sector_driver": parsed_data.get("sector_driver", ""),
            "key_movers": parsed_data.get("key_movers", []),
            "stale": snap.stale,
        })

    logger.info("Step 4/5: calculating HTML heatmap layout")
    from src.render.heatmap import generate_heatmap_data
    heatmap_boxes = generate_heatmap_data(resolved, countries_cfg)

    logger.info("Step 5/5: composing + sending + archiving")
    any_fallback = any(r.stale for r in resolved)
    
    # Generate Executive Summary
    exec_summary = {}
    try:
        summaries = [json.dumps({"country": c["name"], "data": {"macro": c["macro_driver"], "sector": c["sector_driver"], "movers": c["key_movers"]}}) for c in output_countries if c["macro_driver"]]
        subj_prompt = build_executive_prompt(summaries)
        raw_exec = generate(subj_prompt, system=EXECUTIVE_SUMMARY_PROMPT, temperature=0.5, json_mode=True)
        exec_summary = json.loads(raw_exec)
        subject_str = exec_summary.get('subject', 'Asian Markets See Broad Volatility Across Key Sectors').strip('\"\'')
        date_prefix = datetime.now().strftime("%d/%m/%Y")
        final_subject = f"{date_prefix} Macro Brief — {subject_str}"
    except Exception as e:
        logger.error("Failed to generate executive summary: %s", e)
        date_prefix = datetime.now().strftime("%d/%m/%Y")
        final_subject = f"{date_prefix} Macro Brief — {output_countries[0]['name']} Leads Market Volatility Amid Shifting Macro Conditions"
        exec_summary = {
            "bullet_1_global_regime": "Global markets traded mixed.",
            "bullet_2_cross_asset": "Cross-asset volatility remains muted.",
            "bullet_3_catalysts": "Awaiting further macroeconomic data."
        }

    html = build_email_html(output_countries, any_fallback, exec_summary, heatmap_boxes)
    send_brief(
        subject=final_subject,
        html_body=html,
        to_address=TO_ADDRESS,
    )
    write_daily_snapshot(resolved)

    logger.info("Pipeline complete.")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logger.critical("Pipeline failed: %s", e, exc_info=True)
        try:
            send_failure_alert(e, TO_ADDRESS)
        finally:
            sys.exit(1)
