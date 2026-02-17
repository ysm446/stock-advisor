"""Portfolio health check: 3-level alert system."""
import logging

from src.core.technicals import get_technical_signals

logger = logging.getLogger(__name__)

# Alert level labels
_LEVEL_LABELS = {
    "ok": "✅ 正常",
    "watch": "👀 早期警告",
    "caution": "⚠️ 注意",
    "exit": "🔴 撤退検討",
}

_LEVEL_ACTIONS = {
    "ok": "現状維持。定期的にモニタリングを続けてください。",
    "watch": "注視が必要です。テクニカル指標が悪化しています。",
    "caution": "一部利確を検討してください。テクニカル・ファンダメンタル両面で警戒サインが出ています。",
    "exit": "撤退を検討してください。テクニカル崩壊とファンダメンタル悪化が同時発生しています。",
}


def _check_fundamental_deterioration(info: dict) -> int:
    """Count how many fundamental indicators have deteriorated.

    Deterioration criteria (rough heuristics using available data):
      - ROE < 5% (low profitability)
      - Revenue growth < 0% (declining revenue)
      - Operating margin < 0% (operating loss)

    Returns:
        Number of deteriorated indicators (0–3).
    """
    count = 0
    roe = info.get("returnOnEquity")
    if roe is not None and roe < 0.05:
        count += 1
    rev_growth = info.get("revenueGrowth")
    if rev_growth is not None and rev_growth < 0:
        count += 1
    op_margin = info.get("operatingMargins")
    if op_margin is not None and op_margin < 0:
        count += 1
    return count


def check_health(ticker: str, yahoo_client) -> dict:
    """Run a 3-level health check for a ticker.

    Levels:
        ok      — No significant warning signals.
        watch   — Early warning: price below SMA50, or RSI < 30.
        caution — SMA50 approaching SMA200 + 1 fundamental indicator worsened.
        exit    — Dead cross + 2+ fundamental indicators worsened.
                  (ETF: dead cross alone triggers exit.)

    Args:
        ticker: Ticker symbol.
        yahoo_client: YahooClient instance.

    Returns:
        {
            "ticker": str,
            "name": str,
            "is_etf": bool,
            "level": "ok" | "watch" | "caution" | "exit",
            "level_label": str,
            "signals": list[str],
            "action": str,
            "technicals": dict,
        }
    """
    ticker = ticker.strip().upper()
    info = yahoo_client.get_ticker_info(ticker)
    name = info.get("longName") or info.get("shortName") or ticker
    is_etf = yahoo_client.is_etf(ticker)

    history = yahoo_client.get_history(ticker, period="2y")
    tech = get_technical_signals(history)

    signals: list[str] = []
    level = "ok"

    # --- Technical signals ---
    if tech["cross"] == "dead":
        signals.append("デッドクロス: SMA50 が SMA200 を下抜け")

    if not tech["above_sma50"] and tech["sma50"] is not None:
        signals.append(f"SMA50 割れ (現在値 {tech['current_price']:.1f} < SMA50 {tech['sma50']:.1f})")

    rsi = tech.get("rsi")
    if rsi is not None and rsi < 30:
        signals.append(f"RSI 過売り圏 (RSI = {rsi:.1f})")

    if tech["sma50_near_sma200"]:
        signals.append("SMA50 が SMA200 に接近中 (5%以内)")

    # --- Fundamental signals (equity only) ---
    funda_count = 0
    if not is_etf:
        funda_count = _check_fundamental_deterioration(info)
        if funda_count >= 2:
            signals.append(f"ファンダメンタル悪化: {funda_count}指標が警戒水準")
        elif funda_count == 1:
            signals.append("ファンダメンタル軽微悪化: 1指標が警戒水準")

    # --- Level determination ---
    dead_cross = tech["cross"] == "dead"

    if is_etf:
        # ETF: technical only
        if dead_cross:
            level = "exit"
        elif tech["sma50_near_sma200"]:
            level = "caution"
        elif not tech["above_sma50"] or (rsi is not None and rsi < 30):
            level = "watch"
    else:
        # Equity: both technical and fundamental required for exit
        if dead_cross and funda_count >= 2:
            level = "exit"
        elif tech["sma50_near_sma200"] and funda_count >= 1:
            level = "caution"
        elif not tech["above_sma50"] or (rsi is not None and rsi < 30):
            level = "watch"

    return {
        "ticker": ticker,
        "name": name,
        "is_etf": is_etf,
        "level": level,
        "level_label": _LEVEL_LABELS[level],
        "signals": signals,
        "action": _LEVEL_ACTIONS[level],
        "technicals": tech,
    }
