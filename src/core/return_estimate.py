"""Return estimation: 3-scenario projected returns."""
import logging
import math

import numpy as np

logger = logging.getLogger(__name__)

_ANALYST_SPREAD_MULTIPLIER = 1.3  # Applied when analyst count < 3
_CAGR_CAP = 0.50                  # ±50% cap to prevent outlier inflation


def estimate_return(ticker: str, yahoo_client) -> dict:
    """Estimate 3-scenario annualised returns for a ticker.

    For equities: uses analyst price targets (High/Mean/Low) vs current price.
    For ETFs:     uses 2-year monthly return CAGR ± 1 standard deviation.

    Args:
        ticker: Ticker symbol.
        yahoo_client: YahooClient instance.

    Returns:
        {
            "ticker": str,
            "name": str,
            "is_etf": bool,
            "method": "analyst" | "cagr",
            "optimistic": float,    # annualised return as decimal (e.g. 0.15)
            "base": float,
            "pessimistic": float,
            "current_price": float | None,
            "note": str,
        }
    """
    ticker = ticker.strip().upper()
    info = yahoo_client.get_ticker_info(ticker)
    name = info.get("longName") or info.get("shortName") or ticker
    is_etf = yahoo_client.is_etf(ticker)
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")

    if is_etf:
        return _estimate_etf(ticker, name, current_price, yahoo_client)
    return _estimate_equity(ticker, name, current_price, yahoo_client)


# ------------------------------------------------------------------
# Equity: analyst target price method
# ------------------------------------------------------------------

def _estimate_equity(ticker: str, name: str, current_price, yahoo_client) -> dict:
    analyst = yahoo_client.get_analyst_data(ticker)
    target_high = analyst.get("target_high")
    target_mean = analyst.get("target_mean")
    target_low = analyst.get("target_low")
    analyst_count = analyst.get("analyst_count") or 0

    note = ""

    # Fallback: if analyst data is missing, return zeros
    if current_price is None or target_mean is None:
        return {
            "ticker": ticker,
            "name": name,
            "is_etf": False,
            "method": "analyst",
            "optimistic": 0.0,
            "base": 0.0,
            "pessimistic": 0.0,
            "current_price": current_price,
            "note": "アナリスト目標株価データなし",
        }

    base = (target_mean - current_price) / current_price

    # If high/low are missing or same as mean, synthesise spread
    if target_high is None or target_low is None or target_high == target_low == target_mean:
        spread = abs(base) * 0.3 if base != 0 else 0.05
        optimistic = base + spread
        pessimistic = base - spread
        note = "目標株価 High/Low が取得できなかったため自動スプレッドを適用"
    else:
        optimistic = (target_high - current_price) / current_price
        pessimistic = (target_low - current_price) / current_price

    # Spread expansion for thin analyst coverage
    if analyst_count < 3:
        mid = (optimistic + pessimistic) / 2
        half = (optimistic - pessimistic) / 2 * _ANALYST_SPREAD_MULTIPLIER
        optimistic = mid + half
        pessimistic = mid - half
        note += f"（アナリスト{analyst_count}名のため±スプレッドを{_ANALYST_SPREAD_MULTIPLIER}倍に拡張）"

    return {
        "ticker": ticker,
        "name": name,
        "is_etf": False,
        "method": "analyst",
        "optimistic": round(optimistic, 4),
        "base": round(base, 4),
        "pessimistic": round(pessimistic, 4),
        "current_price": current_price,
        "note": note.strip(),
    }


# ------------------------------------------------------------------
# ETF: CAGR from 2-year monthly returns
# ------------------------------------------------------------------

def _estimate_etf(ticker: str, name: str, current_price, yahoo_client) -> dict:
    history = yahoo_client.get_history(ticker, period="2y")

    if history.empty or "Close" not in history.columns:
        return {
            "ticker": ticker,
            "name": name,
            "is_etf": True,
            "method": "cagr",
            "optimistic": 0.0,
            "base": 0.0,
            "pessimistic": 0.0,
            "current_price": current_price,
            "note": "価格履歴データなし",
        }

    prices = history["Close"].dropna()
    if len(prices) < 24:
        return {
            "ticker": ticker,
            "name": name,
            "is_etf": True,
            "method": "cagr",
            "optimistic": 0.0,
            "base": 0.0,
            "pessimistic": 0.0,
            "current_price": current_price,
            "note": "価格履歴が24ヶ月未満のため試算不可",
        }

    # Resample to monthly end prices and compute monthly returns
    monthly = prices.resample("ME").last().dropna()
    monthly_returns = monthly.pct_change().dropna()

    if len(monthly_returns) < 2:
        return {
            "ticker": ticker,
            "name": name,
            "is_etf": True,
            "method": "cagr",
            "optimistic": 0.0,
            "base": 0.0,
            "pessimistic": 0.0,
            "current_price": current_price,
            "note": "月次リターンデータ不足",
        }

    # CAGR from total return over period
    n_months = len(monthly_returns)
    total_return = float((1 + monthly_returns).prod())
    if total_return <= 0:
        cagr = -0.99
    else:
        cagr = total_return ** (12 / n_months) - 1

    sigma = float(monthly_returns.std()) * math.sqrt(12)  # annualised std dev

    optimistic = min(cagr + sigma, _CAGR_CAP)
    pessimistic = max(cagr - sigma, -_CAGR_CAP)
    base = max(min(cagr, _CAGR_CAP), -_CAGR_CAP)

    note = f"過去{n_months}ヶ月の月次リターンから CAGR を算出。標準偏差 {sigma*100:.1f}% でシナリオ分岐。"

    return {
        "ticker": ticker,
        "name": name,
        "is_etf": True,
        "method": "cagr",
        "optimistic": round(optimistic, 4),
        "base": round(base, 4),
        "pessimistic": round(pessimistic, 4),
        "current_price": current_price,
        "note": note,
    }
