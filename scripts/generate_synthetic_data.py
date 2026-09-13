# SIMULATED RESEARCH ARTIFACT -- NOT A TRADING SYSTEM.
"""
This code is not connected to, endorsed by, or representative of any exchange, broker, depository, regulator or trading venue, and it does not execute, route or settle orders. Nothing here is legal, financial, tax, accounting or investment advice. Fee, calendar, settlement and price-limit values are approximations compiled by the authors from public sources for academic use. They are NOT official data and have NOT been verified against the instruments they approximate. Do not rely on them for any real-world purpose. See README.md (Provenance and attribution) for what each class of value approximates.

Generate minimal synthetic CSVs for smoke testing only.

No real market data is included; this is purely synthetic.
"""

from pathlib import Path
import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PHASE4 = ROOT / "code" / "phase4"
PHASE3 = ROOT / "code" / "phase3"

PHASE4.mkdir(parents=True, exist_ok=True)
PHASE3.mkdir(parents=True, exist_ok=True)

np.random.seed(42)

# Synthetic tickers and dates
TICKERS = ["TKR1", "TKR2", "TKR3"]
DATES = pd.bdate_range("2020-01-02", periods=30)  # 30 business days
HOURS = [9, 10, 11, 12, 13, 14]  # hourly bars

rows = []
for d in DATES:
    # simple random-walk base per ticker
    base = {
        t: 100.0 + np.cumsum(np.random.normal(0, 0.2, size=len(HOURS)))[-1]
        for t in TICKERS
    }
    # intra-day profile per hour
    for h in HOURS:
        for t in TICKERS:
            # small intraday jitter
            price = base[t] + np.random.normal(0, 0.1)
            rows.append(
                {
                    "date": d.date(),
                    "time": h,
                    "ticker": t,
                    "close": round(float(price), 4),
                }
            )

intraday = pd.DataFrame(rows)

# Ensure at least one row per (date,time,ticker)
assert not intraday.empty

# Liquidity tiers
liq = pd.DataFrame(
    {
        "ticker": TICKERS,
        "tier": ["TIER_1_HIGHLY_LIQUID", "TIER_2_LIQUID", "TIER_3_MODERATE"],
    }
)

# Write CSVs
phase4_csv = PHASE4 / "intraday_prices_hourly.csv"
phase3_csv = PHASE3 / "surviving_stocks_liquidity_tiers.csv"

intraday.to_csv(phase4_csv, index=False)
liq.to_csv(phase3_csv, index=False)

print(f"[OK] Wrote synthetic intraday: {phase4_csv}")
print(f"[OK] Wrote synthetic liquidity tiers: {phase3_csv}")
print(
    "Note: Synthetic data is for smoke tests only and does not represent real markets."
)
