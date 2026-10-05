"""Sectors from SEC's industry code (SIC) through a fixed table (roadmap section 3, "Sector list"; decision 2026-10-04),
the cyclical industries (agent 3's type rules) and the out-of-scope labels (agent 3, approach 2; decision 2026-10-05).

Until the Eye's tag mapping exists (phase 4) the sector comes from this table. A wrong sector is corrected in
`settings.yaml` → `sector_overrides` (ticker: sector). Shared because agent 2 uses the sector too.
"""

from __future__ import annotations

from shared import config

GICS = ("Energy", "Materials", "Industrials", "Consumer Discretionary", "Consumer Staples", "Health Care", "Financials",
        "Information Technology", "Communication Services", "Utilities", "Real Estate")

# (first SIC, last SIC, sector) — the first range that holds the code wins, so narrow ranges come before wide ones.
SIC_TABLE: list[tuple[int, int, str]] = [
    (1311, 1389, "Energy"), (1220, 1241, "Energy"), (2900, 2999, "Energy"), (4922, 4922, "Energy"),
    (1000, 1499, "Materials"), (2400, 2499, "Materials"), (2600, 2699, "Materials"), (2800, 2829, "Materials"),
    (2850, 2899, "Materials"), (3011, 3011, "Consumer Discretionary"), (3021, 3021, "Consumer Discretionary"),
    (3000, 3099, "Materials"),
    (3200, 3399, "Materials"),
    (2830, 2836, "Health Care"), (3841, 3851, "Health Care"), (5122, 5122, "Health Care"), (8000, 8099, "Health Care"),
    (2840, 2844, "Consumer Staples"), (100, 999, "Consumer Staples"), (2000, 2199, "Consumer Staples"),
    (5400, 5499, "Consumer Staples"), (5140, 5149, "Consumer Staples"), (5912, 5912, "Consumer Staples"),
    (5331, 5331, "Consumer Staples"), (5399, 5399, "Consumer Staples"),
    (3570, 3579, "Information Technology"), (3600, 3629, "Information Technology"),
    (3630, 3639, "Consumer Discretionary"), (3650, 3652, "Consumer Discretionary"), (3640, 3699, "Information Technology"),
    (3812, 3812, "Industrials"), (3800, 3839, "Information Technology"), (7370, 7379, "Information Technology"),
    (3711, 3716, "Consumer Discretionary"), (3751, 3751, "Consumer Discretionary"), (2200, 2399, "Consumer Discretionary"),
    (2500, 2599, "Consumer Discretionary"), (3100, 3199, "Consumer Discretionary"),
    (3900, 3999, "Consumer Discretionary"), (1520, 1531, "Consumer Discretionary"), (5200, 5999, "Consumer Discretionary"),
    (7000, 7099, "Consumer Discretionary"), (7900, 7999, "Consumer Discretionary"), (8200, 8299, "Consumer Discretionary"),
    (2700, 2799, "Communication Services"), (4800, 4899, "Communication Services"), (7310, 7319, "Communication Services"),
    (7810, 7829, "Communication Services"),
    (4950, 4959, "Industrials"), (4900, 4999, "Utilities"),
    (6500, 6553, "Real Estate"), (6798, 6798, "Real Estate"), (6000, 6799, "Financials"),
    (1500, 1799, "Industrials"), (3400, 3599, "Industrials"), (3700, 3799, "Industrials"), (4000, 4799, "Industrials"),
    (5000, 5199, "Industrials"), (7300, 7399, "Industrials"), (8700, 8799, "Industrials"),
]

# Agent 3, type rule 1: semiconductors, autos, airlines, shipping, homebuilding, chemicals (drugs 2830–2836 and soaps /
# cosmetics 2840–2844 not included), steel, mining.
CYCLICAL_SIC = [(3674, 3674), (3711, 3716), (4512, 4522), (4400, 4499), (1520, 1531), (2800, 2829), (2850, 2899),
                (3310, 3329), (1000, 1499)]

# Agent 3, approach 2 (decision 2026-10-05). `pre_revenue` is decided from the figures, not from the code.
OUT_OF_SCOPE_SIC: list[tuple[int, int, str]] = [
    (6021, 6036, "bank"), (6311, 6399, "insurance"), (6798, 6798, "reit"),
    (4911, 4911, "utility"), (4923, 4924, "utility"), (4931, 4932, "utility"), (4941, 4941, "utility"),
    (4991, 4991, "utility"),
]


def sector_for(sic: int | None, ticker: str | None = None) -> str:
    overrides = config.settings().get("sector_overrides") or {}
    if ticker and ticker.upper() in overrides:
        return overrides[ticker.upper()]
    if sic is None:
        return "other"
    for lo, hi, sector in SIC_TABLE:
        if lo <= sic <= hi:
            return sector
    return "other"


def is_cyclical_sic(sic: int | None) -> bool:
    return sic is not None and any(lo <= sic <= hi for lo, hi in CYCLICAL_SIC)


def out_of_scope_for(sic: int | None) -> str | None:
    if sic is None:
        return None
    for lo, hi, label in OUT_OF_SCOPE_SIC:
        if lo <= sic <= hi:
            return label
    return None
