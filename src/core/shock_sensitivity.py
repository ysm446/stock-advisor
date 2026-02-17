"""Shock sensitivity mapping: ticker → scenario shock keys."""

# Sector name (from yfinance) → list of applicable shock keys
_SECTOR_SHOCK_KEYS: dict[str, list[str]] = {
    "Technology": ["technology", "equity"],
    "Communication Services": ["technology", "equity"],
    "Real Estate": ["real_estate", "equity"],
    "Energy": ["oil", "equity"],
    "Basic Materials": ["commodity", "equity"],
    "Consumer Cyclical": ["other_equity", "equity"],
    "Consumer Defensive": ["equity"],
    "Industrials": ["other_equity", "equity"],
    "Healthcare": ["healthcare", "equity"],
    "Financial Services": ["equity"],
    "Utilities": ["equity"],
}

# Keywords in longName/shortName → ETF asset class
_ETF_CLASS_KEYWORDS: list[tuple[list[str], str]] = [
    (["Gold", "金", "GOLD"], "gold"),
    (["Treasury", "T-Bond", "Treasur"], "treasury"),
    (["Long Bond", "Long-Bond", "20+", "長期債", "TLT"], "long_bond"),
    (["TIPS", "Inflation", "インフレ"], "tips"),
    (["Defense", "Aerospace", "防衛"], "defense"),
    (["Dividend", "Income", "インカム", "配当"], "equity_income"),
    (["Bond", "債券", "Fixed Income", "Credit"], "long_bond"),
]


def get_etf_class(ticker: str, info: dict) -> str | None:
    """Classify an ETF into an asset class used in scenario etf_overrides.

    Args:
        ticker: Ticker symbol.
        info: Ticker info dict from YahooClient.

    Returns:
        Asset class string (e.g. "gold", "long_bond") or None if unclassified.
    """
    name = (info.get("longName") or info.get("shortName") or ticker).upper()
    for keywords, asset_class in _ETF_CLASS_KEYWORDS:
        if any(kw.upper() in name for kw in keywords):
            return asset_class
    return None


def get_shock_mapping(ticker: str, yahoo_client) -> dict[str, float]:
    """Return the shock key → multiplier mapping for a ticker.

    For equities: maps sector to shock keys with multiplier = 1.0.
    For ETFs:     maps ETF asset class to shock key(s).

    Args:
        ticker: Ticker symbol.
        yahoo_client: YahooClient instance.

    Returns:
        Dict of {shock_key: multiplier}.  Falls back to {"equity": 1.0}.
    """
    info = yahoo_client.get_ticker_info(ticker)
    is_etf = yahoo_client.is_etf(ticker)

    if is_etf:
        etf_class = get_etf_class(ticker, info)
        if etf_class == "gold":
            return {"gold": 1.0}
        if etf_class in ("long_bond", "treasury"):
            return {"long_bond": 1.0, "bond": 1.0}
        if etf_class == "tips":
            return {"tips": 1.0, "bond": 0.5}
        if etf_class == "defense":
            return {"defense": 1.0, "equity": 0.5}
        if etf_class == "equity_income":
            return {"equity": 1.0}
        # Generic equity ETF
        return {"equity": 1.0}

    # Equity: sector-based mapping
    sector = info.get("sector") or ""
    shock_keys = _SECTOR_SHOCK_KEYS.get(sector, ["equity"])
    return {k: 1.0 for k in shock_keys}
