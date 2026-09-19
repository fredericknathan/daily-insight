# Daily Macro Market Brief — Project Outline

**Status:** v0.4 — build-ready, all ticker questions resolved
**Owner:** Nathan
**Last updated:** 2026-09-19

---

## 1. Locked decisions

| Decision | Value |
|---|---|
| Delivery time | **06:00 HKT** (UTC+8, no DST — safe year-round, see §2) |
| Days | **Tue–Sat HKT** (= Mon–Fri US sessions) |
| Budget | **$0** |
| Countries | HK, CN, US, JP, KR, ID, SG, PH, VN |
| Format | Strict 9-country list (not restructured) |
| Paragraph length | **~20-second read** → target 50–60 words / 2–3 sentences per country |
| Country order | **Ranked by absolute % move**, biggest first |
| Ticker format | **Bloomberg convention** — `XXX Index` for indices, `TICKER CC Equity` for stocks |
| Rates | Include 10Y sovereign yield for all 9 countries |
| Commodities | Out of scope |
| Economic calendar | Out of scope |
| Email theme | Light mode only |
| Failure alerts | Email |
| History storage | Committed to the repo itself — see §7 |
| Data source | Perplexity Finance page scrape (primary) → yfinance (silent fallback) |
| LLM | GitHub Models (free, `GITHUB_TOKEN`-authenticated) |
| Scheduler | GitHub Actions, private repo, `timezone: Asia/Hong_Kong` |

---

## 2. Why 06:00 HKT works

Hong Kong has no DST; the US does. The gap between the US close and delivery now holds up year-round:

| Period | US close (ET) | = HKT | Buffer before 06:00 |
|---|---|---|---|
| EDT (~Mar–Nov) | 16:00 | 04:00 | 2 hrs |
| EST (~Nov–Mar) | 16:00 | 05:00 | 1 hr |

One hour is enough for closing prints to settle and for a scrape/fetch/compose pipeline to run. `05:00` would have zeroed this out every winter — good catch avoided.

`cron: '0 6 * * 2-6'` with `timezone: Asia/Hong_Kong` = Tuesday–Saturday HKT, which lines up with Monday–Friday US closes. Saturday's HKT run covers Friday's US session.

---

## 3. Data architecture — scrape-primary, API-fallback

### 3.1 Perplexity Finance scrape (primary)

`perplexity.ai/finance/{TICKER}` is a client-rendered SPA — a plain HTTP `GET` returns an empty shell. This needs a **headless browser**, not `requests`/`BeautifulSoup`.

```python
# src/fetch/perplexity_scrape.py — sketch
from playwright.sync_api import sync_playwright

def scrape_finance_page(ticker: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=REALISTIC_UA)
        page.goto(f"https://www.perplexity.ai/finance/{ticker}", wait_until="networkidle")
        page.wait_for_selector("[data-testid='price']", timeout=8000)
        price = page.locator("[data-testid='price']").inner_text()
        change_pct = page.locator("[data-testid='change-pct']").inner_text()
        news_items = page.locator("[data-testid='news-item']").all_inner_texts()
        browser.close()
        return {"price": price, "change_pct": change_pct, "news": news_items}
```

**Known fragility, designed around rather than ignored:**
- `data-testid` selectors are guesses — **Phase 0 must open dev tools on the real page and record actual selectors** before this is written for real.
- Bot detection may block the runner's IP outright (Cloudflare has previously documented Perplexity itself doing this kind of evasion against other sites — they're not casual about it on their own surface either).
- The page layout can change without notice; a broken selector should throw a clear, caught exception, not silently return empty data.
- Rate limit yourself even though nobody's charging you: 9–11 sequential page loads with 3–5s gaps, not a parallel burst.

**Resilience layer (non-negotiable):**
```
scrape Perplexity → succeeds → use it
              ↓ fails / selector breaks / blocked
        yfinance batch fetch → succeeds → use it, flag as "fallback source" in logs
              ↓ fails
        last committed good value from data/ → use it, flag as STALE in the email
```
This means a Perplexity block degrades the brief's freshness, not its existence.

### 3.2 News

Perplexity's page also surfaces recent news per ticker — scrape that alongside the price data in the same page load (no extra round-trip). If the scrape fails, fall back to direct publisher RSS (not Google News — see rationale below) filtered to items <12h old.

> **One thing to flag from the earlier research, still relevant:** if you ever *do* get quota headroom or reconsider the API later, Perplexity's own `finance_search` tool returns this exact same data (price + narrative + citations) legitimately for $5/1,000 calls. Worth remembering as a plan B if scraping proves too brittle to maintain.

### 3.3 Rates — 10Y sovereign yields for all 9 countries

No single free source covers all nine cleanly. Layered approach:

| Tier | Source | Coverage |
|---|---|---|
| 1 | **FRED API** (free key, 120 req/min) | US, Japan, Korea, and other OECD members reliably. **China, Indonesia, Philippines, Vietnam, Hong Kong, Singapore need verification** — FRED's non-OECD coverage is inconsistent |
| 2 | **yfinance** `^TNX` | US 10Y only, as a redundant cross-check |
| 3 | Scrape fallback (investing.com or TradingView's bonds page, same Playwright pattern as §3.1) | Whatever Tier 1 doesn't cover |

**Phase 0 must run all 9 countries through FRED first** and only build the scrape fallback for the ones that actually come back empty — don't build infrastructure you don't need.

### 3.4 Heatmap — Option A, confirmed

Cross-country index heatmap. 9 tiles (not 11 — dropping the earlier US-ETF idea since you didn't select it), colour = % change, sized uniformly or by nominal GDP. One `matplotlib` script, data already in hand from §3.1/3.2. No new fetch required.

### 3.5 LLM — GitHub Models, unchanged

Free, `GITHUB_TOKEN`-authenticated, no key to manage. Numbers are **injected** into the prompt from the scrape/fetch layer, never generated by the model — this is the one rule that isn't up for revision, because it's the difference between a brief you can trust and one you can't.

---

## 4. Ticker map — finalized (industry-standard index per country)

| Country | Index | Bloomberg | Yahoo (fallback) | Status |
|---|---|---|---|---|
| USA | S&P 500 | `SPX Index` | `^GSPC` | ✅ |
| Japan | Nikkei 225 | `NKY Index` | `^N225` | ✅ |
| China | CSI 300 | `SHSZ300 Index` | `000300.SS` | ✅ |
| Hong Kong | Hang Seng | `HSI Index` | `^HSI` | ✅ |
| Korea | KOSPI | `KOSPI Index` | `^KS11` | ✅ |
| Vietnam | VN-Index | `VNINDEX Index` | `^VNINDEX.VN` | ✅ |
| Indonesia | **Jakarta Composite (JCI)** | `JCI Index` | `^JKSE` | ✅ — industry-standard headline index, confirmed Yahoo coverage |
| Singapore | **Straits Times Index (STI)** | `STI Index` | `^STI` | ✅ |
| Philippines | **PSEi** | `PCOMP Index` | `^PSI` — **Phase 0 must still verify this Yahoo ticker actually resolves**, format unconfirmed | ⚠️ Only remaining open item, resolved in Phase 0 not before |

**Stock ticker format (per Bloomberg convention, for any company mentioned in the news):** `TICKER CC Equity` — e.g. Tencent → `700 HK Equity`, Bank Central Asia → `BBCA IJ Equity`, Samsung Electronics → `005930 KS Equity`, Apple → `AAPL US Equity`. Exchange codes to confirm in Phase 0: `HK`, `CH`/`CN` (China dual-listing needs care — Shanghai vs Shenzhen have different suffixes), `JT` (Japan), `KS` (Korea), `IJ` (Indonesia), `SP` (Singapore), `PM` (Philippines), `VN` (Vietnam).

---

## 5. Revised architecture

```
┌──────────────────────────────────────────────────────────┐
│  GitHub Actions — cron '0 6 * * 2-6'                     │
│  timezone: Asia/Hong_Kong                                │
└───────────────────────────┬──────────────────────────────┘
                            ▼
        ┌───────────────────────────────────────┐
        │  1. SCRAPE (primary)                  │
        │  • Playwright → perplexity.ai/finance │
        │    /{TICKER} × 9 indices + 10Y yields │
        │  • price, %chg, YTD, news per ticker  │
        │  • sequential, 3–5s gaps              │
        └───────────────────┬───────────────────┘
                            ▼  (on failure per-ticker)
        ┌───────────────────────────────────────┐
        │  1b. FALLBACK                         │
        │  • yfinance batch                     │
        │  • FRED for rates                     │
        │  • last committed good value          │
        │  • flag source + staleness in output  │
        └───────────────────┬───────────────────┘
                            ▼
        ┌───────────────────────────────────────┐
        │  2. RANK                              │
        │  • sort 9 countries by |% move| desc  │
        └───────────────────┬───────────────────┘
                            ▼
        ┌───────────────────────────────────────┐
        │  3. SYNTHESISE — GitHub Models         │
        │  • numbers INJECTED, never generated  │
        │  • 50–60 word cap per country          │
        │  • Bloomberg-format ticker annotation │
        │  • validate every % against source    │
        └───────────────────┬───────────────────┘
                            ▼
        ┌───────────────────────────────────────┐
        │  4. RENDER                            │
        │  • matplotlib → 9-tile index heatmap  │
        └───────────────────┬───────────────────┘
                            ▼
        ┌───────────────────────────────────────┐
        │  5. COMPOSE + SEND                    │
        │  • Jinja2 → premailer → light-mode CSS│
        │  • PNG as CID attachment              │
        │  • Gmail SMTP                         │
        │  • commit data/YYYY-MM-DD.json        │
        │  • on failure → alert email            │
        └───────────────────────────────────────┘
```

---

## 6. Repo structure

```
market-intelligence/
├── .github/workflows/
│   └── daily-brief.yml
├── src/
│   ├── config/
│   │   ├── markets.yaml          # index + stock exchange codes, Bloomberg suffixes
│   │   └── holidays.yaml         # exchange holiday calendars
│   ├── fetch/
│   │   ├── perplexity_scrape.py  # Playwright, primary source
│   │   ├── yfinance_fallback.py
│   │   ├── rates.py              # FRED primary, scrape fallback for gaps
│   │   └── cache.py              # reads data/ for last-good-value
│   ├── synthesise/
│   │   ├── client.py             # GitHub Models wrapper
│   │   ├── prompts.py            # 50–60 word cap enforced in prompt
│   │   ├── ticker_format.py      # Bloomberg-format annotation
│   │   └── validate.py           # number-hallucination guard
│   ├── render/
│   │   └── heatmap.py            # 9-tile matplotlib
│   ├── compose/
│   │   ├── templates/brief.html.j2   # light mode only
│   │   └── build.py
│   ├── deliver/
│   │   ├── mailer.py
│   │   └── alerting.py           # failure → email
│   └── main.py
├── data/                         # ← history lives here, see §7
│   └── 2026-09-19.json
├── tests/
│   └── test_smoke_tickers.py     # Phase 0 — build first
├── requirements.txt
├── .env.example
└── README.md
```

---

## 7. Where history is stored — answering Q14

**Committed straight into the repo, under `data/`.** One JSON file per day:

```json
{
  "date": "2026-09-19",
  "generated_at": "2026-09-19T06:00:14+08:00",
  "countries": [
    {
      "name": "China",
      "index": "SHSZ300 Index",
      "close": 4123.5,
      "change_pct": -0.42,
      "ytd_pct": 12.1,
      "rate_10y_pct": 1.86,
      "source": "perplexity_scrape",
      "narrative": "...",
      "mentioned_tickers": ["700 HK Equity", "9988 HK Equity"]
    }
  ]
}
```

**Why this, over an actual database:**
- **$0**, no signup, no expiry — GitHub private repos don't purge data
- **Free audit trail** — every commit is timestamped, so you get versioned history for nothing
- **Doubles as the fallback cache** in §3.1/3.3 — one mechanism serves two purposes
- **Queryable later** — `git log data/` or a small script over the JSON files gets you a backtest of the brief's own signal without standing up infrastructure

If the repo ever gets unwieldy (unlikely at 1 file/day for years), the exit path is trivial: `git filter-repo` the `data/` folder into its own repo, or migrate to SQLite committed as a single file. Not worth building now.

---

## 8. Build phases

### Phase 0 — De-risk (~4 hrs, do before anything else)
1. **Open `perplexity.ai/finance/^GSPC` in real dev tools** — record actual selectors/DOM structure. Do this for one index and one stock page; the structure should be consistent across tickers.
2. Run the same scrape from a GitHub Actions runner, not your laptop — confirm the datacenter IP isn't immediately blocked.
3. **Verify `^PSI` actually resolves on Yahoo** (last open item — everything else in the ticker map is confirmed).
4. Query FRED for all 9 countries' 10Y yields — record which ones return data and which need the scrape fallback.
5. Call GitHub Models from an Actions workflow with `models: read` — confirm no `403` (put the repo on your personal account, not an org, per earlier findings).
6. Send yourself one hardcoded HTML email with a CID PNG, light-mode CSS — confirm rendering in your actual client.

> If (1)/(2) fails outright, fall straight to the yfinance-primary design from v0.2 — it's already written and sitting in git history if you want to compare. If (5) fails, fall to Gemini/Groq free tier.

### Phase 1 — Data spine
Scrape + fallback chain, rate limiting, `data/` write, cache read-back.

### Phase 2 — Narrative
GitHub Models integration, 50–60 word cap, Bloomberg ticker annotation pass, number-validation guard, ranking by |% move|.

### Phase 3 — Visuals
9-tile heatmap.

### Phase 4 — Email
Light-mode Jinja2 template, premailer inlining, CID embedding, test in real client.

### Phase 5 — Automate
Workflow, `timezone: Asia/Hong_Kong`, `cron: '0 6 * * 2-6'`, secrets, `data/` commit, failure→email alerting.

### Phase 6 — Harden
Holiday calendars (Lunar New Year hits HK/CN/KR/SG/VN hardest), dead-man's-switch if no email by 06:30 HKT, scrape-selector monitoring (alert if the fallback path triggers 2+ days running — that's your signal the scrape needs fixing).

---

## 9. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| **LLM hallucinates a %** | 🔴 Critical | Inject numbers, never generate; regex-validate every figure against source |
| **Perplexity scrape blocked/selectors break** | 🔴 High | yfinance + cached fallback chain; alert when fallback triggers repeatedly |
| Rates data missing for smaller markets | 🟡 Medium | FRED-first, scrape-fallback only where needed; label unavailable rates explicitly rather than guessing |
| `^PSI` wrong/missing | 🟡 Medium | Phase 0 verification — last unresolved item |
| GitHub Models 403 on org repos | 🟡 Medium | Personal account; Gemini/Groq backup |
| Lunar New Year → 5 markets closed at once | 🟡 Medium | Holiday calendar; label closed markets, don't omit silently |
| GitHub cron delayed | 🟢 Low | Dead-man's-switch by 06:30 HKT |
| Bloomberg exchange-code errors (China dual-listing, etc.) | 🟢 Low | Verify suffix table in Phase 0 |

---

## 10. Summary

Scraping stays, built with a headless browser and a resilience chain so a block degrades freshness rather than breaking delivery outright — and the same free APIs from the last round (yfinance, FRED, GitHub Models) sit underneath as the safety net, so nothing from that research goes to waste. History lives as one committed JSON file per day in the repo itself, which is free, versioned, and doubles as your fallback cache. All 9 indices are now confirmed to the industry-standard headline index per country; the only item left for Phase 0 to verify is whether `^PSI` is the correct Yahoo fallback ticker for the PSEi.

---

## Appendix — Sources carried from v0.2 research

- GitHub Models free inference — github.blog
- GitHub Actions `timezone:` field — GitHub Changelog, March 2026
- FRED API — fred.stlouisfed.org (free key, 120 req/min)
- Bloomberg ticker convention — SMU Libraries FAQ; Bloomberg HBS guide
- yfinance rate limiting — ranaroussi/yfinance issues #2422, #2431
- Email HTML limitations — Mailchimp
