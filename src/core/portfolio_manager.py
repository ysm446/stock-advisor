"""Portfolio management: trade records, snapshot, and structure analysis."""
import csv
import logging
import os
from datetime import date
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

_CSV_COLUMNS = ["date", "action", "ticker", "quantity", "price", "currency", "notes"]


class PortfolioManager:
    """Manage portfolio trades stored in a CSV file."""

    def __init__(self, csv_path: str = "data/portfolio.csv") -> None:
        """
        Args:
            csv_path: Path to the portfolio CSV file.
        """
        self.csv_path = csv_path
        self._ensure_csv()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_csv(self) -> None:
        """Create the CSV with headers if it does not exist."""
        os.makedirs(os.path.dirname(self.csv_path) or ".", exist_ok=True)
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=_CSV_COLUMNS)
                writer.writeheader()

    # ------------------------------------------------------------------
    # Trade recording
    # ------------------------------------------------------------------

    def add_trade(
        self,
        action: str,
        ticker: str,
        quantity: float,
        price: float,
        currency: str,
        notes: str = "",
    ) -> None:
        """Append a buy or sell trade to the CSV.

        Args:
            action: "buy" or "sell".
            ticker: Ticker symbol.
            quantity: Number of shares/units.
            price: Price per share/unit.
            currency: ISO 4217 currency code (e.g. "JPY", "USD").
            notes: Optional free-text note.
        """
        action = action.lower()
        if action not in ("buy", "sell"):
            raise ValueError(f"action must be 'buy' or 'sell', got '{action}'")
        row = {
            "date": date.today().isoformat(),
            "action": action,
            "ticker": ticker.upper(),
            "quantity": quantity,
            "price": price,
            "currency": currency.upper(),
            "notes": notes,
        }
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_CSV_COLUMNS)
            writer.writerow(row)

    def get_trades(self) -> pd.DataFrame:
        """Return all trade records as a DataFrame.

        Returns:
            DataFrame with columns matching _CSV_COLUMNS, or empty DataFrame.
        """
        try:
            df = pd.read_csv(self.csv_path, encoding="utf-8")
            if df.empty:
                return pd.DataFrame(columns=_CSV_COLUMNS)
            df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            return df
        except Exception as e:
            logger.warning("get_trades failed: %s", e)
            return pd.DataFrame(columns=_CSV_COLUMNS)

    # ------------------------------------------------------------------
    # Position aggregation
    # ------------------------------------------------------------------

    def get_positions(self) -> dict[str, dict]:
        """Aggregate current positions from trade history.

        Returns:
            Dict mapping ticker → {quantity, avg_price, currency}.
            Tickers with zero or negative quantity are excluded.
        """
        df = self.get_trades()
        if df.empty:
            return {}

        positions: dict[str, dict] = {}
        for _, row in df.iterrows():
            ticker = str(row["ticker"])
            qty = float(row["quantity"])
            price = float(row["price"])
            currency = str(row["currency"])
            action = str(row["action"]).lower()

            if ticker not in positions:
                positions[ticker] = {"quantity": 0.0, "cost_total": 0.0, "currency": currency}

            if action == "buy":
                positions[ticker]["quantity"] += qty
                positions[ticker]["cost_total"] += qty * price
            elif action == "sell":
                positions[ticker]["quantity"] -= qty
                # Reduce cost proportionally
                if positions[ticker]["quantity"] + qty > 0:
                    ratio = qty / (positions[ticker]["quantity"] + qty)
                    positions[ticker]["cost_total"] *= (1 - ratio)

        result = {}
        for ticker, pos in positions.items():
            if pos["quantity"] > 0:
                result[ticker] = {
                    "quantity": pos["quantity"],
                    "avg_price": pos["cost_total"] / pos["quantity"],
                    "currency": pos["currency"],
                }
        return result

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def get_snapshot(self, yahoo_client) -> list[dict]:
        """Fetch current prices and compute unrealised P&L for each position.

        Args:
            yahoo_client: YahooClient instance.

        Returns:
            List of dicts per position:
              {ticker, name, quantity, avg_price, current_price,
               currency, market_value, cost, gain, gain_pct}
            current_price / market_value / gain are None if price fetch fails.
        """
        positions = self.get_positions()
        snapshot = []
        for ticker, pos in positions.items():
            info = yahoo_client.get_ticker_info(ticker)
            current_price: Optional[float] = (
                info.get("currentPrice") or info.get("regularMarketPrice")
            )
            name = info.get("longName") or info.get("shortName") or ticker
            qty = pos["quantity"]
            avg = pos["avg_price"]
            currency = pos["currency"]
            cost = qty * avg
            market_value = qty * current_price if current_price is not None else None
            gain = (market_value - cost) if market_value is not None else None
            gain_pct = (gain / cost) if (gain is not None and cost > 0) else None

            snapshot.append({
                "ticker": ticker,
                "name": name,
                "quantity": qty,
                "avg_price": avg,
                "current_price": current_price,
                "currency": currency,
                "market_value": market_value,
                "cost": cost,
                "gain": gain,
                "gain_pct": gain_pct,
            })
        return snapshot

    # ------------------------------------------------------------------
    # Structure analysis
    # ------------------------------------------------------------------

    def get_structure(self, yahoo_client) -> dict:
        """Compute HHI concentration and sector allocation.

        Args:
            yahoo_client: YahooClient instance.

        Returns:
            {
                "hhi": float,               # 0–1 Herfindahl-Hirschman Index
                "sectors": {sector: pct},   # Sector allocation (%)
                "tickers": [ticker, ...],
            }
        """
        snapshot = self.get_snapshot(yahoo_client)
        if not snapshot:
            return {"hhi": 0.0, "sectors": {}, "tickers": []}

        # Use market_value for weights; fall back to cost if price unavailable
        weights: list[float] = []
        sector_values: dict[str, float] = {}
        tickers = []

        for item in snapshot:
            val = item["market_value"] if item["market_value"] is not None else item["cost"]
            weights.append(val)
            tickers.append(item["ticker"])
            info = yahoo_client.get_ticker_info(item["ticker"])
            sector = info.get("sector") or "不明"
            sector_values[sector] = sector_values.get(sector, 0.0) + val

        total = sum(weights)
        if total <= 0:
            return {"hhi": 0.0, "sectors": {}, "tickers": tickers}

        # HHI: sum of squared weight ratios
        hhi = sum((w / total) ** 2 for w in weights)

        sectors = {s: round(v / total * 100, 1) for s, v in sorted(
            sector_values.items(), key=lambda x: x[1], reverse=True
        )}

        return {"hhi": round(hhi, 4), "sectors": sectors, "tickers": tickers}
