# SIMULATED RESEARCH ARTIFACT -- NOT A TRADING SYSTEM.
"""
This code is not connected to, endorsed by, or representative of any exchange, broker, depository, regulator or trading venue, and it does not execute, route or settle orders. Nothing here is legal, financial, tax, accounting or investment advice. Fee, calendar, settlement and price-limit values are approximations compiled by the authors from public sources for academic use. They are NOT official data and have NOT been verified against the instruments they approximate. Do not rely on them for any real-world purpose. See README.md (Provenance and attribution) for what each class of value approximates.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from collections import defaultdict, deque
import sys
import datetime as dt

# Make local engine/ and alpha/ importable for research code snapshot
sys.path.insert(0, str(Path(__file__).parent))
from engine.fees import FeeEngine
from alpha.research.experimental.market_impact import EnhancedMarketImpactModel


class MultiAgentPortfolioEnvironment:
    """Multi-agent portfolio optimization environment with shared market dynamics."""

    def __init__(
        self,
        intraday_prices: pd.DataFrame,
        feature_engineer,
        tickers: List[str],
        trading_calendar: pd.DatetimeIndex,
        agent_configs: List[Dict[str, Any]],
        liquidity_tiers: Optional[pd.DataFrame] = None,
        market_impact_enabled: bool = True,
        costs_enabled: bool = True,
        trading_hours: Optional[List[int]] = None,
        settlement_lag_days: int = 3,
    ):
        self.intraday_prices = intraday_prices
        self.feature_engineer = feature_engineer
        self.tickers = tickers
        self.trading_calendar = trading_calendar
        self.agent_configs = agent_configs
        self.num_agents = len(agent_configs)
        self.market_impact_enabled = market_impact_enabled
        self.costs_enabled = costs_enabled
        self.trading_hours = trading_hours or [9, 10, 11, 12, 13, 14]
        self.settlement_lag_days = settlement_lag_days

        # Liquidity tiers for market impact
        self.liquidity_tiers = liquidity_tiers
        self.ticker_to_tier = {}
        if (
            liquidity_tiers is not None
            and "ticker" in liquidity_tiers.columns
            and "tier" in liquidity_tiers.columns
        ):
            self.ticker_to_tier = dict(
                zip(liquidity_tiers["ticker"], liquidity_tiers["tier"])
            )

        # Initialize market impact model
        if self.market_impact_enabled:
            self.market_impact_model = EnhancedMarketImpactModel(
                enable_empirical_validation=True
            )
        else:
            self.market_impact_model = None

        # Initialize fee engines per agent (different fee tiers)
        self.fee_engines = {}
        for config in agent_configs:
            agent_id = config["agent_id"]
            fee_config = config.get("fee_config", {})
            brokerage_rate = fee_config.get("brokerage_rate", 0.0176)
            multiplier = brokerage_rate / 0.0176  # Normalize to regulatory max
            self.fee_engines[agent_id] = FeeEngine(
                on=dt.date.today(),
                brokerage_rate_multiplier=multiplier,
                include_vat_on_brokerage=True,
            )

        # Per-agent state tracking
        self.agent_states = {}
        for config in agent_configs:
            agent_id = config["agent_id"]
            self.agent_states[agent_id] = {
                "investor_type": config["investor_type"],
                "initial_capital": config["initial_capital"],
                "portfolio_value": config["initial_capital"],
                "cash": config["initial_capital"],
                "holdings": {ticker: 0.0 for ticker in tickers},
                "weights": np.zeros(len(tickers)),
                "cumulative_fees": 0.0,
                "cumulative_turnover": 0.0,
                "position_limits": config.get("position_limits", {}),
                "history": [],
            }

        # Global state tracking
        self.current_step = 0
        self.current_date = None
        self.current_hour = None
        self.intraday_bar_index = 0

        # Settlement queue (T+3 settlement)
        self.settlement_queue = deque()

        # Market impact cache (for performance)
        self.market_impact_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

        # Validate configuration
        self._validate_configuration()

    def _validate_configuration(self):
        missing_tickers = set(self.tickers) - set(self.intraday_prices.columns)
        if missing_tickers:
            raise ValueError(f"Tickers not in intraday_prices: {missing_tickers}")
        agent_ids = [config["agent_id"] for config in self.agent_configs]
        if len(agent_ids) != len(set(agent_ids)):
            raise ValueError("Agent IDs must be unique")
        if not (2 <= self.num_agents <= 20):
            raise ValueError(f"num_agents must be 2-20, got {self.num_agents}")
        print(f"[INFO] MultiAgentPortfolioEnvironment initialized:")
        print(f"  - Num agents: {self.num_agents}")
        print(f"  - Tickers: {len(self.tickers)}")
        print(f"  - Intraday bars: {len(self.intraday_prices)}")
        print(f"  - Market impact: {self.market_impact_enabled}")
        print(f"  - Costs enabled: {self.costs_enabled}")
        print(f"  - Settlement lag: T+{self.settlement_lag_days}")

    def _check_price_limits(
        self, ticker: str, proposed_price: float
    ) -> Tuple[bool, float]:
        try:
            current_date_idx = self.trading_calendar.index(self.current_date.date())
        except (ValueError, AttributeError):
            return True, proposed_price
        if current_date_idx == 0:
            return True, proposed_price
        prev_date = self.trading_calendar[current_date_idx - 1]
        prev_day_data = self.intraday_prices[
            (self.intraday_prices.index.get_level_values(0) == prev_date.date())
        ]
        if len(prev_day_data) == 0:
            return True, proposed_price
        prev_close = prev_day_data[ticker].iloc[-1]
        if pd.isna(prev_close) or prev_close <= 0:
            return True, proposed_price
        lower_limit = prev_close * 0.90
        upper_limit = prev_close * 1.10
        if proposed_price < lower_limit:
            return False, lower_limit
        elif proposed_price > upper_limit:
            return False, upper_limit
        else:
            return True, proposed_price

    def reset(self, start_date: Optional[pd.Timestamp] = None) -> Dict[Any, np.ndarray]:
        if start_date is None:
            start_date = self.trading_calendar[0]
        self.current_date = start_date
        self.current_hour = self.trading_hours[0]
        try:
            mask = (
                self.intraday_prices.index.get_level_values("date") == start_date
            ) & (
                self.intraday_prices.index.get_level_values("time") == self.current_hour
            )
            self.intraday_bar_index = np.where(mask)[0][0]
        except Exception:
            self.intraday_bar_index = 0
        self.current_step = 0
        for agent_id, state in self.agent_states.items():
            state["portfolio_value"] = state["initial_capital"]
            state["cash"] = state["initial_capital"]
            state["holdings"] = {ticker: 0.0 for ticker in self.tickers}
            state["weights"] = np.zeros(len(self.tickers))
            state["cumulative_fees"] = 0.0
            state["cumulative_turnover"] = 0.0
            state["history"] = []
        self.settlement_queue.clear()
        self.market_impact_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        initial_states = {}
        for agent_id in self.agent_states.keys():
            initial_states[agent_id] = self._get_state_vector(agent_id)
        return initial_states

    def _get_state_vector(self, agent_id: Any) -> np.ndarray:
        agent_state = self.agent_states[agent_id]
        base_features = self.feature_engineer.get_state_vector(
            self.current_date, self.tickers, standardize=True
        )
        portfolio_features = []
        cash_pct = (
            agent_state["cash"] / agent_state["portfolio_value"]
            if agent_state["portfolio_value"] > 0
            else 0.0
        )
        portfolio_features.append(cash_pct)
        portfolio_features.extend(agent_state["weights"])
        hour_of_day = self.current_hour - 9
        hours_to_close = 14 - self.current_hour
        portfolio_features.append(hour_of_day / 5.0)
        portfolio_features.append(hours_to_close / 5.0)
        state = np.concatenate([base_features, np.array(portfolio_features)])
        return state

    def step(self, actions: Dict[Any, np.ndarray]) -> Tuple[Dict, Dict, Dict, Dict]:
        self._process_settlements()
        current_prices = self._get_current_prices()
        aggregated_orders = self._aggregate_orders(actions, current_prices)
        market_impacts = self._calculate_market_impacts(
            aggregated_orders, current_prices
        )
        rewards = {}
        infos = {}
        for agent_id, action in actions.items():
            reward, info = self._execute_agent_orders(
                agent_id, action, current_prices, market_impacts
            )
            rewards[agent_id] = reward
            infos[agent_id] = info
        self.current_step += 1
        self.intraday_bar_index += 1
        done = self.intraday_bar_index >= len(self.intraday_prices)
        dones = {agent_id: done for agent_id in self.agent_states.keys()}
        if not done:
            try:
                next_row = self.intraday_prices.iloc[self.intraday_bar_index]
                self.current_date = next_row.name[0]
                self.current_hour = next_row.name[1]
            except Exception:
                pass
            next_states = {
                agent_id: self._get_state_vector(agent_id)
                for agent_id in self.agent_states.keys()
            }
        else:
            state_dim = len(self._get_state_vector(list(self.agent_states.keys())[0]))
            next_states = {
                agent_id: np.zeros(state_dim) for agent_id in self.agent_states.keys()
            }
        return next_states, rewards, dones, infos

    def _get_current_prices(self) -> Dict[str, float]:
        if self.intraday_bar_index >= len(self.intraday_prices):
            current_row = self.intraday_prices.iloc[-1]
        else:
            current_row = self.intraday_prices.iloc[self.intraday_bar_index]
        prices = {}
        for ticker in self.tickers:
            if ticker in current_row:
                price = current_row[ticker]
                if isinstance(price, pd.Series):
                    price = price.get("close", np.nan)
                prices[ticker] = price if not np.isnan(price) else None
            else:
                prices[ticker] = None
        return prices

    def _aggregate_orders(
        self, actions: Dict[Any, np.ndarray], current_prices: Dict[str, float]
    ) -> Dict[str, float]:
        aggregated = defaultdict(float)
        for agent_id, action in actions.items():
            agent_state = self.agent_states[agent_id]
            portfolio_value = agent_state["portfolio_value"]
            action = np.clip(action, 0, 1)
            action = action / (action.sum() + 1e-8)
            action = self._apply_position_limits(agent_id, action)
            target_values = action * portfolio_value
            current_holdings_values = []
            for i, ticker in enumerate(self.tickers):
                price = current_prices.get(ticker)
                if price is not None:
                    value = agent_state["holdings"][ticker] * price
                else:
                    value = 0.0
                current_holdings_values.append(value)
            current_holdings_values = np.array(current_holdings_values)
            order_values = target_values - current_holdings_values
            for i, ticker in enumerate(self.tickers):
                if current_prices.get(ticker) is not None:
                    aggregated[ticker] += order_values[i]
        return dict(aggregated)

    def _apply_position_limits(self, agent_id: Any, action: np.ndarray) -> np.ndarray:
        agent_state = self.agent_states[agent_id]
        position_limits = agent_state.get("position_limits", {})
        max_position_pct = position_limits.get("max_position_pct", 1.0)
        action = np.clip(action, 0, max_position_pct)
        action = action / (action.sum() + 1e-8)
        return action

    def _calculate_market_impacts(
        self, aggregated_orders: Dict[str, float], current_prices: Dict[str, float]
    ) -> Dict[str, float]:
        if not self.market_impact_enabled:
            return {ticker: 0.0 for ticker in aggregated_orders.keys()}
        impacts = {}
        for ticker, order_value in aggregated_orders.items():
            if abs(order_value) < 1e-6:
                impacts[ticker] = 0.0
                continue
            cache_key = (ticker, self.current_date, round(order_value, -3))
            if cache_key in self.market_impact_cache:
                impacts[ticker] = self.market_impact_cache[cache_key]
                self.cache_hits += 1
                continue
            self.cache_misses += 1
            tier = self.ticker_to_tier.get(ticker, "TIER_2_LIQUID")
            if tier == "TIER_1_HIGHLY_LIQUID":
                est_daily_volume_kes = 50_000_000
                base_impact_bps = 2
            elif tier == "TIER_2_LIQUID":
                est_daily_volume_kes = 5_000_000
                base_impact_bps = 10
            else:
                est_daily_volume_kes = 500_000
                base_impact_bps = 25
            pct_of_daily_volume = abs(order_value) / est_daily_volume_kes
            impact_bps = base_impact_bps * pct_of_daily_volume
            impact_fraction = impact_bps / 10000.0
            if order_value > 0:
                impact_fraction = abs(impact_fraction)
            else:
                impact_fraction = -abs(impact_fraction)
            impact_fraction = np.clip(impact_fraction, -0.10, 0.10)
            impacts[ticker] = impact_fraction
            self.market_impact_cache[cache_key] = impact_fraction
        return impacts

    def _execute_agent_orders(
        self,
        agent_id: Any,
        action: np.ndarray,
        current_prices: Dict[str, float],
        market_impacts: Dict[str, float],
    ) -> Tuple[float, Dict]:
        agent_state = self.agent_states[agent_id]
        action = np.clip(action, 0, 1)
        action = action / (action.sum() + 1e-8)
        action = self._apply_position_limits(agent_id, action)
        portfolio_value_before = agent_state["portfolio_value"]
        execution_prices = {}
        circuit_breakers_triggered = []
        for ticker, price in current_prices.items():
            if price is not None:
                impact = market_impacts.get(ticker, 0.0)
                proposed_price = price * (1 + impact)
                within_limits, clamped_price = self._check_price_limits(
                    ticker, proposed_price
                )
                execution_prices[ticker] = clamped_price
                if not within_limits:
                    circuit_breakers_triggered.append(ticker)
            else:
                execution_prices[ticker] = None
        target_values = action * portfolio_value_before
        current_holdings_values = []
        for i, ticker in enumerate(self.tickers):
            price = execution_prices.get(ticker)
            if price is not None:
                value = agent_state["holdings"][ticker] * price
            else:
                value = 0.0
            current_holdings_values.append(value)
        current_holdings_values = np.array(current_holdings_values)
        target_shares = []
        for i, ticker in enumerate(self.tickers):
            price = execution_prices.get(ticker)
            if price is not None and price > 0:
                shares = target_values[i] / price
            else:
                shares = 0.0
            target_shares.append(shares)
        target_shares = np.array(target_shares)
        current_shares = np.array(
            [agent_state["holdings"][ticker] for ticker in self.tickers]
        )
        trades = target_shares - current_shares
        total_fees = 0.0
        turnover = 0.0
        for i, ticker in enumerate(self.tickers):
            trade_qty = trades[i]
            if abs(trade_qty) < 1e-6:
                continue
            price = execution_prices.get(ticker)
            if price is None or price <= 0:
                continue
            trade_value = abs(trade_qty * price)
            turnover += trade_value
            if self.costs_enabled:
                side = "buy" if trade_qty > 0 else "sell"
                fees_result = self.fee_engines[agent_id].equity_trade_cost(
                    trade_value, transaction_type=side
                )
                total_fees += fees_result.get("total", 0.0)
            agent_state["holdings"][ticker] += trade_qty
        total_trade_value = sum(
            [
                trades[i] * execution_prices.get(self.tickers[i], 0.0)
                for i in range(len(self.tickers))
                if execution_prices.get(self.tickers[i]) is not None
            ]
        )
        agent_state["cash"] -= total_trade_value + total_fees
        agent_state["cumulative_fees"] += total_fees
        agent_state["cumulative_turnover"] += turnover
        holdings_value = sum(
            [
                agent_state["holdings"][ticker] * (execution_prices.get(ticker) or 0.0)
                for ticker in self.tickers
            ]
        )
        portfolio_value_after = agent_state["cash"] + holdings_value
        agent_state["portfolio_value"] = portfolio_value_after
        if portfolio_value_after > 0:
            agent_state["weights"] = np.array(
                [
                    agent_state["holdings"][ticker]
                    * (execution_prices.get(ticker) or 0.0)
                    / portfolio_value_after
                    for ticker in self.tickers
                ]
            )
        else:
            agent_state["weights"] = np.zeros(len(self.tickers))
        log_return = 0.0
        cost_ratio = 0.0
        if portfolio_value_before > 0 and portfolio_value_after > 0:
            log_return = np.log(portfolio_value_after / portfolio_value_before)
            cost_ratio = total_fees / portfolio_value_before
            reward = log_return - cost_ratio
        else:
            reward = 0.0
        info = {
            "portfolio_value": portfolio_value_after,
            "cash": agent_state["cash"],
            "fees": total_fees,
            "turnover": turnover,
            "log_return": log_return,
            "cost_ratio": cost_ratio,
            "circuit_breakers_triggered": circuit_breakers_triggered,
        }
        agent_state["history"].append(
            {
                "date": self.current_date,
                "hour": self.current_hour,
                "portfolio_value": portfolio_value_after,
                "cash": agent_state["cash"],
                "fees": total_fees,
                "turnover": turnover,
                "reward": reward,
            }
        )
        return reward, info

    def _process_settlements(self):
        pass

    def get_agent_metrics(self, agent_id: Any) -> Dict[str, float]:
        agent_state = self.agent_states[agent_id]
        history = agent_state["history"]
        if len(history) == 0:
            return {}
        initial_value = agent_state["initial_capital"]
        final_value = agent_state["portfolio_value"]
        total_return = (
            (final_value - initial_value) / initial_value if initial_value > 0 else 0.0
        )
        rewards = [h["reward"] for h in history]
        if len(rewards) > 1:
            sharpe_ratio = (
                np.mean(rewards) / (np.std(rewards) + 1e-8) * np.sqrt(252 * 6)
            )
        else:
            sharpe_ratio = 0.0
        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe_ratio,
            "cumulative_fees": agent_state["cumulative_fees"],
            "cumulative_turnover": agent_state["cumulative_turnover"],
            "final_portfolio_value": final_value,
        }

    def get_cache_stats(self) -> Dict[str, int]:
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses + 1e-8),
            "cache_size": len(self.market_impact_cache),
        }
