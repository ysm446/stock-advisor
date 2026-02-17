"""Scenario analysis engine: compute per-ticker and portfolio-level shock impacts."""
import logging
from typing import Optional

from src.core.concentration import calculate_hhi, classify_hhi
from src.core.correlation import (
    calculate_correlation_matrix,
    calculate_var,
    fetch_returns,
    top_correlated_pair,
)
from src.core.shock_sensitivity import get_etf_class, get_shock_mapping

logger = logging.getLogger(__name__)


def run_scenario(
    tickers: list[str],
    scenario_key: str,
    scenarios: dict,
    yahoo_client,
    weights: Optional[list[float]] = None,
) -> dict:
    """Run a stress test scenario for a list of tickers.

    Args:
        tickers: Ticker symbols to analyse.
        scenario_key: Key from the scenarios dict (e.g. "triple_decline").
        scenarios: Loaded scenarios.yaml dict.
        yahoo_client: YahooClient instance.
        weights: Optional portfolio weights (market values or ratios).
                 Equal-weighted if None.

    Returns:
        Result dict with keys:
          scenario_name, scenario_description, hhi, hhi_label,
          ticker_impacts, portfolio_impact, var_95, var_99,
          correlation_summary, error.
    """
    if scenario_key not in scenarios:
        return {"error": f"シナリオ '{scenario_key}' が見つかりません。"}

    scenario = scenarios[scenario_key]
    shocks: dict = scenario.get("shocks", {})
    etf_overrides: dict = scenario.get("etf_overrides", {})
    sector_multipliers: dict = scenario.get("sector_multipliers", {})

    if not tickers:
        return {"error": "ティッカーが指定されていません。"}

    # --- Per-ticker impact ---
    ticker_impacts = []
    impact_values: list[float] = []

    for ticker in tickers:
        ticker = ticker.strip().upper()
        info = yahoo_client.get_ticker_info(ticker)
        name = info.get("longName") or info.get("shortName") or ticker
        sector = info.get("sector") or "-"
        is_etf = yahoo_client.is_etf(ticker)

        impact = _compute_impact(
            ticker, info, is_etf, shocks, etf_overrides, sector_multipliers, yahoo_client
        )
        impact_values.append(impact)
        shock_label = _describe_shock(ticker, info, is_etf, shocks, etf_overrides, yahoo_client)

        ticker_impacts.append({
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "is_etf": is_etf,
            "impact_pct": round(impact, 4),
            "shock_applied": shock_label,
        })

    # Sort by impact (worst first)
    ticker_impacts.sort(key=lambda x: x["impact_pct"])

    # --- HHI ---
    w = weights if weights and len(weights) == len(tickers) else [1.0] * len(tickers)
    hhi = calculate_hhi(w)
    hhi_label = classify_hhi(hhi)

    # --- Portfolio-level weighted impact ---
    total_w = sum(w)
    portfolio_impact = (
        sum(imp * wi for imp, wi in zip(impact_values, w)) / total_w
        if total_w > 0
        else 0.0
    )

    # --- Correlation & VaR ---
    var_95 = 0.0
    var_99 = 0.0
    corr_summary = ""
    try:
        returns = fetch_returns(tickers, yahoo_client)
        if not returns.empty:
            corr_matrix = calculate_correlation_matrix(returns)
            aligned_w = _align_weights(tickers, returns.columns.tolist(), w)
            var_95 = calculate_var(returns, aligned_w, confidence=0.95)
            var_99 = calculate_var(returns, aligned_w, confidence=0.99)
            corr_summary = top_correlated_pair(corr_matrix)
    except Exception as e:
        logger.warning("Correlation/VaR calculation failed: %s", e)

    return {
        "scenario_name": scenario.get("name", scenario_key),
        "scenario_description": scenario.get("description", ""),
        "hhi": round(hhi, 4),
        "hhi_label": hhi_label,
        "ticker_impacts": ticker_impacts,
        "portfolio_impact": round(portfolio_impact, 4),
        "var_95": var_95,
        "var_99": var_99,
        "correlation_summary": corr_summary,
        "error": None,
    }


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _compute_impact(
    ticker: str,
    info: dict,
    is_etf: bool,
    shocks: dict,
    etf_overrides: dict,
    sector_multipliers: dict,
    yahoo_client,
) -> float:
    """Compute the estimated return impact (decimal) for a single ticker."""
    # ETF with explicit override
    if is_etf:
        etf_class = get_etf_class(ticker, info)
        if etf_class and etf_class in etf_overrides:
            return float(etf_overrides[etf_class])

    # Get shock keys for the ticker
    shock_map = get_shock_mapping(ticker, yahoo_client)

    # Find the most specific applicable shock
    best_shock = None
    best_key = None
    for shock_key in shock_map:
        if shock_key in shocks:
            # Prefer more specific keys (non-equity) over generic equity
            if best_shock is None or (shock_key != "equity" and best_key == "equity"):
                best_shock = shocks[shock_key]
                best_key = shock_key

    if best_shock is None:
        # Fallback to equity shock
        best_shock = shocks.get("equity", shocks.get("other_equity", 0.0))
        best_key = "equity"

    # Apply sector multiplier if defined
    sector = info.get("sector") or ""
    multiplier = sector_multipliers.get(sector, 1.0)
    return float(best_shock) * multiplier


def _describe_shock(
    ticker: str,
    info: dict,
    is_etf: bool,
    shocks: dict,
    etf_overrides: dict,
    yahoo_client,
) -> str:
    """Return a short label describing which shock was applied."""
    if is_etf:
        etf_class = get_etf_class(ticker, info)
        if etf_class and etf_class in etf_overrides:
            return f"ETF({etf_class})"
    shock_map = get_shock_mapping(ticker, yahoo_client)
    for key in shock_map:
        if key in shocks and key != "equity":
            return key
    return "equity"


def _align_weights(
    tickers: list[str], available: list[str], weights: list[float]
) -> list[float]:
    """Align weights to the available tickers in the returns DataFrame."""
    w_map = dict(zip(tickers, weights))
    aligned = [w_map.get(t, 0.0) for t in available]
    total = sum(aligned)
    if total <= 0:
        n = len(available)
        return [1.0 / n] * n
    return [wi / total for wi in aligned]
