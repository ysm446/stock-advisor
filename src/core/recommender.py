"""Generate recommended actions from stress test analysis results."""


def generate_recommendations(analysis: dict) -> list[str]:
    """Produce a list of actionable recommendations from a scenario analysis result.

    Rules (applied in order, multiple may trigger):
      - HHI > 0.25          → 集中度が高い → 分散を検討
      - portfolio < -25%    → 大規模下落リスク → ヘッジ/縮小を検討
      - VaR 95% < -15%      → 高ボラティリティ → ポジションサイズ見直し
      - 単一銘柄 < -40%     → 個別インパクト大 → リバランスを検討
      - 問題なし             → 主要リスクシグナルなし

    Args:
        analysis: Result dict from scenario_analysis.run_scenario().

    Returns:
        List of recommendation strings.
    """
    recs: list[str] = []

    hhi = analysis.get("hhi", 0.0)
    portfolio_impact = analysis.get("portfolio_impact", 0.0)
    var_95 = analysis.get("var_95", 0.0)
    ticker_impacts: list[dict] = analysis.get("ticker_impacts", [])

    if hhi > 0.25:
        recs.append(
            f"集中度が高い (HHI = {hhi:.2f})。"
            "上位銘柄のウェイト削減または新規銘柄の追加による分散を検討してください。"
        )

    if portfolio_impact < -0.25:
        recs.append(
            f"このシナリオでは推定 {portfolio_impact * 100:.1f}% の下落が見込まれます。"
            "ヘッジ手段 (金ETF・債券ETFの組み入れ等) またはポジション縮小を検討してください。"
        )

    if var_95 < -0.15:
        recs.append(
            f"95% VaR が {var_95 * 100:.1f}% と高水準です。"
            "ポートフォリオ全体のポジションサイズの見直しを推奨します。"
        )

    for item in ticker_impacts:
        if item["impact_pct"] < -0.40:
            recs.append(
                f"{item['name']} ({item['ticker']}): "
                f"シナリオ下での推定インパクトが {item['impact_pct'] * 100:.1f}% と大きい。"
                "リバランスまたはリスク低減を検討してください。"
            )

    if not recs:
        recs.append(
            "現時点でこのシナリオにおける主要なリスクシグナルは検出されていません。"
            "引き続き定期的なモニタリングを継続してください。"
        )

    return recs
