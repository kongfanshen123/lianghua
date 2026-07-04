from typing import List, Dict
import math


def calculate_momentum(prices: List[Dict], period: int = 20) -> float:
    if len(prices) < period + 1:
        return 0.0

    prices_sorted = sorted(prices, key=lambda x: x["trade_date"])
    latest_price = prices_sorted[-1]["close_price"]
    period_ago_price = prices_sorted[-(period + 1)]["close_price"]

    if period_ago_price == 0:
        return 0.0

    return (latest_price - period_ago_price) / period_ago_price * 100


def calculate_ewma_momentum(prices: List[Dict], alpha: float = 0.1) -> float:
    prices_sorted = sorted(prices, key=lambda x: x["trade_date"])

    returns = []
    for i in range(1, len(prices_sorted)):
        prev_price = prices_sorted[i-1]["close_price"]
        curr_price = prices_sorted[i]["close_price"]
        if prev_price > 0:
            returns.append((curr_price - prev_price) / prev_price)

    if len(returns) == 0:
        return 0.0

    ewma = returns[-1]
    for i in range(len(returns)-2, -1, -1):
        ewma = alpha * returns[i] + (1 - alpha) * ewma

    return ewma * 100


def calculate_adjust_factor(daily_prices: List[Dict]) -> float:
    if len(daily_prices) < 2:
        return 1.0

    prices_sorted = sorted(daily_prices, key=lambda x: x["trade_date"])
    base_price = prices_sorted[0]["close_price"]
    latest_price = prices_sorted[-1]["close_price"]

    if base_price == 0:
        return 1.0

    return latest_price / base_price


def evaluate_trend_strength(momentum: float) -> str:
    if momentum >= 15:
        return "极强上涨"
    elif momentum >= 5:
        return "较强上涨"
    elif momentum >= 0:
        return "微弱上涨"
    elif momentum >= -5:
        return "微弱下跌"
    elif momentum >= -15:
        return "较强下跌"
    else:
        return "极强下跌"


def format_momentum(value: float) -> str:
    return f"{value:+.2f}%"


def format_ranking_change(change: int) -> str:
    if change > 0:
        return f"↑{change}"
    elif change < 0:
        return f"↓{abs(change)}"
    else:
        return "→"
