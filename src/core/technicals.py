"""Technical indicator calculations."""
from typing import Optional

import numpy as np
import pandas as pd


def calculate_sma(prices: pd.Series, window: int) -> pd.Series:
    """Simple moving average.

    Args:
        prices: Closing price series.
        window: Lookback period in days.

    Returns:
        SMA series (NaN for insufficient data).
    """
    return prices.rolling(window=window).mean()


def calculate_rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (0–100).

    Args:
        prices: Closing price series.
        window: RSI period (default 14).

    Returns:
        RSI series (NaN for insufficient data).
    """
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=window - 1, min_periods=window).mean()
    avg_loss = loss.ewm(com=window - 1, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def detect_cross(fast: pd.Series, slow: pd.Series) -> str:
    """Detect the most recent golden or dead cross.

    Compares the last two data points of fast and slow moving averages.

    Args:
        fast: Faster MA (e.g. SMA50).
        slow: Slower MA (e.g. SMA200).

    Returns:
        "golden" if fast just crossed above slow,
        "dead"   if fast just crossed below slow,
        "none"   otherwise.
    """
    fast = fast.dropna()
    slow = slow.dropna()
    common = fast.index.intersection(slow.index)
    if len(common) < 2:
        return "none"
    idx = common[-2:]
    prev_above = fast[idx[0]] > slow[idx[0]]
    curr_above = fast[idx[1]] > slow[idx[1]]
    if not prev_above and curr_above:
        return "golden"
    if prev_above and not curr_above:
        return "dead"
    return "none"


def get_technical_signals(history: pd.DataFrame) -> dict:
    """Compute a set of technical signals from OHLCV history.

    Args:
        history: DataFrame with a "Close" column and DatetimeIndex.

    Returns:
        Dict with keys:
          current_price, sma50, sma200, rsi, cross,
          above_sma50, above_sma200, sma50_near_sma200.
        Values are None when insufficient data.
    """
    result: dict = {
        "current_price": None,
        "sma50": None,
        "sma200": None,
        "rsi": None,
        "cross": "none",
        "above_sma50": False,
        "above_sma200": False,
        "sma50_near_sma200": False,
    }

    if history.empty or "Close" not in history.columns:
        return result

    prices = history["Close"].dropna()
    if prices.empty:
        return result

    current = float(prices.iloc[-1])
    result["current_price"] = current

    sma50 = calculate_sma(prices, 50)
    sma200 = calculate_sma(prices, 200)

    if not sma50.empty and not sma50.isna().all():
        s50 = float(sma50.iloc[-1])
        if not np.isnan(s50):
            result["sma50"] = s50
            result["above_sma50"] = current > s50

    if not sma200.empty and not sma200.isna().all():
        s200 = float(sma200.iloc[-1])
        if not np.isnan(s200):
            result["sma200"] = s200
            result["above_sma200"] = current > s200

    rsi_series = calculate_rsi(prices)
    if not rsi_series.empty and not rsi_series.isna().all():
        rsi_val = float(rsi_series.iloc[-1])
        if not np.isnan(rsi_val):
            result["rsi"] = round(rsi_val, 1)

    # SMA50 near SMA200: within 5%
    s50 = result["sma50"]
    s200 = result["sma200"]
    if s50 is not None and s200 is not None and s200 != 0:
        result["sma50_near_sma200"] = abs(s50 - s200) / s200 < 0.05

    # Cross detection requires both SMAs
    if result["sma50"] is not None and result["sma200"] is not None:
        result["cross"] = detect_cross(sma50, sma200)

    return result
