"""Herfindahl-Hirschman Index (HHI) concentration analysis."""


def calculate_hhi(weights: list[float]) -> float:
    """Calculate the Herfindahl-Hirschman Index from a list of weights.

    Weights can be raw amounts (e.g. market values) or ratios — they are
    normalised internally before squaring.

    Args:
        weights: Non-negative numeric weights (market values, quantities, etc.).

    Returns:
        HHI value in [0, 1].  Returns 0.0 for empty or all-zero input.
    """
    if not weights:
        return 0.0
    total = sum(weights)
    if total <= 0:
        return 0.0
    return sum((w / total) ** 2 for w in weights if w > 0)


def classify_hhi(hhi: float) -> str:
    """Return a Japanese label for an HHI value.

    Args:
        hhi: HHI value in [0, 1].

    Returns:
        "低集中 (分散良好)" | "中集中" | "高集中 (要注意)"
    """
    if hhi < 0.15:
        return "低集中 (分散良好)"
    if hhi < 0.25:
        return "中集中"
    return "高集中 (要注意)"
