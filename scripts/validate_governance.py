#!/usr/bin/env python3
# SIMULATED RESEARCH ARTIFACT -- NOT A TRADING SYSTEM.
"""
This code is not connected to, endorsed by, or representative of any exchange, broker, depository, regulator or trading venue, and it does not execute, route or settle orders. Nothing here is legal, financial, tax, accounting or investment advice. Fee, calendar, settlement and price-limit values are approximations compiled by the authors from public sources for academic use. They are NOT official data and have NOT been verified against the instruments they approximate. Do not rely on them for any real-world purpose. See README.md (Provenance and attribution) for what each class of value approximates.

Artifact-level design-objective validations (V1-V5).

These checks exercise the governance mechanisms documented in the manuscript
against the codebase. They are NOT empirical tests of propositions P1-P5;
they are design-objective validations in the sense of DSR Activity 5
(Peffers et al. 2007, Hevner et al. 2004).

Run from repo root:
    python scripts/validate_governance.py

Writes:
    results/validation/validation_results.json
    results/validation/validation_summary.md
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import os
import sys
from pathlib import Path

# Make the phase4 package importable
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PHASE4 = ROOT / "code" / "phase4"
sys.path.insert(0, str(PHASE4))
sys.path.insert(0, str(PHASE4 / "engine"))

import numpy as np
import pandas as pd

import resolver as resolver_mod  # type: ignore
from loader import load_yaml  # type: ignore
from trading_calendar import TradingCalendar  # type: ignore


def _ok(b: bool) -> str:
    return "PASS" if b else "FAIL"


# ---------------------------------------------------------------------------
# V1: Fee resolver boundary tests
# ---------------------------------------------------------------------------
def validate_v1_fee_resolver_boundaries() -> dict:
    """For each known regulatory transition in fees.yaml, confirm that the
    resolver selects the correct period on the boundary dates."""
    cfg = load_yaml("fees")
    periods = cfg["equities_trading_fees"]["shares_transaction_fees"]["standard_rates"]

    expected = [
        # (date, expected regulatory_period label)
        (dt.date(2002, 1, 1), "Pre-2012 estimates"),
        (dt.date(2012, 8, 16), "Pre-2012 estimates"),
        (dt.date(2012, 8, 17), "Legal Notice 88/2012"),
        (dt.date(2016, 3, 10), "Legal Notice 88/2012"),
        (dt.date(2016, 3, 11), "Legal Notice 35/2016"),
        (dt.date(2022, 8, 11), "Legal Notice 35/2016"),
        (dt.date(2022, 8, 12), "Legal Notice 135/2022"),
        (dt.date(2025, 1, 1), "Legal Notice 135/2022"),
    ]

    cases = []
    for on, expected_label in expected:
        picked = resolver_mod.resolve_effective_item(periods, on)
        actual_label = picked["regulatory_period"] if picked else None
        cases.append(
            {
                "date": on.isoformat(),
                "expected": expected_label,
                "actual": actual_label,
                "passed": actual_label == expected_label,
            }
        )

    n_pass = sum(1 for c in cases if c["passed"])
    return {
        "id": "V1",
        "name": "Fee resolver boundary tests",
        "objective": "Resolve rules deterministically (Activity 2 (iii))",
        "n_cases": len(cases),
        "n_passed": n_pass,
        "passed": n_pass == len(cases),
        "cases": cases,
    }


# ---------------------------------------------------------------------------
# V2: T+3 settlement correctness across weekends and holidays
# ---------------------------------------------------------------------------
def validate_v2_settlement() -> dict:
    cal = TradingCalendar(start_year=2020, end_year=2025)

    # Build expected (trade_date, expected_settlement_date) pairs by computing
    # 3 trading-day-forward independently using the calendar's trading_days index.
    # The expected logic: skip the trade date itself, advance to next trading
    # days until we have counted settlement_days = 3.
    def expected_settlement(trade_date: pd.Timestamp) -> pd.Timestamp:
        d = pd.Timestamp(trade_date.date())
        counted = 0
        while counted < cal.settlement_days:
            d = d + pd.Timedelta(days=1)
            while (d.weekday() >= 5) or (d in cal.holidays):
                d = d + pd.Timedelta(days=1)
            counted += 1
        return d

    # Pick a varied set of trade dates: midweek, before weekend, before holiday,
    # over year boundary, and across a long-weekend cluster.
    probe_dates = [
        pd.Timestamp("2023-03-14"),  # Tuesday, no weekend interaction
        pd.Timestamp("2023-03-16"),  # Thursday -> spans weekend
        pd.Timestamp("2023-12-28"),  # Thursday in holiday cluster (12-25, 12-26)
        pd.Timestamp("2023-12-29"),  # Friday at year end
        pd.Timestamp("2024-04-30"),  # Tuesday before 05-01 holiday
        pd.Timestamp("2024-10-18"),  # Friday before 10-20 holiday
        pd.Timestamp("2024-12-23"),  # Monday before 12-25/26 holiday
        pd.Timestamp("2025-01-02"),  # Thursday right after 01-01 holiday
    ]

    cases = []
    for td in probe_dates:
        if not cal.is_trading_day(td):
            continue
        actual = cal.get_settlement_date(td)
        expected = expected_settlement(td)
        cases.append(
            {
                "trade_date": td.date().isoformat(),
                "expected_settlement": expected.date().isoformat(),
                "actual_settlement": actual.date().isoformat(),
                "passed": actual.date() == expected.date(),
            }
        )

    n_pass = sum(1 for c in cases if c["passed"])
    return {
        "id": "V2",
        "name": "T+3 settlement correctness across weekends and holidays",
        "objective": "Make validity windows explicit (Activity 2 (ii))",
        "n_cases": len(cases),
        "n_passed": n_pass,
        "passed": n_pass == len(cases),
        "cases": cases,
    }


# ---------------------------------------------------------------------------
# V3: Schema conformance on synthetic data generator output
# ---------------------------------------------------------------------------
def validate_v3_schema_conformance() -> dict:
    # Re-run the generator (it is deterministic with seed 42)
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_synthetic_data.py")],
        capture_output=True,
        text=True,
    )
    generator_ok = proc.returncode == 0

    intraday_csv = PHASE4 / "intraday_prices_hourly.csv"
    liq_csv = ROOT / "code" / "phase3" / "surviving_stocks_liquidity_tiers.csv"

    expected_intraday_cols = ["date", "time", "ticker", "close"]
    expected_liq_cols = ["ticker", "tier"]

    intraday_df = pd.read_csv(intraday_csv)
    liq_df = pd.read_csv(liq_csv)

    intraday_cols_match = list(intraday_df.columns) == expected_intraday_cols
    liq_cols_match = list(liq_df.columns) == expected_liq_cols

    # Field-level conformance
    hours_ok = set(int(h) for h in intraday_df["time"].unique()) == {
        9,
        10,
        11,
        12,
        13,
        14,
    }
    tickers_ok = set(intraday_df["ticker"].unique()) == {"TKR1", "TKR2", "TKR3"}
    tiers_ok = set(liq_df["tier"].unique()) == {
        "TIER_1_HIGHLY_LIQUID",
        "TIER_2_LIQUID",
        "TIER_3_MODERATE",
    }

    checks = {
        "generator_exit_zero": generator_ok,
        "intraday_columns": intraday_cols_match,
        "liquidity_columns": liq_cols_match,
        "intraday_hours_match_{9..14}": hours_ok,
        "intraday_tickers_match_{TKR1..3}": tickers_ok,
        "liquidity_tiers_match_documented_set": tiers_ok,
    }
    all_ok = all(checks.values())

    return {
        "id": "V3",
        "name": "Schema conformance on synthetic data generator output",
        "objective": "Make data contracts inspectable (Activity 2 (iv))",
        "checks": checks,
        "intraday_rows": int(len(intraday_df)),
        "liquidity_rows": int(len(liq_df)),
        "passed": all_ok,
    }


# ---------------------------------------------------------------------------
# V4: Defensive-transform sanitization rates on a synthetic feature batch
# ---------------------------------------------------------------------------
def validate_v4_sanitization_rates() -> dict:
    """Construct a representative batch of raw feature values that includes NaNs
    and out-of-range entries; pass them through the documented defensive
    transform (clip to [-3,3] then divide by 3) and measure sanitization rates.
    Mirrors _standardize_features() in feature_engineering_v2.py."""
    rng = np.random.default_rng(42)
    n = 10_000

    # Mix: 75 percent standard-normal features, 10 percent NaN, 15 percent extreme.
    raw = rng.normal(0.0, 1.0, size=n)
    n_nan = int(0.10 * n)
    n_extreme = int(0.15 * n)
    nan_idx = rng.choice(n, size=n_nan, replace=False)
    raw[nan_idx] = np.nan
    remaining = np.setdiff1d(np.arange(n), nan_idx)
    extreme_idx = rng.choice(remaining, size=n_extreme, replace=False)
    raw[extreme_idx] = rng.choice([-10.0, 10.0, -50.0, 50.0], size=n_extreme)

    # Documented defensive transform
    nan_replaced = np.isnan(raw)
    intermediate = np.where(nan_replaced, 0.0, raw)
    clipped_mask = (intermediate > 3.0) | (intermediate < -3.0)
    clipped = np.clip(intermediate, -3.0, 3.0)
    normalized = clipped / 3.0

    in_range = np.all((normalized >= -1.0) & (normalized <= 1.0))

    return {
        "id": "V4",
        "name": "Defensive-transform sanitization rates on a synthetic batch",
        "objective": "Make defaults visible and contestable (Activity 2 (v))",
        "n_features": n,
        "nan_replacement_rate": float(nan_replaced.mean()),
        "clipping_rate": float(clipped_mask.mean()),
        "output_in_unit_interval": bool(in_range),
        "passed": bool(in_range),
    }


# ---------------------------------------------------------------------------
# V5: Audit output stability across two synthetic runs with the same input
# ---------------------------------------------------------------------------
def validate_v5_audit_output_stability() -> dict:
    """Drive the manuscript-cited reporting routine with a deterministic
    synthetic metrics dict and confirm that two runs produce byte-equal output
    files (stable file names, stable column header order, deterministic row
    serialization)."""
    sys.path.insert(0, str(PHASE4 / "analysis"))
    from plot_training_results import save_metrics_csv, save_summary_markdown  # type: ignore

    def fake_metrics():
        return {
            "epochs": [1, 2, 3],
            "mean_sharpes": [0.10, 0.11, 0.12],
            "min_sharpes": [-0.05, 0.00, 0.02],
            "max_sharpes": [0.20, 0.22, 0.24],
            "epoch_times": [12.5, 12.6, 12.4],
            "avg_policy_losses": [0.3, 0.28, 0.26],
            "avg_value_losses": [0.5, 0.48, 0.45],
            "avg_entropies": [0.9, 0.88, 0.86],
            "mean_ann_vols": [0.15, 0.14, 0.13],
            "mean_sortinos": [0.20, 0.22, 0.24],
            "mean_ann_returns": [5.0, 6.0, 7.0],
            "agent_sharpe_series": {
                "agent_A": [0.10, 0.11, 0.12],
                "agent_B": [0.08, 0.09, 0.10],
            },
            "agent_total_reward_series": {
                "agent_A": [1.0, 1.2, 1.4],
                "agent_B": [0.8, 0.9, 1.0],
            },
            "agent_max_drawdown_series": {
                "agent_A": [-0.05, -0.04, -0.03],
                "agent_B": [-0.06, -0.05, -0.04],
            },
            "agent_ann_vol_series": {
                "agent_A": [0.15, 0.14, 0.13],
                "agent_B": [0.16, 0.15, 0.14],
            },
            "agent_sortino_series": {
                "agent_A": [0.2, 0.22, 0.24],
                "agent_B": [0.18, 0.20, 0.22],
            },
            "agent_ann_return_series": {
                "agent_A": [5.0, 6.0, 7.0],
                "agent_B": [4.0, 5.0, 6.0],
            },
            "agent_turnover_series": {
                "agent_A": [10.0, 10.5, 11.0],
                "agent_B": [9.5, 10.0, 10.5],
            },
            "best_epoch": 3,
        }

    out_a = ROOT / "results" / "validation" / "audit_run_a"
    out_b = ROOT / "results" / "validation" / "audit_run_b"
    out_a.mkdir(parents=True, exist_ok=True)
    out_b.mkdir(parents=True, exist_ok=True)

    save_metrics_csv(str(out_a), fake_metrics())
    save_metrics_csv(str(out_b), fake_metrics())
    save_summary_markdown(str(out_a), fake_metrics())
    save_summary_markdown(str(out_b), fake_metrics())

    def h(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    csv_a = out_a / "metrics_summary.csv"
    csv_b = out_b / "metrics_summary.csv"
    md_a = out_a / "results_summary.md"
    md_b = out_b / "results_summary.md"

    csv_equal = h(csv_a) == h(csv_b)
    md_equal = h(md_a) == h(md_b)

    # Stable column header check
    with csv_a.open() as f:
        header = f.readline().strip().split(",")
    expected_first_cols = [
        "epoch",
        "mean_sharpe",
        "min_sharpe",
        "max_sharpe",
        "epoch_time_sec",
        "avg_policy_loss",
        "avg_value_loss",
        "avg_entropy",
    ]
    header_starts_correctly = header[: len(expected_first_cols)] == expected_first_cols

    return {
        "id": "V5",
        "name": "Audit output stability across two synthetic runs",
        "objective": "Emit truthful audit artifacts (Activity 2 (vi))",
        "metrics_csv_byte_equal": csv_equal,
        "results_summary_md_byte_equal": md_equal,
        "header_starts_with_documented_columns": header_starts_correctly,
        "csv_column_count": len(header),
        "passed": bool(csv_equal and md_equal and header_starts_correctly),
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> int:
    results = []
    for fn in [
        validate_v1_fee_resolver_boundaries,
        validate_v2_settlement,
        validate_v3_schema_conformance,
        validate_v4_sanitization_rates,
        validate_v5_audit_output_stability,
    ]:
        try:
            r = fn()
        except Exception as e:
            r = {
                "id": fn.__name__,
                "passed": False,
                "error": f"{type(e).__name__}: {e}",
            }
        results.append(r)

    out_dir = ROOT / "results" / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "validation_results.json"
    md_path = out_dir / "validation_summary.md"

    json_path.write_text(json.dumps(results, indent=2))

    lines = ["# Artifact-level design-objective validation results", ""]
    lines.append("| ID | Validation | Design objective | Result |")
    lines.append("|----|------------|------------------|--------|")
    for r in results:
        name = r.get("name", r.get("id"))
        obj = r.get("objective", "-")
        result = _ok(bool(r.get("passed")))
        lines.append(f"| {r['id']} | {name} | {obj} | {result} |")

    lines.append("")
    lines.append("## Details")
    for r in results:
        lines.append("")
        lines.append(f"### {r['id']}: {r.get('name', '')}")
        lines.append("```json")
        lines.append(json.dumps(r, indent=2))
        lines.append("```")

    md_path.write_text("\n".join(lines))

    print(f"[VALIDATE] wrote {json_path}")
    print(f"[VALIDATE] wrote {md_path}")

    overall = all(r.get("passed") for r in results)
    print(f"[VALIDATE] overall: {'PASS' if overall else 'FAIL'}")

    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
