"""Correlation matrix and historical VaR calculation."""
import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def fetch_returns(tickers: list[str], yahoo_client) -> pd.DataFrame:
    """Fetch 2-year daily close-to-close returns for a list of tickers.

    Args:
        tickers: List of ticker symbols.
        yahoo_client: YahooClient instance.

    Returns:
        DataFrame with tickers as columns and date as index.
        Columns with insufficient data are dropped.
    """
    frames: dict[str, pd.Series] = {}
    for ticker in tickers:
        hist = yahoo_client.get_history(ticker, period="2y")
        if hist.empty or "Close" not in hist.columns:
            logger.warning("No history for %s, skipping", ticker)
            continue
        prices = hist["Close"].dropna()
        if len(prices) < 5:
            continue
        frames[ticker] = prices.pct_change().dropna()

    if not frames:
        return pd.DataFrame()

    df = pd.DataFrame(frames)
    # Keep only rows where all tickers have data
    return df.dropna()


def calculate_correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Compute Pearson correlation matrix.

    Args:
        returns: Daily returns DataFrame (tickers as columns).

    Returns:
        Correlation matrix DataFrame. Empty if input has < 2 columns.
    """
    if returns.empty or returns.shape[1] < 2:
        return pd.DataFrame()
    return returns.corr()


def calculate_var(
    returns: pd.DataFrame,
    weights: Optional[list[float]] = None,
    confidence: float = 0.95,
) -> float:
    """Historical simulation Value at Risk for a portfolio.

    Args:
        returns: Daily returns DataFrame (tickers as columns).
        weights: Portfolio weights. Equal-weighted if None.
        confidence: Confidence level (e.g. 0.95 for 95% VaR).

    Returns:
        VaR as a negative decimal (e.g. -0.125 means -12.5% loss).
        Returns 0.0 if insufficient data.
    """
    if returns.empty:
        return 0.0

    n = returns.shape[1]
    if weights is None:
        w = np.array([1.0 / n] * n)
    else:
        arr = np.array(weights, dtype=float)
        total = arr.sum()
        w = arr / total if total > 0 else np.array([1.0 / n] * n)

    # Align weights to columns
    w = w[:n]
    if len(w) < n:
        w = np.append(w, [1.0 / n] * (n - len(w)))

    portfolio_returns = returns.values @ w
    var = float(np.percentile(portfolio_returns, (1 - confidence) * 100))
    return round(var, 4)


def top_correlated_pair(corr_matrix: pd.DataFrame) -> str:
    """Find the most correlated ticker pair (excluding self-correlation).

    Args:
        corr_matrix: Correlation matrix from calculate_correlation_matrix().

    Returns:
        Human-readable string describing the highest-correlated pair.
        Empty string if fewer than 2 tickers.
    """
    if corr_matrix.empty or corr_matrix.shape[0] < 2:
        return ""
    tickers = corr_matrix.columns.tolist()
    best = ("", "", -999.0)
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            val = corr_matrix.iloc[i, j]
            if val > best[2]:
                best = (tickers[i], tickers[j], val)
    if best[2] == -999.0:
        return ""
    return f"{best[0]} と {best[1]} の相関が最も高い (r = {best[2]:.2f})"
