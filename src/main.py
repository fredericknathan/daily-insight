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

from src.config.markets_loader import load_config, load_countries
from src.fetch.primary import fetch_all
from src.fetch.resilience import resolve_all, write_daily_snapshot
from src.fetch.rates import fetch_all_rates
from src.synthesise.client import generate
from src.synthesise.prompts import SYSTEM_PROMPT, build_country_prompt, SUBJECT_SYSTEM_PROMPT, build_subject_prompt
from src.synthesise.validate import validate_paragraph, fallback_sentence
from src.synthesise.ticker_format import format_index
from src.render.heatmap import render_heatmap
from src.compose.build import build_email_html
from src.deliver.mailer import send_brief
from src.deliver.alerting import send_failure_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TO_ADDRESS = os.environ.get("BRIEF_RECIPIENT", os.environ.get("GMAIL_ADDRESS", ""))
OUTPUT_DIR = Path("output")


def synthesise_country(country_cfg, snapshot) -> str:
    """LLM attempts to summarize the macro narrative based on headlines."""
    if snapshot.price is None:
        return fallback_sentence(country_cfg.name, country_cfg.index_name, snapshot)

    for attempt in range(2):
        try:
            prompt = build_country_prompt(country_cfg, snapshot)
            paragraph = generate(prompt, system=SYSTEM_PROMPT)
            return paragraph
        except Exception as e:
            logger.error("%s: LLM generation failed (attempt %d): %s", country_cfg.name, attempt + 1, e)

    logger.warning("%s: falling back to template sentence after failed generation", country_cfg.name)
    return fallback_sentence(country_cfg.name, country_cfg.index_name, snapshot)


def run():
    config = load_config()
    countries_cfg = load_countries()
    countries_raw = config["countries"]

    logger.info("Step 1/5: primary fetch + cache fallback chain")
    primary_results = fetch_all(countries_raw)
    resolved = resolve_all(countries_raw, primary_results)
    rates = fetch_all_rates(countries_raw)

    logger.info("Step 2/5: ranking by |%% move|")
    resolved_by_name = {r.country: r for r in resolved}
    ranked_cfgs = sorted(
        countries_cfg,
        key=lambda c: abs(resolved_by_name[c.name].change_pct)
        if resolved_by_name[c.name].change_pct is not None else -1,
        reverse=True,
    )

    logger.info("Step 3/5: synthesising narrative (GitHub Models + validation guard)")
    output_countries = []
    any_fallback = False
    for cfg in ranked_cfgs:
        snap = resolved_by_name[cfg.name]
        if snap.source != "yfinance_rss":
            any_fallback = True
        paragraph = synthesise_country(cfg, snap)
        output_countries.append({
            "name": cfg.name,
            "index_name": cfg.index_name,
            "bloomberg": format_index(cfg.bloomberg),
            "price": snap.price,
            "change_pct": snap.change_pct,
            "ytd_pct": snap.ytd_pct,
            "rate_10y_pct": rates.get(cfg.name),
            "paragraph": paragraph,
            "stale": snap.stale,
        })

    logger.info("Step 4/5: rendering heatmap")
    OUTPUT_DIR.mkdir(exist_ok=True)
    heatmap_path = str(OUTPUT_DIR / "heatmap.png")
    render_heatmap(resolved, countries_cfg, heatmap_path)

    logger.info("Step 5/5: composing + sending + archiving")
    
    # Generate dynamic subject line
    try:
        summaries = [c["paragraph"] for c in output_countries]
        subj_prompt = build_subject_prompt(summaries)
        generated_subject = generate(subj_prompt, system=SUBJECT_SYSTEM_PROMPT, temperature=0.5)
        # Strip quotes just in case
        generated_subject = generated_subject.strip('"\'')
        final_subject = f"Daily Macro Brief — {generated_subject}"
    except Exception as e:
        logger.error("Failed to generate subject line, using fallback: %s", e)
        final_subject = f"Daily Macro Brief — {output_countries[0]['name']} leads the move"

    html = build_email_html(output_countries, any_fallback)
    send_brief(
        subject=final_subject,
        html_body=html,
        heatmap_path=heatmap_path,
        to_address=TO_ADDRESS,
    )
    write_daily_snapshot(resolved, rates)

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
