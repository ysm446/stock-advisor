"""Formatting utilities for Markdown tables and display strings."""
from typing import Optional

# ---------------------------------------------------------------------------
# Sector / Industry localization (Yahoo Finance English → Japanese)
# ---------------------------------------------------------------------------

_SECTOR_JA: dict[str, str] = {
    "Technology": "テクノロジー",
    "Financial Services": "金融サービス",
    "Healthcare": "ヘルスケア",
    "Consumer Cyclical": "一般消費財・サービス",
    "Consumer Defensive": "生活必需品",
    "Communication Services": "コミュニケーション・サービス",
    "Industrials": "資本財・サービス",
    "Basic Materials": "素材",
    "Energy": "エネルギー",
    "Real Estate": "不動産",
    "Utilities": "公益事業",
}

_INDUSTRY_JA: dict[str, str] = {
    # Technology
    "Semiconductors": "半導体",
    "Semiconductor Equipment & Materials": "半導体製造装置・材料",
    "Consumer Electronics": "家電",
    "Electronic Components": "電子部品",
    "Electronic Gaming & Multimedia": "電子ゲーム・マルチメディア",
    "Electronics & Computer Distribution": "電子機器・コンピュータ流通",
    "Information Technology Services": "ITサービス",
    "Software - Application": "ソフトウェア（応用）",
    "Software - Infrastructure": "ソフトウェア（インフラ）",
    "Computer Hardware": "コンピュータハードウェア",
    "Communication Equipment": "通信機器",
    "Scientific & Technical Instruments": "科学・技術機器",
    "Solar": "太陽光発電",
    # Financial Services
    "Banks - Regional": "地方銀行",
    "Banks - Diversified": "総合銀行",
    "Banks - Global": "グローバル銀行",
    "Asset Management": "資産運用",
    "Insurance - Life": "生命保険",
    "Insurance - Property & Casualty": "損害保険",
    "Insurance - Diversified": "総合保険",
    "Insurance - Specialty": "特殊保険",
    "Insurance - Reinsurance": "再保険",
    "Capital Markets": "資本市場",
    "Financial Conglomerates": "総合金融",
    "Credit Services": "クレジット・消費者金融",
    "Mortgage Finance": "住宅ローン",
    # Healthcare
    "Drug Manufacturers - General": "医薬品（大手）",
    "Drug Manufacturers - Specialty & Generic": "医薬品（特殊・ジェネリック）",
    "Biotechnology": "バイオテクノロジー",
    "Medical Devices": "医療機器",
    "Medical Instruments & Supplies": "医療用品・器具",
    "Diagnostics & Research": "診断・研究",
    "Healthcare Plans": "医療保険・サービス",
    "Medical Care Facilities": "医療施設",
    "Pharmaceutical Retailers": "調剤薬局",
    "Health Information Services": "ヘルスケア情報サービス",
    # Consumer Cyclical
    "Automobiles": "自動車",
    "Auto Parts": "自動車部品",
    "Auto & Truck Dealerships": "自動車販売",
    "Auto Manufacturers": "自動車メーカー",
    "Apparel Manufacturing": "アパレル製造",
    "Apparel Retail": "アパレル小売",
    "Department Stores": "百貨店",
    "Specialty Retail": "専門小売",
    "Home Improvement Retail": "ホームセンター",
    "Luxury Goods": "高級品",
    "Residential Construction": "住宅建設",
    "Lodging": "宿泊業",
    "Restaurants": "外食",
    "Gambling": "ギャンブル",
    "Leisure": "レジャー",
    "Personal Services": "個人サービス",
    "Recreational Vehicles": "レジャー車両",
    "Travel Services": "旅行サービス",
    "Internet Retail": "ネット通販",
    # Consumer Defensive
    "Beverages - Non-Alcoholic": "飲料（非アルコール）",
    "Beverages - Alcoholic": "飲料（アルコール）",
    "Beverages - Brewers": "ビール・醸造",
    "Beverages - Wineries & Distilleries": "ワイン・蒸留酒",
    "Confectioners": "菓子・製菓",
    "Packaged Foods": "加工食品",
    "Farm Products": "農産物",
    "Grocery Stores": "食料品スーパー",
    "Food Distribution": "食品流通",
    "Discount Stores": "ディスカウントストア",
    "Household & Personal Products": "家庭用品・日用品",
    "Tobacco": "タバコ",
    # Communication Services
    "Telecom Services": "通信サービス",
    "Internet Content & Information": "インターネット・コンテンツ",
    "Broadcasting": "放送",
    "Entertainment": "エンターテインメント",
    "Publishing": "出版",
    "Advertising Agencies": "広告代理店",
    # Industrials
    "Aerospace & Defense": "航空宇宙・防衛",
    "Airlines": "航空",
    "Airports & Air Services": "空港・航空サービス",
    "Building Products & Equipment": "建材・設備",
    "Business Equipment & Supplies": "事務機器・備品",
    "Conglomerates": "コングロマリット",
    "Consulting Services": "コンサルティング",
    "Electrical Equipment & Parts": "電気機器・部品",
    "Engineering & Construction": "建設・土木",
    "Farm & Heavy Construction Machinery": "農業・建設機械",
    "Industrial Distribution": "産業流通",
    "Infrastructure Operations": "インフラ運営",
    "Integrated Freight & Logistics": "総合物流",
    "Marine Shipping": "海運",
    "Metal Fabrication": "金属加工",
    "Pollution & Treatment Controls": "環境・廃棄物処理",
    "Railroads": "鉄道",
    "Rental & Leasing Services": "レンタル・リース",
    "Security & Protection Services": "セキュリティ・警備",
    "Specialty Business Services": "専門ビジネスサービス",
    "Specialty Industrial Machinery": "産業機械（特殊）",
    "Staffing & Employment Services": "人材サービス",
    "Tools & Accessories": "工具・アクセサリー",
    "Trucking": "トラック輸送",
    "Waste Management": "廃棄物管理",
    # Basic Materials
    "Aluminum": "アルミニウム",
    "Building Materials": "建設資材",
    "Chemicals": "化学",
    "Specialty Chemicals": "特殊化学品",
    "Agricultural Inputs": "農業資材",
    "Coking Coal": "コークス用炭",
    "Copper": "銅",
    "Gold": "金",
    "Lumber & Wood Production": "木材",
    "Other Industrial Metals & Mining": "その他鉱業",
    "Other Precious Metals & Mining": "その他貴金属鉱業",
    "Paper & Paper Products": "紙・紙製品",
    "Silver": "銀",
    "Steel": "鉄鋼",
    # Energy
    "Oil & Gas E&P": "石油・ガス（探鉱・開発）",
    "Oil & Gas Integrated": "石油・ガス（総合）",
    "Oil & Gas Midstream": "石油・ガス（中流）",
    "Oil & Gas Refining & Marketing": "石油・ガス（精製・販売）",
    "Oil & Gas Equipment & Services": "石油・ガス機器・サービス",
    "Thermal Coal": "一般炭",
    "Uranium": "ウラン",
    # Real Estate
    "Real Estate - Diversified": "不動産（総合）",
    "Real Estate - Development": "不動産開発",
    "Real Estate Services": "不動産サービス",
    "REIT - Diversified": "REIT（総合）",
    "REIT - Healthcare Facilities": "REIT（医療施設）",
    "REIT - Hotel & Motel": "REIT（ホテル）",
    "REIT - Industrial": "REIT（産業用）",
    "REIT - Mortgage": "REIT（モーゲージ）",
    "REIT - Office": "REIT（オフィス）",
    "REIT - Residential": "REIT（住宅）",
    "REIT - Retail": "REIT（商業）",
    "REIT - Specialty": "REIT（特殊）",
    # Utilities
    "Utilities - Diversified": "公益（総合）",
    "Utilities - Independent Power Producers": "独立系電力",
    "Utilities - Regulated Electric": "電力（規制）",
    "Utilities - Regulated Gas": "ガス（規制）",
    "Utilities - Regulated Water": "水道（規制）",
    "Utilities - Renewable": "再生可能エネルギー",
}


def localize_sector(name: Optional[str]) -> str:
    """Translate a Yahoo Finance sector name to Japanese.

    Returns the original name if no translation is available.
    """
    if not name:
        return "-"
    return _SECTOR_JA.get(name, name)


def localize_industry(name: Optional[str]) -> str:
    """Translate a Yahoo Finance industry name to Japanese.

    Returns the original name if no translation is available.
    """
    if not name:
        return "-"
    return _INDUSTRY_JA.get(name, name)


def fmt_pct(value: Optional[float], decimals: int = 1) -> str:
    """Format a decimal ratio as a percentage string (e.g. 0.035 → '3.5%')."""
    if value is None:
        return "-"
    return f"{value * 100:.{decimals}f}%"


def fmt_float(value: Optional[float], decimals: int = 1) -> str:
    """Format a float with fixed decimal places."""
    if value is None:
        return "-"
    return f"{value:.{decimals}f}"


def fmt_market_cap(cap: Optional[float], currency: Optional[str] = None) -> str:
    """Format a market cap value with currency-aware units."""
    if cap is None:
        return "-"
    if currency == "JPY":
        cho = int(cap // 1e12)
        oku = int((cap % 1e12) // 1e8)
        if cho > 0 and oku > 0:
            return f"¥{cho}兆{oku}億"
        if cho > 0:
            return f"¥{cho}兆"
        return f"¥{oku}億"
    if cap >= 1e12:
        return f"${cap / 1e12:.1f}T"
    if cap >= 1e9:
        return f"${cap / 1e9:.1f}B"
    return f"${cap / 1e6:.0f}M"


def fmt_price(price: Optional[float], currency: Optional[str] = None) -> str:
    """Format a price value."""
    if price is None:
        return "-"
    if currency == "JPY":
        return f"¥{price:,.0f}"
    return f"${price:,.2f}"


def markdown_table(headers: list[str], rows: list[list]) -> str:
    """Build a simple Markdown table.

    Args:
        headers: Column header strings.
        rows: List of row value lists (converted to str automatically).

    Returns:
        Markdown-formatted table string.
    """
    sep = " | ".join(["---"] * len(headers))
    header_row = " | ".join(headers)
    body_rows = "\n".join(
        " | ".join(str(cell) for cell in row) for row in rows
    )
    return f"| {header_row} |\n| {sep} |\n" + "\n".join(
        f"| {' | '.join(str(c) for c in row)} |" for row in rows
    )
