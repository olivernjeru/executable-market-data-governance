# SIMULATED RESEARCH ARTIFACT -- NOT A TRADING SYSTEM.
"""
  This code is not connected to, endorsed by, or representative of any exchange, broker, depository, regulator or trading venue, and it does not execute, route or settle orders. Nothing here is legal, financial, tax, accounting or investment advice. Fee, calendar, settlement and price-limit values are approximations compiled by the authors from public sources for academic use. They are NOT official data and have NOT been verified against the instruments they approximate. Do not rely on them for any real-world purpose. See README.md (Provenance and attribution) for what each class of value approximates.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Optional


def _parse(date_val: Any) -> Optional[dt.date]:
    if date_val is None or date_val is False:
        return None
    if isinstance(date_val, dt.date):
        return date_val
    if isinstance(date_val, str):
        return dt.date.fromisoformat(date_val)
    return None


def is_active(item: Any, on: dt.date, include_projected: bool = False) -> bool:
    status = getattr(item, "status", None) or (
        isinstance(item, dict) and item.get("status")
    )
    if status == "projected" and not include_projected:
        return False

    eff_from = _parse(
        getattr(item, "effective_from", None)
        or (isinstance(item, dict) and item.get("effective_from"))
    )
    eff_to = _parse(
        getattr(item, "effective_to", None)
        or (isinstance(item, dict) and item.get("effective_to"))
    )

    if eff_from and on < eff_from:
        return False
    if eff_to and on > eff_to:
        return False
    return True


def resolve_effective_item(
    items: list[Any], on: dt.date, include_projected: bool = False
) -> Optional[Any]:
    candidates = [
        i for i in items if is_active(i, on, include_projected=include_projected)
    ]
    if not candidates:
        return None

    def _key(i: Any):
        eff_from = getattr(i, "effective_from", None) or (
            isinstance(i, dict) and i.get("effective_from")
        )
        return _parse(eff_from) or dt.date.min

    candidates.sort(key=_key, reverse=True)
    return candidates[0]
