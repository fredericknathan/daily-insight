# Daily Macro Brief

8-country index brief, fetched via `yfinance` and Google News RSS with a cache
fallback chain, synthesised by GitHub Models (free), delivered by email at
06:00 HKT via GitHub Actions. Full design rationale in `PROJECT_OUTLINE.md`
(carry that file over from the planning conversation — it's the spec this
code was built against).

## ⚠️ Start here: Phase 0

**Nothing else in this repo should be trusted until Phase 0 passes.** It
tests whether `yfinance` and Google News RSS are actually returning fresh data for all markets.

### Run it

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium  # Keep for future rates scraping if needed

python tests/test_smoke_tickers.py
```

This tests every ticker and prints `PASS`/`FAIL` to the console, and writes `tests/phase0_results.json`. 

### Then check rates coverage

```bash
export FRED_API_KEY=your_free_key   # register at fred.stlouisfed.org
python -m src.fetch.rates
```

This prints which of the countries FRED actually covers. Anything that
comes back `NOT FOUND / EMPTY` needs either a manually-sourced FRED series
ID or a different rates scrape source (e.g. Investing.com).

### Then check GitHub Models from Actions, not just locally

Push this repo to **your personal GitHub account** (not an org — see the
docstring in `src/synthesise/client.py` for why), then run the workflow
manually once via the Actions tab's "Run workflow" button before trusting
the schedule. Check the log for a clean LLM response, not a 403.

### Then test the email rendering

```bash
python -m src.main   # will fail without real secrets, that's expected —
                      # but check output/heatmap.png got created, and
                      # sanity-check the HTML build.py produces
```

Once Phase 0 passes, everything downstream (`src/main.py`
onward) should mostly just work.

## Repo secrets needed (Settings → Secrets and variables → Actions)

| Secret | Where to get it |
|---|---|
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | myaccount.google.com/apppasswords (needs 2FA on first) |
| `BRIEF_RECIPIENT` | Usually same as GMAIL_ADDRESS |
| `FRED_API_KEY` | fred.stlouisfed.org, free, no card |

`GITHUB_TOKEN` is injected automatically by Actions — do not set it manually.
