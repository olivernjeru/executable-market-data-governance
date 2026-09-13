# SIMULATED RESEARCH ARTIFACT -- NOT A TRADING SYSTEM.
"""
This code is not connected to, endorsed by, or representative of any exchange, broker, depository, regulator or trading venue, and it does not execute, route or settle orders. Nothing here is legal, financial, tax, accounting or investment advice. Fee, calendar, settlement and price-limit values are approximations compiled by the authors from public sources for academic use. They are NOT official data and have NOT been verified against the instruments they approximate. Do not rely on them for any real-world purpose. See README.md (Provenance and attribution) for what each class of value approximates.
"""

import pandas as pd
from typing import List, Optional
from datetime import time, timedelta
from collections import deque
import warnings

warnings.filterwarnings("ignore")


class TradingCalendar:
    """
    Simulated trading calendar with holiday tracking and settlement logic.
    """

    def __init__(self, start_year: int = 1997, end_year: int = 2026):
        self.start_year = start_year
        self.end_year = end_year
        self.market_open_time = time(9, 0)
        self.market_close_time = time(14, 0)
        self.settlement_days = 3
        self.holidays = self._generate_holidays()
        self.trading_days = self._generate_trading_days()

    def _generate_holidays(self) -> List[pd.Timestamp]:
        holidays = []
        for year in range(self.start_year, self.end_year + 1):
            holidays.extend(
                [
                    pd.Timestamp(f"{year}-01-01"),
                    pd.Timestamp(f"{year}-05-01"),
                    pd.Timestamp(f"{year}-06-01"),
                    pd.Timestamp(f"{year}-10-20"),
                    pd.Timestamp(f"{year}-12-12"),
                    pd.Timestamp(f"{year}-12-25"),
                    pd.Timestamp(f"{year}-12-26"),
                ]
            )
        adjusted_holidays = []
        for holiday in holidays:
            if holiday.weekday() == 5:
                adjusted_holidays.append(holiday + timedelta(days=2))
            elif holiday.weekday() == 6:
                adjusted_holidays.append(holiday + timedelta(days=1))
            else:
                adjusted_holidays.append(holiday)
        return sorted(list(set(adjusted_holidays)))

    def _generate_trading_days(self) -> pd.DatetimeIndex:
        all_days = pd.bdate_range(
            start=f"{self.start_year}-01-01", end=f"{self.end_year}-12-31"
        )
        trading_days = [day for day in all_days if day not in self.holidays]
        return pd.DatetimeIndex(trading_days)

    def is_trading_day(self, date: pd.Timestamp) -> bool:
        date_only = pd.Timestamp(date.date())
        if date_only.weekday() >= 5:
            return False
        if date_only in self.holidays:
            return False
        return True

    def is_market_open(self, timestamp: pd.Timestamp) -> bool:
        if not self.is_trading_day(timestamp):
            return False
        current_time = timestamp.time()
        if (
            current_time < self.market_open_time
            or current_time >= self.market_close_time
        ):
            return False
        return True

    def get_trading_hour(self, timestamp: pd.Timestamp) -> Optional[int]:
        if not self.is_market_open(timestamp):
            return None
        return timestamp.hour

    def get_next_trading_day(self, date: pd.Timestamp) -> pd.Timestamp:
        date_only = pd.Timestamp(date.date())
        next_day = date_only + timedelta(days=1)
        while not self.is_trading_day(next_day):
            next_day += timedelta(days=1)
        return next_day

    def get_settlement_date(self, trade_date: pd.Timestamp) -> pd.Timestamp:
        current_date = pd.Timestamp(trade_date.date())
        trading_days_counted = 0
        while trading_days_counted < self.settlement_days:
            current_date = self.get_next_trading_day(current_date)
            trading_days_counted += 1
        return current_date

    def get_trading_days_between(
        self, start_date: pd.Timestamp, end_date: pd.Timestamp
    ) -> int:
        start = pd.Timestamp(start_date.date())
        end = pd.Timestamp(end_date.date())
        count = 0
        current = start
        while current <= end:
            if self.is_trading_day(current):
                count += 1
            current += timedelta(days=1)
        return count


class T3SettlementQueue:
    def __init__(self, calendar: TradingCalendar):
        self.calendar = calendar
        self.pending_settlements = deque()
        self.total_trades = 0
        self.total_settled = 0

    def add_trade(
        self,
        trade_date: pd.Timestamp,
        ticker: str,
        shares: float,
        price: float,
        side: str,
        fees: float,
    ):
        settlement_date = self.calendar.get_settlement_date(trade_date)
        trade_value = shares * price
        cash_impact = -(trade_value + fees) if side == "buy" else (trade_value - fees)
        trade_details = {
            "trade_date": trade_date,
            "settlement_date": settlement_date,
            "ticker": ticker,
            "shares": shares,
            "price": price,
            "side": side,
            "fees": fees,
            "cash_impact": cash_impact,
        }
        self.pending_settlements.append(trade_details)
        self.total_trades += 1

    def settle_due_trades(self, current_date: pd.Timestamp) -> float:
        total_cash_change = 0.0
        while self.pending_settlements:
            trade = self.pending_settlements[0]
            if trade["settlement_date"] <= current_date:
                self.pending_settlements.popleft()
                total_cash_change += trade["cash_impact"]
                self.total_settled += 1
            else:
                break
        return total_cash_change

    def get_statistics(self):
        return {
            "total_trades": self.total_trades,
            "total_settled": self.total_settled,
            "pending_settlements": len(self.pending_settlements),
            "pending_cash_impact": sum(
                trade["cash_impact"] for trade in self.pending_settlements
            ),
        }


def create_trading_calendar(
    start_year: int = 1997, end_year: int = 2026
) -> TradingCalendar:
    return TradingCalendar(start_year=start_year, end_year=end_year)


def create_settlement_queue(calendar: TradingCalendar) -> T3SettlementQueue:
    return T3SettlementQueue(calendar=calendar)
