"""
Bloomberg ticker formatting per the outline's confirmed convention:
  - Indices:  "XXX Index"       e.g. "HSI Index", "SPX Index"
  - Stocks:   "TICKER CC Equity" e.g. "700 HK Equity", "AAPL US Equity"

The exchange-code table below is a starting point, not gospel — Phase 0
flagged China as needing manual care (Shanghai vs Shenzhen use different
codes/suffixes; a dual-listed stock needs the venue disambiguated).
Confirm against a real Bloomberg reference before this goes into
production copy that anyone other than you will read.
"""

EXCHANGE_CODES = {
    "USA": "US",
    "Japan": "JT",
    "China_Shanghai": "CH",   # verify — Shanghai-listed
    "China_Shenzhen": "CG",   # verify — Shenzhen-listed
    "Hong Kong": "HK",
    "Korea": "KS",
    "Indonesia": "IJ",
    "Singapore": "SP",
    "Philippines": "PM",
    "Vietnam": "VN",
}


def format_index(bloomberg_name: str) -> str:
    """markets.yaml already stores the correct 'XXX Index' string —
    this function exists mainly as a single place to fix formatting
    bugs later without touching every call site."""
    return bloomberg_name


def format_stock(ticker: str, country: str) -> str:
    code = EXCHANGE_CODES.get(country)
    if not code:
        return f"{ticker} [EXCHANGE UNCONFIRMED] Equity"
    return f"{ticker} {code} Equity"
