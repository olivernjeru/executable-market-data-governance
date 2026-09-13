# Verification report: manuscript claims against the artifact

This document maps every factual claim the manuscript makes about the artifact to the exact file
and line range that evidences it, so that the claims can be checked without trusting the paper's
prose. It is intended for editors and reviewers who wish to confirm the technical statements
independently.

Line numbers refer to the files as distributed in this package. All paths are relative to the
package root.

Status values: `VERIFIED` (claim matches the code exactly), `VERIFIED (refined)` (the claim is
true, and the manuscript wording was sharpened in the current revision to state it more precisely).

---

## 1. Effective-dated fee policy

| # | Manuscript claim | Evidence | Status |
| --- | --- | --- | --- |
| 1.1 | Fee configuration defines periods with `effective_from`, `effective_to` and a `regulatory_period` label | `code/phase4/config/market_data/fees.yaml:12-133` | VERIFIED |
| 1.2 | Encoded standard-rate periods span 2002-01-01/2012-08-16, 2012-08-17/2016-03-10, 2016-03-11/2022-08-11, 2022-08-12/open | `fees.yaml:13-15, 41-43, 72-74, 103-105` | VERIFIED |
| 1.3 | Brokerage maxima per period: 0.0178 / 0.0150, 0.0178 / 0.0150, 0.0176 / 0.0136, 0.0176 / 0.0136 (small / large trades, 100,000 KES threshold) | `fees.yaml:20, 24, 48, 52, 79, 83, 110, 114` | VERIFIED |
| 1.4 | The configuration header explicitly flags values as estimates/approximations for academic use | `fees.yaml:1-8` (per-file disclaimer header) | VERIFIED |
| 1.5 | `is_active` checks date bounds and excludes `status: projected` entries | `code/phase4/engine/resolver.py:22-42` | VERIFIED (refined) |
| 1.6 | `resolve_effective_item` selects the most recent active candidate by `effective_from` descending | `resolver.py:45-61` | VERIFIED |
| 1.7 | The fee engine loads configuration via `load_yaml("fees")` and supports both the nested and a legacy structure | `code/phase4/engine/fees.py:43-65`; `engine/loader.py:13-19` | VERIFIED |
| 1.8 | Day-trading rebate mode exists and is disabled in the main environment wiring | `fees.py:29, 43-54, 128-197`; `multi_agent_portfolio_environment.py:69-81` (constructs `FeeEngine` without `is_day_trading`, whose default is `False`) | VERIFIED |
| 1.9 | The brokerage multiplier is clamped | `fees.py:36-38` — `min(1.0, max(0.0, brokerage_rate_multiplier))` | VERIFIED (refined) |
| 1.10 | The engine returns an itemized breakdown rather than an opaque total | `fees.py:86-128` | VERIFIED |

**Refinement note on 1.5.** The `status: projected` filter is implemented in the resolver, but no
`status` key occurs anywhere in `fees.yaml`. The capability exists and is unexercised by this
configuration. The revised manuscript states this explicitly rather than implying the filter is in
use; the unexercised capability is itself an instance of designed-for-change capacity.

**Refinement note on 1.9.** The clamp is to the interval [0, 1] applied to a multiplier that is
normalised against the regulatory maximum rate, so its governance meaning is a cap at the
regulatory maximum, not a generic bound. The revised manuscript says so.

## 2. Trading calendar and settlement

| # | Manuscript claim | Evidence | Status |
| --- | --- | --- | --- |
| 2.1 | Market open 09:00, close 14:00 | `code/phase4/trading_calendar.py:23-24` | VERIFIED |
| 2.2 | `settlement_days = 3` (T+3) | `trading_calendar.py:25` | VERIFIED |
| 2.3 | Holidays generated per year from a fixed list and adjusted when falling on a weekend | `trading_calendar.py:29-51` | VERIFIED |
| 2.4 | Calendar exposes `is_trading_day`, `is_market_open`, `get_trading_hour`, `get_settlement_date` | `trading_calendar.py:60, 68, 79, 91` | VERIFIED |
| 2.5 | Settlement advances by trading days, not calendar days, skipping weekends and holidays | `trading_calendar.py:91-98` via `get_next_trading_day:84-89` | VERIFIED |
| 2.6 | A fuller `T3SettlementQueue` abstraction exists in the calendar module but is not wired into the environment | `trading_calendar.py:113-166` (class); `multi_agent_portfolio_environment.py` imports the calendar but never instantiates the queue | VERIFIED |

## 3. Schema exemplars and fixtures

| # | Manuscript claim | Evidence | Status |
| --- | --- | --- | --- |
| 3.1 | Intraday CSV schema is `date,time,ticker,close` | `code/phase4/intraday_prices_hourly.csv:1` | VERIFIED |
| 3.2 | Generator produces tickers TKR1-TKR3 over 30 business days, hours {9,10,11,12,13,14} | `scripts/generate_synthetic_data.py:25-27` | VERIFIED |
| 3.3 | Liquidity-tier CSV maps tickers to TIER_1_HIGHLY_LIQUID, TIER_2_LIQUID, TIER_3_MODERATE | `generate_synthetic_data.py:56-59`; `code/phase3/surviving_stocks_liquidity_tiers.csv` | VERIFIED |
| 3.4 | Ingestion uses these columns directly with no explicit schema-validation gate | No validation call exists on the ingestion path; the contract is carried by exemplar and fixture only | VERIFIED |
| 3.5 | Generator output is 540 intraday rows and 3 liquidity rows | 30 business days x 6 hours x 3 tickers = 540; confirmed by execution (`results/validation/validation_results.json`, V3) | VERIFIED |

## 4. Defensive feature engineering

| # | Manuscript claim | Evidence | Status |
| --- | --- | --- | --- |
| 4.1 | Stable schema of exactly 14 features per ticker, in a fixed order, exposed via `get_feature_names` | `code/phase4/feature_engineering_v2.py:363-378` (14 named entries); `:380-384` | VERIFIED |
| 4.2 | NaN replacement with 0.0 | `feature_engineering_v2.py:339` | VERIFIED |
| 4.3 | Clipping to [-3, +3] then division by 3, yielding [-1, +1] | `feature_engineering_v2.py:356-358` | VERIFIED |
| 4.4 | Liquidity defaults to 0.5 when tier information is unavailable | `feature_engineering_v2.py:67, 72, 80, 85, 217, 233` | VERIFIED |

## 5. Execution constraints and negative knowledge

| # | Manuscript claim | Evidence | Status |
| --- | --- | --- | --- |
| 5.1 | A +/-10% price-limit clamp against the prior day's close | `code/phase4/multi_agent_portfolio_environment.py:131-155` (`prev_close * 0.90` / `* 1.10`) | VERIFIED |
| 5.2 | Per-agent fee engines with different brokerage multipliers | `multi_agent_portfolio_environment.py:69-81` | VERIFIED |
| 5.3 | VAT-on-brokerage is enabled unconditionally in the current wiring although agent configurations carry a per-agent VAT field | `multi_agent_portfolio_environment.py:77` (`include_vat_on_brokerage=True`, hardcoded); the per-agent `vat_on_brokerage` value is defined per investor type and passed into each agent's `fee_config` in the training driver, then never read | VERIFIED (refined) |
| 5.4 | A settlement queue and settlement-lag parameter exist, but the environment's settlement-processing hook is a stub | `multi_agent_portfolio_environment.py:34, 45, 104` (queue and lag); `:461-462` (`_process_settlements` body is `pass`) | VERIFIED |

**Refinement note on 5.3.** The field is not merely present in configuration: it is plumbed through
the training driver into the environment's per-agent `fee_config` and then ignored, because the
environment hardcodes the flag. The revised manuscript states the stronger, accurate version. The
investor-type configuration file that defines the field is not included in this package because no
manuscript claim depends on its contents beyond the existence of the field.

## 6. Automated reporting as audit artifact

| # | Manuscript claim | Evidence | Status |
| --- | --- | --- | --- |
| 6.1 | The analysis module converts an experiment history JSON into summaries and plots | `code/phase4/analysis/plot_training_results.py` | VERIFIED |
| 6.2 | It writes a markdown summary (`results_summary.md`) and a `metrics_summary.csv` with stable columns and stable file names | `plot_training_results.py:207-242` (CSV header construction), and the markdown writer in the same module | VERIFIED |
| 6.3 | The CSV header begins with eight documented columns | `plot_training_results.py:213-222` | VERIFIED |
| 6.4 | Per-agent columns are emitted in sorted order, giving deterministic serialization | `plot_training_results.py:226-239` (`sorted(...)` on every agent group) | VERIFIED |

## 7. Design-objective validations V1-V5

The harness is `scripts/validate_governance.py`. Results below were produced by executing it in this
package; they are byte-identical to the results reported in the manuscript.

| ID | What it establishes | Result |
| --- | --- | --- |
| V1 | The resolver selects the expected regulatory period on both sides of all four transitions encoded in `fees.yaml` | 8/8 cases pass |
| V2 | The settlement advance skips weekends and holidays across midweek, pre-weekend, holiday-cluster and year-end trade dates | 8/8 cases pass |
| V3 | Generator output conforms to the documented columns, hours, tickers and tier labels | all checks pass; 540 intraday rows, 3 liquidity rows |
| V4 | The documented defensive transform replaces all NaNs, clips the expected fraction, and bounds output in [-1, +1] | 10.00% NaN replacement, 15.27% clipping, output in range |
| V5 | Two runs of the reporting routine on identical input produce byte-equal CSV and markdown, with the documented leading columns | byte-equal; header starts with the eight documented columns; 25 columns total |

### What V1 and V2 do and do not establish

V1's expected regulatory-period labels are written by hand from the configuration. V1 therefore
verifies the **resolver**, not the correctness of the fee data, which the artifact itself flags as
estimates for academic use.

V2 re-implements the settlement advance independently (day-by-day, skipping weekends and holidays)
and compares it against `get_settlement_date`, but both use the **same** holiday set. V2 therefore
verifies the **advance logic**, not the fidelity of the holiday calendar to any real exchange.

The revised manuscript states both boundaries explicitly. Neither V1-V5 nor any other content of
this package is evidence about organizational adoption, governance effectiveness, user
interpretation, or audit outcomes.

### Reproducibility across environments

The results shipped in `results/validation/` were first produced in May 2026 and re-executed in
August 2026 on a different machine and operating system, under two dependency environments:
numpy 2.2.5 / pandas 2.2.3 / PyYAML 6.0.2 (the versions pinned by the original repository) and
numpy 2.5.2 / pandas 3.0.5 / PyYAML 6.0.3. The JSON results object was identical in all three
cases, including the reported sanitization rates. The determinism comes from fixed seeds
(`np.random.default_rng(42)` in the harness, `np.random.seed(42)` in the generator) and from sorted,
non-hash-ordered column construction in the reporting module.

---

## Files deliberately excluded from this package

This package contains only what is needed to check the manuscript's claims. The following parts of
the original research repository are excluded because no manuscript claim depends on them: the
reinforcement-learning trainer, the full ecosystem training driver, market-impact models, model
checkpoints, the investor-type taxonomy configuration, evaluation and smoke-test scripts, and
plotting dependencies.

One consequence: `code/phase4/multi_agent_portfolio_environment.py` is included **for inspection
only**. It imports a market-impact module that is not part of this package, so it cannot be
executed here. It is included because manuscript claims 5.1-5.4 are read from its source. The
validation harness never imports it.
