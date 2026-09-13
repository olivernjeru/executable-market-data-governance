# SIMULATED RESEARCH ARTIFACT -- NOT A TRADING SYSTEM.
"""
  This code is not connected to, endorsed by, or representative of any exchange, broker, depository, regulator or trading venue, and it does not execute, route or settle orders. Nothing here is legal, financial, tax, accounting or investment advice. Fee, calendar, settlement and price-limit values are approximations compiled by the authors from public sources for academic use. They are NOT official data and have NOT been verified against the instruments they approximate. Do not rely on them for any real-world purpose. See README.md (Provenance and attribution) for what each class of value approximates.

Enhanced Feature Engineering for Phase 4 Intraday DRL Training
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import warnings

warnings.filterwarnings("ignore")


class IntradayFeatureEngineer:
    """
    Enhanced feature engineer for intraday (hourly) DRL training.
    """

    def __init__(
        self,
        intraday_prices: pd.DataFrame,
        daily_prices: Optional[pd.DataFrame] = None,
        liquidity_tiers: Optional[pd.DataFrame] = None,
        rolling_window: int = 252,
        trading_hours: Optional[List[int]] = None,
    ):
        """
        Initialize intraday feature engineer.
        """
        self.intraday_prices = intraday_prices
        self.daily_prices = daily_prices
        self.liquidity_tiers = liquidity_tiers
        self.rolling_window = rolling_window
        self.trading_hours = trading_hours or [9, 10, 11, 12, 13, 14]
        self.num_hours_per_day = len(self.trading_hours)

        # Compute intraday returns
        self.intraday_returns = self.intraday_prices.pct_change()
        self.intraday_log_returns = np.log(
            self.intraday_prices / self.intraday_prices.shift(1)
        )

        # Compute daily returns (if daily prices provided)
        if self.daily_prices is not None:
            self.daily_returns = self.daily_prices.pct_change()
            self.daily_log_returns = np.log(
                self.daily_prices / self.daily_prices.shift(1)
            )
        else:
            self.daily_returns = None
            self.daily_log_returns = None

        # Liquidity map
        self.liquidity_map = self._compute_liquidity_percentiles()

        # Feature cache (performance optimization)
        self._feature_cache = {}
        self._standardization_cache = {}

    def _compute_liquidity_percentiles(self) -> Dict[str, float]:
        """Map tickers to liquidity percentiles based on tiers."""
        if self.liquidity_tiers is None or len(self.liquidity_tiers) == 0:
            # Default: all assets equal liquidity
            tickers = self.intraday_prices.columns
            return {ticker: 0.5 for ticker in tickers}

        # Map TIER_1/2/3 to percentiles
        tier_to_percentile = {
            "TIER_1_HIGHLY_LIQUID": 1.0,
            "TIER_2_LIQUID": 0.5,
            "TIER_3_MODERATE": 0.0,
        }

        liquidity_map = {}
        for _, row in self.liquidity_tiers.iterrows():
            ticker = row["ticker"]
            tier = row["tier"]
            liquidity_map[ticker] = tier_to_percentile.get(tier, 0.5)

        # Fill missing tickers with median
        for ticker in self.intraday_prices.columns:
            if ticker not in liquidity_map:
                liquidity_map[ticker] = 0.5

        return liquidity_map

    def compute_intraday_features(
        self, date: pd.Timestamp, hour: int, ticker: str
    ) -> Dict[str, float]:
        """
        Compute intraday features for a specific ticker at a given date/hour.
        """
        features = {}

        if ticker not in self.intraday_prices.columns:
            # Missing ticker: return zero features
            return {
                "time_of_day": 0.0,
                "hours_to_close": 0.0,
                "intraday_volatility": 0.0,
                "volume_profile_position": 0.0,
                "cumulative_return_today": 0.0,
                "current_price_vs_open": 0.0,
                "high_low_range_today": 0.0,
            }

        # Time-of-day features
        hour_index = self.trading_hours.index(hour) if hour in self.trading_hours else 0
        features["time_of_day"] = hour_index / (
            self.num_hours_per_day - 1
        )  # Normalize to [0, 1]
        features["hours_to_close"] = (self.num_hours_per_day - 1 - hour_index) / (
            self.num_hours_per_day - 1
        )

        # Get today's bars up to current hour
        try:
            today_mask = self.intraday_prices.index.get_level_values(0) == date
            today_bars = self.intraday_prices.loc[today_mask, ticker]
            today_hours = self.intraday_prices.index.get_level_values(1)[today_mask]

            # Filter to bars up to current hour
            current_hour_mask = today_hours <= hour
            bars_so_far = today_bars[current_hour_mask]

            if len(bars_so_far) == 0:
                # No bars yet today
                features["intraday_volatility"] = 0.0
                features["cumulative_return_today"] = 0.0
                features["current_price_vs_open"] = 0.0
                features["high_low_range_today"] = 0.0
            else:
                # Intraday volatility (returns so far today, annualized)
                if len(bars_so_far) > 1:
                    returns_today = bars_so_far.pct_change().dropna()
                    if len(returns_today) > 0:
                        # Annualize: std * sqrt(252 days * 6 hours/day)
                        vol = returns_today.std() * np.sqrt(
                            252 * self.num_hours_per_day
                        )
                        features["intraday_volatility"] = (
                            vol if not np.isnan(vol) else 0.0
                        )
                    else:
                        features["intraday_volatility"] = 0.0
                else:
                    features["intraday_volatility"] = 0.0

                # Cumulative return today (open to now)
                open_price = bars_so_far.iloc[0]
                current_price = bars_so_far.iloc[-1]
                if (
                    open_price > 0
                    and not np.isnan(open_price)
                    and not np.isnan(current_price)
                ):
                    cum_return = (current_price - open_price) / open_price
                    features["cumulative_return_today"] = (
                        cum_return if not np.isnan(cum_return) else 0.0
                    )
                    features["current_price_vs_open"] = (
                        cum_return if not np.isnan(cum_return) else 0.0
                    )
                else:
                    features["cumulative_return_today"] = 0.0
                    features["current_price_vs_open"] = 0.0

                # High-low range today
                high_today = bars_so_far.max()
                low_today = bars_so_far.min()
                if (
                    open_price > 0
                    and not np.isnan(open_price)
                    and not np.isnan(high_today)
                    and not np.isnan(low_today)
                ):
                    range_pct = (high_today - low_today) / open_price
                    features["high_low_range_today"] = (
                        range_pct if not np.isnan(range_pct) else 0.0
                    )
                else:
                    features["high_low_range_today"] = 0.0

        except (KeyError, IndexError):
            # Data not available
            features["intraday_volatility"] = 0.0
            features["cumulative_return_today"] = 0.0
            features["current_price_vs_open"] = 0.0
            features["high_low_range_today"] = 0.0

        # Volume profile position (expected % of daily volume by this hour)
        volume_profile = [0.25, 0.15, 0.10, 0.10, 0.15, 0.25]
        cumulative_volume_pct = sum(volume_profile[: hour_index + 1])
        features["volume_profile_position"] = cumulative_volume_pct

        return features

    def compute_daily_features(
        self, date: pd.Timestamp, ticker: str
    ) -> Dict[str, float]:
        """
        Compute daily features for a specific ticker.
        """
        features = {}

        if self.daily_prices is None or ticker not in self.daily_prices.columns:
            # No daily prices: return zero features
            return {
                "ret_1d": 0.0,
                "ret_5d": 0.0,
                "ret_21d": 0.0,
                "vol_21d": 0.0,
                "mom_63d": 0.0,
                "mom_126d": 0.0,
                "liquidity": self.liquidity_map.get(ticker, 0.5),
            }

        # Get historical window up to date
        hist_prices = self.daily_prices.loc[:date, ticker]
        hist_returns = self.daily_log_returns.loc[:date, ticker]

        if len(hist_prices) < 126:
            # Insufficient history: return zero features
            return {
                "ret_1d": 0.0,
                "ret_5d": 0.0,
                "ret_21d": 0.0,
                "vol_21d": 0.0,
                "mom_63d": 0.0,
                "mom_126d": 0.0,
                "liquidity": self.liquidity_map.get(ticker, 0.5),
            }

        # 1-day log return
        ret_1d = hist_returns.iloc[-1] if len(hist_returns) > 0 else 0.0
        features["ret_1d"] = ret_1d if not np.isnan(ret_1d) else 0.0

        # 5-day log return
        if len(hist_returns) >= 5:
            ret_5d = np.sum(hist_returns.iloc[-5:])
            features["ret_5d"] = ret_5d if not np.isnan(ret_5d) else 0.0
        else:
            features["ret_5d"] = 0.0

        # 21-day log return
        if len(hist_returns) >= 21:
            ret_21d = np.sum(hist_returns.iloc[-21:])
            features["ret_21d"] = ret_21d if not np.isnan(ret_21d) else 0.0
        else:
            features["ret_21d"] = 0.0

        # 21-day realized volatility (annualized)
        if len(hist_returns) >= 21:
            vol = hist_returns.iloc[-21:].std() * np.sqrt(252)
            features["vol_21d"] = vol if not np.isnan(vol) else 0.0
        else:
            features["vol_21d"] = 0.0

        # 63-day momentum
        if len(hist_prices) >= 63:
            mom_63 = (hist_prices.iloc[-1] / hist_prices.iloc[-63]) - 1.0
            features["mom_63d"] = mom_63 if not np.isnan(mom_63) else 0.0
        else:
            features["mom_63d"] = 0.0

        # 126-day momentum
        if len(hist_prices) >= 126:
            mom_126 = (hist_prices.iloc[-1] / hist_prices.iloc[-126]) - 1.0
            features["mom_126d"] = mom_126 if not np.isnan(mom_126) else 0.0
        else:
            features["mom_126d"] = 0.0

        # Liquidity percentile (static)
        features["liquidity"] = self.liquidity_map.get(ticker, 0.5)

        return features

    def get_state_vector(
        self,
        date: pd.Timestamp,
        tickers: List[str],
        hour: Optional[int] = None,
        standardize: bool = True,
    ) -> np.ndarray:
        """
        Get state vector for all tickers at a given date/hour.
        """
        # Determine hour (if not provided, use end of day)
        if hour is None:
            hour = self.trading_hours[-1]  # Default to last hour (2 PM)

        all_features = []

        for ticker in tickers:
            # Compute intraday features
            intraday_feat = self.compute_intraday_features(date, hour, ticker)

            # Compute daily features
            daily_feat = self.compute_daily_features(date, ticker)

            # Combine features
            combined_feat = {**intraday_feat, **daily_feat}

            # Convert to ordered list
            feature_values = [
                combined_feat["time_of_day"],
                combined_feat["hours_to_close"],
                combined_feat["intraday_volatility"],
                combined_feat["volume_profile_position"],
                combined_feat["cumulative_return_today"],
                combined_feat["current_price_vs_open"],
                combined_feat["high_low_range_today"],
                combined_feat["ret_1d"],
                combined_feat["ret_5d"],
                combined_feat["ret_21d"],
                combined_feat["vol_21d"],
                combined_feat["mom_63d"],
                combined_feat["mom_126d"],
                combined_feat["liquidity"],
            ]

            # Replace any NaN values with 0.0 (safety check)
            feature_values = [0.0 if np.isnan(val) else val for val in feature_values]

            # Standardize (z-score) if requested
            if standardize:
                feature_values = self._standardize_features(
                    date, ticker, feature_values
                )

            all_features.extend(feature_values)

        state_vector = np.array(all_features)

        # Final safety check: replace any remaining NaN values with 0.0
        if np.isnan(state_vector).any():
            state_vector = np.nan_to_num(state_vector, nan=0.0, posinf=0.0, neginf=0.0)

        return state_vector

    def _standardize_features(
        self, date: pd.Timestamp, ticker: str, features: List[float]
    ) -> List[float]:
        """
        Standardize features using rolling window statistics.
        """
        standardized = []
        for feat_val in features:
            # Handle NaN values
            if np.isnan(feat_val):
                feat_val = 0.0

            # Clip to reasonable range
            clipped = np.clip(feat_val, -3.0, 3.0)
            # Normalize to [-1, 1]
            normalized = clipped / 3.0
            standardized.append(normalized)

        return standardized

    def get_feature_names(self) -> List[str]:
        """Get ordered list of feature names."""
        return [
            "time_of_day",
            "hours_to_close",
            "intraday_volatility",
            "volume_profile_position",
            "cumulative_return_today",
            "current_price_vs_open",
            "high_low_range_today",
            "ret_1d",
            "ret_5d",
            "ret_21d",
            "vol_21d",
            "mom_63d",
            "mom_126d",
            "liquidity",
        ]

    def get_num_features_per_ticker(self) -> int:
        """Get number of features per ticker."""
        return len(self.get_feature_names())


def create_feature_engineer(
    intraday_prices: pd.DataFrame,
    daily_prices: Optional[pd.DataFrame] = None,
    liquidity_tiers: Optional[pd.DataFrame] = None,
    **kwargs
) -> IntradayFeatureEngineer:
    """
    Create IntradayFeatureEngineer instance.
    """
    return IntradayFeatureEngineer(
        intraday_prices=intraday_prices,
        daily_prices=daily_prices,
        liquidity_tiers=liquidity_tiers,
        **kwargs
    )
