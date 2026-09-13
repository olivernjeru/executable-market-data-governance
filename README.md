# Executable market data governance: artifact and validation harness

This package accompanies *Market Data Governance as Knowledge Management: Managing Temporality via
Rule Versioning, Provenance, and Auditability*, accepted 9 September 2026 in the **VINE Journal of
Information and Knowledge Management Systems** (Emerald), DOI
[10.1108/VJIKMS-03-2026-0132](https://doi.org/10.1108/VJIKMS-03-2026-0132). It contains the parts
of the research repository that the paper's claims depend on, plus the harness that produces the
five artifact-level design-objective validations (V1-V5) reported in it.

It is provided so that the paper's technical claims can be checked independently rather than taken
on trust. `VERIFICATION_REPORT.md` maps every claim in the manuscript to the file and line range
that evidences it.

## Status of this artifact

**This is a simulated research artifact, not a trading system.** It is not connected to, endorsed
by, or representative of any exchange, broker, depository, regulator or trading venue, and it does
not execute, route or settle orders. Nothing in it is legal, financial, tax, accounting or
investment advice. Every source file carries this statement in its header.

## Provenance of the artifact

The code analysed here was written by the authors for an earlier, separate research project on
multi-agent reinforcement learning for portfolio allocation under trading frictions in a frontier
equity market. The governance mechanisms the paper studies -- effective-dated fee configuration,
deterministic rule resolution, a session and settlement calendar, schema exemplars and synthetic
fixtures, defensive feature transforms, and report-shaped outputs -- were built as engineering
necessities of that project, **not** as a governance design exercise, and not with the present
research questions in view. The paper is therefore a retrospective analysis from which design
knowledge is abstracted, and it says so.

The only component written for the present paper is `scripts/validate_governance.py`.

## What is here

```text
code/phase4/engine/resolver.py            deterministic effective-dated rule resolution
code/phase4/engine/loader.py              YAML configuration loader
code/phase4/engine/fees.py                fee computation, itemized breakdown, multiplier clamp
code/phase4/engine/__init__.py            package init
code/phase4/config/market_data/fees.yaml  effective-dated fee policy (four regulatory periods)
code/phase4/trading_calendar.py           session hours, holidays, T+3 settlement, settlement queue
code/phase4/feature_engineering_v2.py     14-feature schema and the defensive transform
code/phase4/multi_agent_portfolio_environment.py   inspection only; see note below
code/phase4/analysis/plot_training_results.py      audit-artifact writers (CSV and markdown)
code/phase4/intraday_prices_hourly.csv    schema exemplar (synthetic, produced by the generator)
code/phase3/surviving_stocks_liquidity_tiers.csv   liquidity-tier fixture (synthetic)
scripts/generate_synthetic_data.py        deterministic synthetic fixture generator (seed 42)
scripts/validate_governance.py            the V1-V5 validation harness
results/validation/                       reference output of a passing run
```

`multi_agent_portfolio_environment.py` is included **for inspection only**: manuscript claims about
price limits, per-agent fee engines, the VAT flag and the settlement stub are read from its source.
It imports a market-impact module that is not part of this package, so it cannot be executed here.
The validation harness never imports it.

## What is deliberately not here

Only the code needed to reproduce the paper's claims is included. Excluded: the reinforcement
learning trainer and its training driver, market-impact models, model checkpoints, the investor-type
taxonomy configuration, evaluation and smoke-test scripts, and plotting dependencies. None of the
manuscript's claims depend on them.

No real market data is included or redistributed. Every CSV in this package is synthetic output of
`scripts/generate_synthetic_data.py` and does not represent real market behaviour.

## Running the validations

Python 3.10 or newer.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/validate_governance.py
```

A passing run prints `[VALIDATE] overall: PASS` and writes:

- `results/validation/validation_results.json`
- `results/validation/validation_summary.md`

Compare your output against the reference copies already in `results/validation/`. The harness is
deterministic: it seeds NumPy explicitly and the reporting module builds its column order by sorting
rather than by dictionary iteration.

## Expected results

| ID | Validation | Expected |
| --- | --- | --- |
| V1 | Fee resolver boundary tests across the four regulatory transitions | 8/8 pass |
| V2 | T+3 settlement across weekends, holiday clusters and the year-end boundary | 8/8 pass |
| V3 | Schema conformance of generator output | all checks pass; 540 intraday rows, 3 liquidity rows |
| V4 | Defensive-transform sanitization rates on a 10,000-value batch | 10.00% NaN replacement, 15.27% clipping, output in [-1, +1] |
| V5 | Audit-output stability across two identical runs | byte-equal CSV and markdown; 25 columns, first 8 as documented |

These results were first produced in May 2026 and re-executed in August 2026 on a different machine
and operating system, under two dependency environments: numpy 2.2.5 / pandas 2.2.3 (the versions
pinned by the original repository) and numpy 2.5.2 / pandas 3.0.5. The results object was identical
in all three cases, including the reported sanitization rates.

## What these validations do and do not establish

They confirm that the artifact behaves as the manuscript's stated design objectives require. They
are **not** evidence about organizational adoption, governance effectiveness, user interpretation,
audit outcomes, or reduced reliance on tacit knowledge. Those belong to the paper's propositions,
which are theoretically derived and remain to be tested empirically.

V1 checks the resolver against expected labels written by hand from the configuration; it does not
validate the fee data, whose verification status is itemised in Provenance and attribution below.
V2 compares two independent implementations of the settlement advance that share the
same holiday set; it validates the advance logic, not the calendar's fidelity to any real exchange.

## Provenance and attribution

The manuscript argues that governance artifacts should record where their rules come from. It would
be inconsistent to leave that undocumented here, so each class of value below is stated with what it
approximates and how far it has been checked against public sources (checked August 2026).

The jurisdiction is Kenya; the market is the Nairobi Securities Exchange, regulated by the Capital
Markets Authority with settlement through the Central Depository and Settlement Corporation. Naming
it here is attribution, not endorsement: see the note following the table.

| Value | What it approximates | Status |
| --- | --- | --- |
| Commencement dates of the three named regimes: 2012-08-17, 2016-03-11, 2022-08-12 | Legal Notices 88/2012, 35/2016 and 135/2022 | **Verified exactly.** Kenya Law records all three as amendments to the Capital Markets (Licensing Requirements) (General) Regulations (LN 125/2002), commencing 17 August 2012, 11 March 2016 and 12 August 2022 respectively -- matching the configuration to the day |
| Brokerage caps and statutory fee components within each period | The commission schedule of those Regulations (Fifth Schedule) | **Not verified.** The Fifth Schedule text was not obtainable online. Secondary sources broadly corroborate the headline caps (a small-trade brokerage cap of ~1.78% falling to ~1.76%, and a ~2.10% maximum total cost below KES 100,000) but disagree among themselves on the statutory component breakdown. Treat the component values as approximations |
| "Pre-2012 estimates" period | No single instrument; a stand-in for the regime preceding the 2012 notice | **Estimate**, labelled as such in the configuration |
| Day-trading rebate: 5% rebate on a 0.12% levy | NSE day-trading incentive structure | **Verified.** The published structure is a 5% discount giving 0.114% against a normal 0.12% levy; the configuration reproduces both the 0.0012 base and the 0.05 rebate, and 0.0012 x 0.95 = 0.00114 |
| Day-trading period start, `2017-03-27` | Introduction of day trading | **Incorrect in the artifact.** Day trading was approved by the CMA on 26 October 2021 and launched on 22 November 2021. The configuration comment already marks the date "approximate"; it is wrong by roughly four and a half years. Retained unchanged -- see the note below |
| T+3 settlement | The equity settlement cycle | **Verified.** The market moved from T+4 to T+3 in 2011 and settles T+3 under current trading rules |
| +/-10% daily price limit against the prior close | The daily price movement limit | **Verified in substance.** The published rule caps single-session movement at 10% of the price determined in the previous session. The artifact applies it to the prior day's *last* traded price rather than that session's determined (average) price -- a simplification, not a different limit |
| 16% VAT on brokerage | Kenyan standard-rate VAT | **Verified.** 16% has been the standard rate since the VAT Act 2013, and stockbrokerage is not among the exempt services |
| Session hours 09:00-14:00 | The trading session | **Does not match the published schedule.** The published session is a 09:00-09:30 pre-open followed by continuous trading from 09:30 to 15:00. The artifact's six hourly buckets (09-14) are a simplification. Retained unchanged -- see the note below |
| Holiday calendar | A fixed list of public holidays with weekend adjustment | **Simplified.** Not a real exchange calendar; V2 validates the settlement advance against this list, not the list's fidelity |
| Prices, tickers, liquidity tiers | Nothing real | **Fully synthetic**, generated with a fixed seed by `scripts/generate_synthetic_data.py` |

### Why the two incorrect values were not corrected

The artifact is the object of study, not a deliverable to be improved. It is presented as the state
that was analysed, and silently editing it after the fact would break that correspondence, could
alter the validation results, and would misrepresent what the manuscript examined. Both defects are
therefore left in place and recorded here instead.

Neither affects any claim in the paper. V1 exercises only the four standard-rate transitions, not
the day-trading period; V2 validates the settlement advance against the artifact's own holiday set,
not against a real exchange calendar; and no proposition depends on the session being any particular
length. The manuscript already states that V1 validates the resolver rather than the fee data.

It is worth naming what happened here, because it is the paper's own argument turned on itself:
writing down the provenance of these values surfaced two errors that had been invisible for as long
as the values sat in the configuration undocumented. An effective-dated rule whose effective date is
wrong is exactly the failure mode that dating a rule is supposed to make discoverable.

Three consequences follow, and the manuscript relies on all three:

1. **The numbers are not the object of study.** The paper's claims concern the *mechanisms* — how a rule is dated, resolved, bounded and reported — not whether any rate is correct. V1 validates the resolver against labels written by hand from the configuration; it does not validate the rates.
2. **No institution is implicated.** No exchange, regulator or depository supplied data for, took
   part in, reviewed, or endorses this work. Identifiers naming a specific exchange were removed
   from this package precisely because a class or file so named would assert an official standing
   the code does not have. Naming the jurisdiction in this section is the opposite act: it
   attributes the public instruments the values approximate, so a reader can check them.

   Sources consulted for the table above: Kenya Law (the Regulations and their amendment history),
   the exchange's published equity trading rules and day-trading materials, and Kenya Revenue
   Authority guidance on the standard VAT rate. All are public; none was obtained under licence or
   confidentiality.
3. **Nothing here should be relied upon** for trading, compliance, valuation, or any decision with real consequences.

## Licence

Apache-2.0. Copyright 2026 Oliver Njeru. See `LICENSE` for the licence text and `NOTICE` for the
attribution statement.

The copyright holder is declared in `NOTICE` rather than in per-file headers, and `LICENSE` is a
pristine, unmodified copy of the canonical Apache-2.0 text. `NOTICE` explains why: adding headers
would shift every line number and break the file-and-line correspondence that
`VERIFICATION_REPORT.md` depends on, which would edit the very artifact the paper asks a reader to
inspect unchanged.

## Citing this artifact

If you use this package, please cite both the article and the archived artifact.

> Njeru, O. and Okanda, P. (2026), "Market Data Governance as Knowledge Management: Managing
> Temporality via Rule Versioning, Provenance, and Auditability", *VINE Journal of Information and
> Knowledge Management Systems*, Emerald Publishing.
> <https://doi.org/10.1108/VJIKMS-03-2026-0132>

```bibtex
@article{njeru2026marketdatagovernance,
  author  = {Njeru, Oliver and Okanda, Paul},
  title   = {Market Data Governance as Knowledge Management: Managing Temporality
             via Rule Versioning, Provenance, and Auditability},
  journal = {VINE Journal of Information and Knowledge Management Systems},
  year    = {2026},
  doi     = {10.1108/VJIKMS-03-2026-0132},
  note    = {EarlyCite; volume, issue and pages pending}
}
```

The artifact is archived on Zenodo. Cite the version the article analysed:

- **v1.0.0**, the exact state analysed in the article: <https://doi.org/10.5281/zenodo.22734804>
- All versions: <https://doi.org/10.5281/zenodo.22734803>

```bibtex
@software{njeru2026executablegovernanceartifact,
  author    = {Njeru, Oliver and Okanda, Paul},
  title     = {Executable market data governance: artifact and validation harness},
  version   = {v1.0.0},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.22734804}
}
```

## Authors

Oliver Njeru (ORCID [0009-0008-6611-3813](https://orcid.org/0009-0008-6611-3813)) and Paul Okanda,
School of Science and Technology, United States International University - Africa, Nairobi, Kenya.

Contributions: O. Njeru wrote the artifact, the validation harness and the paper; P. Okanda
supervised and reviewed.
