# SIMULATED RESEARCH ARTIFACT -- NOT A TRADING SYSTEM.
"""
This code is not connected to, endorsed by, or representative of any exchange, broker, depository, regulator or trading venue, and it does not execute, route or settle orders. Nothing here is legal, financial, tax, accounting or investment advice. Fee, calendar, settlement and price-limit values are approximations compiled by the authors from public sources for academic use. They are NOT official data and have NOT been verified against the instruments they approximate. Do not rely on them for any real-world purpose. See README.md (Provenance and attribution) for what each class of value approximates.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from .loader import load_yaml
from .resolver import resolve_effective_item


class FeeEngine:
    """
    Compute applicable fees for trades given the YAML config.
    """

    def __init__(
        self,
        on: Optional[dt.date] = None,
        include_projected: bool = False,
        *,
        include_vat_on_brokerage: bool = False,
        vat_rate: float = 0.16,
        include_broker_levies: bool = True,
        brokerage_rate_multiplier: float = 1.0,
        is_day_trading: bool = False,
    ) -> None:
        self.on = on or dt.date.today()
        self.include_projected = include_projected
        self.include_vat_on_brokerage = include_vat_on_brokerage
        self.vat_rate = vat_rate
        self.include_broker_levies = include_broker_levies
        self.brokerage_rate_multiplier = min(
            1.0, max(0.0, brokerage_rate_multiplier)
        )  # Clamp between 0 and 1
        self.is_day_trading = is_day_trading
        self._fees = load_yaml("fees")

        # Handle both old and new fee structure
        self._use_new_structure = "equities_trading_fees" in self._fees

    def _get_rule(self, key: str) -> Dict[str, Any]:
        if self._use_new_structure:
            # Navigate to appropriate section
            if key == "shares_transaction_fees":
                if self.is_day_trading:
                    # Use day trading rates with rebates
                    rules = (
                        self._fees.get("equities_trading_fees", {})
                        .get("shares_transaction_fees", {})
                        .get("day_trading_rates", {})
                        .get("periods", [])
                    )
                else:
                    # Use standard rates
                    rules = (
                        self._fees.get("equities_trading_fees", {})
                        .get("shares_transaction_fees", {})
                        .get("standard_rates", [])
                    )
            else:
                # Fallback to legacy structure for other keys
                rules = self._fees.get(key, [])
        else:
            # Legacy structure: direct access
            rules = self._fees.get(key, [])

        if not rules:
            raise ValueError(f"No fee rules found for {key}")

        chosen = resolve_effective_item(
            rules, self.on, include_projected=self.include_projected
        )
        if not chosen:
            raise ValueError(f"No effective fee rule for {key} on {self.on}")
        return chosen

    def equity_trade_cost(
        self, kes_value: float, transaction_type: str = "buy"
    ) -> Dict[str, float]:
        rule = self._get_rule("shares_transaction_fees")

        if self.is_day_trading and self._use_new_structure:
            # For day trading, use rebated rates from components
            comps = rule["components"]
            tier, itemized = self._equity_itemized_day_trading(
                kes_value, comps, transaction_type
            )
        else:
            # Standard or legacy structure
            comps = rule["components"]
            tier, itemized = self._equity_itemized(kes_value, comps, transaction_type)
        return itemized

    def corporate_bond_trade_cost(self, kes_value: float) -> Dict[str, float]:
        raise NotImplementedError(
            "Corporate bond fee computation is out of scope for equities-only mode."
        )

    def government_bond_trade_cost(self, kes_value: float) -> Dict[str, float]:
        raise NotImplementedError(
            "Government bond fee computation is out of scope for equities-only mode."
        )

    def equity_itemized_breakdown(
        self, kes_value: float, transaction_type: str = "buy"
    ) -> Dict[str, float]:
        """Public method to get itemized equity fees (includes brokerage tier chosen)."""
        rule = self._get_rule("shares_transaction_fees")

        if self.is_day_trading and self._use_new_structure:
            # For day trading, use rebated rates
            comps = rule["components"]
            tier, itemized = self._equity_itemized_day_trading(
                kes_value, comps, transaction_type
            )
        else:
            # Standard or legacy structure
            comps = rule["components"]
            tier, itemized = self._equity_itemized(kes_value, comps, transaction_type)
        itemized["_brokerage_tier"] = tier
        return itemized

    # --- internal helpers ---
    def _equity_itemized_day_trading(
        self, kes_value: float, comps: Dict[str, Any], transaction_type: str = "buy"
    ) -> tuple[str, Dict[str, float]]:
        """Calculate day trading fees with rebates applied."""
        rebated_fees = comps.get("rebated_statutory_fees", {})

        # Apply standard brokerage calculation (no rebates on brokerage)
        # Use standard rates for brokerage calculation
        brokerage_rates_ref = comps.get("brokerage_rates", "")
        if "Apply standard_rates" in brokerage_rates_ref:
            # Need to get standard rates for brokerage
            standard_rule = None
            if self._use_new_structure:
                standard_rules = (
                    self._fees.get("equities_trading_fees", {})
                    .get("shares_transaction_fees", {})
                    .get("standard_rates", [])
                )
                standard_rule = resolve_effective_item(
                    standard_rules, self.on, include_projected=self.include_projected
                )

            if standard_rule:
                tier, result = self._equity_itemized(
                    kes_value, standard_rule["components"], transaction_type
                )

                # REPLACE statutory fees with rebated versions (don't add to them)
                for fee_type, fee_info in rebated_fees.items():
                    chargeable_rate = fee_info.get("chargeable_levy_after_rebate", 0.0)
                    # Map day trading fee names to standard fee names
                    standard_name = self._map_day_trading_fee_name(fee_type)
                    if standard_name:
                        # Remove the old standard fee and replace with rebated version
                        old_fee_name = self._get_reverse_fee_name_mapping().get(
                            standard_name
                        )
                        if old_fee_name and old_fee_name in result:
                            del result[old_fee_name]
                        # Add rebated fee with old naming for compatibility
                        if old_fee_name:
                            result[old_fee_name] = chargeable_rate * kes_value

                result["total"] = sum(
                    v for k, v in result.items() if k != "_brokerage_tier"
                )
                return tier, result

        # Fallback: calculate directly from day trading rates
        return self._equity_itemized_fallback_day_trading(
            kes_value, rebated_fees, transaction_type
        )

    def _get_reverse_fee_name_mapping(self) -> Dict[str, str]:
        """Map new fee names back to old fee names for compatibility."""
        return {
            "cma_transaction_fee": "cma_investor_fee",
            "cma_investor_compensation_fund_fee": "icf_broker_contribution",
            "exchange_transaction_fee": "exchange_fee",
            "cdsc_transaction_fee": "cdsc_fee",
        }

    def _map_day_trading_fee_name(self, day_trading_name: str) -> Optional[str]:
        """Map day trading fee names to standard fee names."""
        mapping = {
            "exchange_transaction_levy": "exchange_transaction_fee",
            "cma_transaction_levy": "cma_transaction_fee",
            "cdsc_transaction_levy": "cdsc_transaction_fee",
        }
        return mapping.get(day_trading_name)

    def _equity_itemized_fallback_day_trading(
        self,
        kes_value: float,
        rebated_fees: Dict[str, Any],
        transaction_type: str = "buy",
    ) -> tuple[str, Dict[str, float]]:
        """Fallback day trading calculation when standard rates unavailable."""
        result: Dict[str, float] = {}

        # Calculate rebated statutory fees
        for fee_type, fee_info in rebated_fees.items():
            chargeable_rate = fee_info.get("chargeable_levy_after_rebate", 0.0)
            standard_name = self._map_day_trading_fee_name(fee_type)
            if standard_name:
                result[standard_name] = chargeable_rate * kes_value

        # Add minimal brokerage (would need standard rates for proper calculation)
        result["brokerage"] = 0.001 * kes_value  # Placeholder - 0.1%

        # Add transaction levy (0.3% on sales from July 1, 2015 onwards)
        transaction_levy_start_date = dt.date(2015, 7, 1)
        if (
            transaction_type.lower() == "sell"
            and self.on >= transaction_levy_start_date
        ):
            result["transaction_levy"] = 0.003 * kes_value  # 0.3% on sale transactions

        result["total"] = sum(result.values())
        return "day_trading", result

    def _equity_itemized(
        self, kes_value: float, comps: Dict[str, Any], transaction_type: str = "buy"
    ) -> tuple[str, Dict[str, float]]:
        import datetime as dt

        statutory = comps.get("statutory_fees", {})
        payers = comps.get("statutory_fee_payers", {})
        odd_lots = comps.get("odd_lots", {})

        # Handle new odd_lots structure vs legacy
        if isinstance(odd_lots, dict) and "upto_kes_3000" in odd_lots:
            # New structure with separate upto/exceeding sections
            odd_lot_threshold = 3000  # Fixed in new structure
            odd_lot_cap = odd_lots.get("upto_kes_3000", {}).get("commission_kes", 100)
            rate_above_threshold = odd_lots.get("exceeding_kes_3000", {}).get(
                "commission_rate", 0.0176
            )
        else:
            # Legacy structure
            odd_lot_threshold = odd_lots.get("value_threshold_kes", 3000)
            odd_lot_cap = odd_lots.get("max_commission_kes", 100)
            rate_above_threshold = odd_lots.get("rate_above_threshold", 0.0)

        # Odd lot floor enforcement from August 17, 2012 onwards
        odd_lot_floor_date = dt.date(2012, 8, 17)
        enforce_odd_lot_floor = self.on >= odd_lot_floor_date

        # Check for odd-lot transaction first
        if kes_value <= odd_lot_threshold:
            tier = "odd_lots"
            if enforce_odd_lot_floor:
                # Fixed 100 KES brokerage for all trades ≤ 3,000 KES from Aug 17, 2012 onwards
                brokerage = (
                    100.0  # Fixed fee, not affected by brokerage_rate_multiplier
                )
            else:
                # Pre-Aug 17, 2012: Use percentage calculation with cap
                calculated_brokerage = (
                    rate_above_threshold * kes_value * self.brokerage_rate_multiplier
                )
                brokerage = min(calculated_brokerage, odd_lot_cap)
        else:
            # Regular tiered transaction
            small = comps.get("brokerage_max_tiered", {}).get("small_trades", {})
            threshold = small.get("threshold_kes", 100000)

            if kes_value <= threshold:
                tier = "small_trades"
                brokerage_cfg = comps.get("brokerage_max_tiered", {}).get(
                    "small_trades", {}
                )
            else:
                tier = "large_trades"
                brokerage_cfg = comps.get("brokerage_max_tiered", {}).get(
                    "large_trades", {}
                )

            max_rate = brokerage_cfg.get("brokerage_max", 0.0)
            brokerage = max_rate * kes_value * self.brokerage_rate_multiplier

        result: Dict[str, float] = {"brokerage": brokerage}

        if self.include_vat_on_brokerage and brokerage > 0:
            result["vat_on_brokerage"] = brokerage * self.vat_rate

        # Add statutory fees with name mapping for new/old structure
        fee_name_mapping = self._get_fee_name_mapping()

        for old_name, new_name in fee_name_mapping.items():
            # Try new name first, then old name
            v = statutory.get(new_name) or statutory.get(old_name)
            if isinstance(v, (int, float)):
                # Respect payer roles if configured
                payer = payers.get(new_name) or payers.get(old_name)
                if payer == "broker" and not self.include_broker_levies:
                    continue
                # Use consistent naming in result (use old names for backward compatibility)
                result[old_name] = v * kes_value

        # Add transaction levy (0.3% on sales from July 1, 2015 onwards)
        transaction_levy_start_date = dt.date(2015, 7, 1)
        if (
            transaction_type.lower() == "sell"
            and self.on >= transaction_levy_start_date
        ):
            result["transaction_levy"] = 0.003 * kes_value  # 0.3% on sale transactions

        result["total"] = sum(result.values())
        return tier, result

    def _get_fee_name_mapping(self) -> Dict[str, str]:
        """Map old fee names to new fee names for compatibility."""
        return {
            "cma_investor_fee": "cma_transaction_fee",
            "icf_broker_contribution": "cma_investor_compensation_fund_fee",
            "exchange_fee": "exchange_transaction_fee",
            "cdsc_fee": "cdsc_transaction_fee",
        }

    def period_summary(
        self, kes_value: float, transaction_type: str = "buy"
    ) -> Dict[str, Any]:
        """Return a summary including period metadata and itemized breakdown."""
        rule = self._get_rule("shares_transaction_fees")
        tier, itemized = self._equity_itemized(
            kes_value, rule["components"], transaction_type
        )
        return {
            "effective_from": rule.get("effective_from"),
            "effective_to": rule.get("effective_to"),
            "brokerage_tier": tier,
            "itemized": itemized,
            "total": itemized.get("total", 0.0),
        }

    def private_transfer_cost(
        self, kes_value: float, transfer_type: str = "gift_to_close_relation"
    ) -> Dict[str, float]:
        """
        Calculate private transfer fees based on transfer type.
        """
        try:
            # Get private transfer rules
            private_rules = self._fees.get("private_transfer_fees", [])
            if not private_rules:
                return {"error": "No private transfer fees configured", "total": 0.0}

            if transfer_type == "gift_to_close_relation":
                # Regulation 57(a) - subject to prevailing brokerage commission
                return self._private_transfer_gift(kes_value)
            elif transfer_type == "estate_settlement":
                return self._private_transfer_estate(kes_value)
            elif transfer_type == "reorganisation":
                return self._private_transfer_reorganisation(kes_value)
            elif transfer_type == "beneficial_change":
                return self._private_transfer_beneficial_change(kes_value)
            else:
                return {
                    "error": f"Unknown transfer type: {transfer_type}",
                    "total": 0.0,
                }

        except Exception as e:
            return {
                "error": f"Private transfer calculation failed: {str(e)}",
                "total": 0.0,
            }

    def _private_transfer_gift(self, kes_value: float) -> Dict[str, float]:
        """Calculate fees for gift to close relation (Reg 57a) - uses brokerage commission."""
        # This uses the same calculation as regular equity trades
        return self.equity_itemized_breakdown(kes_value)

    def _private_transfer_estate(self, kes_value: float) -> Dict[str, float]:
        """Calculate fees for estate settlement transfers."""
        if kes_value < 10000:
            return {
                "estate_transfer_fee": 0.0,
                "exemption_applied": "Below 10,000 KES threshold",
                "total": 0.0,
            }
        else:
            return {"estate_transfer_fee": 1500.0, "total": 1500.0}

    def _private_transfer_reorganisation(self, kes_value: float) -> Dict[str, float]:
        """Calculate fees for reorganisation transfers (no beneficial change)."""
        fee = min(kes_value * 0.001, 100000.0)  # 0.1% of nominal value, max 100k
        return {
            "reorganisation_fee": fee,
            "rate_applied": "0.1% of nominal value",
            "maximum_cap": "100,000 KES",
            "total": fee,
        }

    def _private_transfer_beneficial_change(self, kes_value: float) -> Dict[str, float]:
        """Calculate fees for transfers resulting in beneficial change."""
        fee = kes_value * 0.005  # 0.5% of market value
        return {
            "beneficial_change_fee": fee,
            "rate_applied": "0.5% of market value",
            "total": fee,
        }
