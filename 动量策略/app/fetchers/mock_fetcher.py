from datetime import date, timedelta
from typing import List, Dict, Optional
import random
from .base_fetcher import BaseFetcher, FetcherResult


class MockFetcher(BaseFetcher):
    def __init__(self):
        super().__init__(request_interval=0, max_retry=1, retry_delay=0)
        self.data_source = "mock"
        self.price_cache = {}

    def fetch_daily_price(self, symbol: str, trade_date: Optional[date] = None) -> FetcherResult:
        result = FetcherResult()
        result.data_source = self.data_source

        if trade_date is None:
            trade_date = date.today()

        if symbol not in self.price_cache:
            self._initialize_cache(symbol)

        price = self._generate_price(symbol, trade_date)
        result.data = [{
            "trade_date": trade_date.strftime("%Y-%m-%d"),
            "close_price": price,
            "open_price": price * random.uniform(0.99, 1.01),
            "high_price": price * random.uniform(1.00, 1.02),
            "low_price": price * random.uniform(0.98, 1.00),
            "volume": random.randint(1000000, 10000000),
            "amount": price * random.randint(1000000, 10000000),
            "adjusted_factor": 1.0,
            "is_suspended": 0,
            "is_ex_dividend": 0,
        }]
        result.success = True
        return result

    def fetch_price_history(self, symbol: str, start_date: date, end_date: date) -> FetcherResult:
        result = FetcherResult()
        result.data_source = self.data_source

        if symbol not in self.price_cache:
            self._initialize_cache(symbol)

        data = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:
                price = self._generate_price(symbol, current_date)
                data.append({
                    "trade_date": current_date.strftime("%Y-%m-%d"),
                    "close_price": price,
                    "open_price": price * random.uniform(0.99, 1.01),
                    "high_price": price * random.uniform(1.00, 1.02),
                    "low_price": price * random.uniform(0.98, 1.00),
                    "volume": random.randint(1000000, 10000000),
                    "amount": price * random.randint(1000000, 10000000),
                    "adjusted_factor": 1.0,
                    "is_suspended": 0,
                    "is_ex_dividend": 0,
                })
            current_date += timedelta(days=1)

        result.data = data
        result.success = True
        return result

    def _initialize_cache(self, symbol: str):
        base_price = random.uniform(10, 500)
        self.price_cache[symbol] = {
            "base_price": base_price,
            "trend": random.uniform(-0.02, 0.02),
            "volatility": random.uniform(0.01, 0.03),
        }

    def _generate_price(self, symbol: str, trade_date: date) -> float:
        cache = self.price_cache[symbol]
        days_since_epoch = (trade_date - date(2024, 1, 1)).days
        price = cache["base_price"] * (1 + cache["trend"]) ** (days_since_epoch / 20)
        price *= (1 + random.uniform(-cache["volatility"], cache["volatility"]))
        return round(price, 2)
