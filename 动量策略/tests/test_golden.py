import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.strategies.momentum_strategy import MomentumStrategy
from app.config import config

BASE_DIR = Path(__file__).parent / "golden"
DATA_DIR = BASE_DIR / "data"
BASELINE_DIR = BASE_DIR / "baselines"
CURRENT_DIR = BASE_DIR / "current"

BASELINE_DATA = {
    "test_normal_momentum": {
        "momentum_20d": 6.1813,
        "trend_strength": "温",
        "volume_confirmed": 1,
        "volume_change_pct": 8.547,
        "status": "valid",
        "message": "",
    },
    "test_strong_upward": {
        "momentum_20d": 12.7073,
        "trend_strength": "温",
        "volume_confirmed": 1,
        "volume_change_pct": 8.547,
        "status": "valid",
        "message": "",
    },
    "test_strong_downward": {
        "momentum_20d": -11.3375,
        "trend_strength": "寒",
        "volume_confirmed": 0,
        "volume_change_pct": 8.547,
        "status": "valid",
        "message": "",
    },
    "test_insufficient_data": {
        "momentum_20d": 0.0,
        "trend_strength": "",
        "volume_confirmed": 0,
        "volume_change_pct": 0.0,
        "status": "insufficient_data",
        "message": "Need at least 21 price points, got 10",
    },
    "test_zero_price": {
        "momentum_20d": 22.017,
        "trend_strength": "热",
        "volume_confirmed": 1,
        "volume_change_pct": 8.547,
        "status": "valid",
        "message": "",
    },
    "test_volume_divergence": {
        "momentum_20d": 6.1813,
        "trend_strength": "温",
        "volume_confirmed": 0,
        "volume_change_pct": -45.7265,
        "status": "valid",
        "message": "",
    },
}


def setup_directories():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)


def generate_test_data(name: str, data: List[Dict]):
    data_path = DATA_DIR / f"{name}.json"
    with open(data_path, "w") as f:
        json.dump(data, f, indent=2)
    return data_path


def generate_baseline(name: str, result: Dict):
    baseline_path = BASELINE_DIR / f"{name}.json"
    with open(baseline_path, "w") as f:
        json.dump(result, f, indent=2)


def compare_results(name: str, current: Dict) -> List[str]:
    baseline = BASELINE_DATA.get(name, {})
    errors = []

    for key in baseline:
        if key not in current:
            errors.append(f"Missing key: {key}")
            continue
        if current[key] != baseline[key]:
            errors.append(f"Mismatch {key}: expected {baseline[key]}, got {current[key]}")

    return errors


def generate_prices(start_date: date, days: int, start_price: float, daily_change: float = 0.01):
    prices = []
    current_price = start_price
    for i in range(days):
        trade_date = start_date + timedelta(days=i)
        prices.append({
            "trade_date": trade_date.isoformat(),
            "close_price": round(current_price, 2),
            "volume": 1000000 + i * 10000,
        })
        current_price *= (1 + daily_change)
    return prices


def run_test(name: str, prices: List[Dict], generate_baseline_flag: bool = False) -> List[str]:
    print(f"Running Golden Test: {name}...")
    
    strategy = MomentumStrategy()
    result = strategy.calculate(symbol_id=1, prices=prices, trade_date=date.today())
    
    result_dict = {
        "momentum_20d": result.momentum_20d,
        "trend_strength": result.trend_strength,
        "volume_confirmed": result.volume_confirmed,
        "volume_change_pct": result.volume_change_pct,
        "status": result.status,
        "message": result.message,
    }
    
    if generate_baseline_flag:
        generate_baseline(name, result_dict)
        print(f"Baseline generated for {name}")
        return []
    else:
        errors = compare_results(name, result_dict)
        if errors:
            print(f"FAILED: {name}")
            for err in errors:
                print(f"  - {err}")
            return errors
        else:
            print(f"PASSED: {name}")
            return []


def test_normal_momentum():
    setup_directories()
    prices = generate_prices(date(2025, 1, 1), 30, 100.0, 0.003)
    errors = run_test("test_normal_momentum", prices)
    assert not errors, f"Golden Test Failed: {errors}"


def test_strong_upward():
    setup_directories()
    prices = generate_prices(date(2025, 1, 1), 30, 100.0, 0.006)
    errors = run_test("test_strong_upward", prices)
    assert not errors, f"Golden Test Failed: {errors}"


def test_strong_downward():
    setup_directories()
    prices = generate_prices(date(2025, 1, 1), 30, 100.0, -0.006)
    errors = run_test("test_strong_downward", prices)
    assert not errors, f"Golden Test Failed: {errors}"


def test_insufficient_data():
    setup_directories()
    prices = generate_prices(date(2025, 1, 1), 10, 100.0)
    errors = run_test("test_insufficient_data", prices)
    assert not errors, f"Golden Test Failed: {errors}"


def test_zero_price():
    setup_directories()
    prices = generate_prices(date(2025, 1, 1), 30, 100.0)
    prices[0]["close_price"] = 0.0
    errors = run_test("test_zero_price", prices)
    assert not errors, f"Golden Test Failed: {errors}"


def test_volume_divergence():
    setup_directories()
    prices = generate_prices(date(2025, 1, 1), 30, 100.0, 0.003)
    for i in range(len(prices) - 5, len(prices)):
        prices[i]["volume"] = prices[i]["volume"] // 2
    errors = run_test("test_volume_divergence", prices)
    assert not errors, f"Golden Test Failed: {errors}"


def test_ranking():
    from app.strategies.base_strategy import StrategyResult
    
    r1 = StrategyResult()
    r1.symbol_id = 1
    r1.momentum_20d = 15.0
    r1.status = "valid"
    
    r2 = StrategyResult()
    r2.symbol_id = 2
    r2.momentum_20d = 5.0
    r2.status = "valid"
    
    r3 = StrategyResult()
    r3.symbol_id = 3
    r3.momentum_20d = 20.0
    r3.status = "valid"
    
    r4 = StrategyResult()
    r4.symbol_id = 4
    r4.momentum_20d = None
    r4.status = "insufficient_data"
    
    results = [r1, r2, r3, r4]
    
    strategy = MomentumStrategy()
    ranked = strategy.rank(results)
    
    assert len(ranked) == 3, f"Expected 3 valid results, got {len(ranked)}"
    assert ranked[0].symbol_id == 3, f"Expected symbol 3 first, got {ranked[0].symbol_id}"
    assert ranked[0].ranking == 1, f"Expected rank 1, got {ranked[0].ranking}"
    assert ranked[1].symbol_id == 1, f"Expected symbol 1 second, got {ranked[1].symbol_id}"
    assert ranked[2].symbol_id == 2, f"Expected symbol 2 third, got {ranked[2].symbol_id}"
    
    print("PASSED: test_ranking")


if __name__ == "__main__":
    setup_directories()
    
    prices_normal = generate_prices(date(2025, 1, 1), 30, 100.0, 0.003)
    prices_strong_up = generate_prices(date(2025, 1, 1), 30, 100.0, 0.006)
    prices_strong_down = generate_prices(date(2025, 1, 1), 30, 100.0, -0.006)
    prices_insufficient = generate_prices(date(2025, 1, 1), 10, 100.0)
    prices_zero = generate_prices(date(2025, 1, 1), 30, 100.0)
    prices_zero[0]["close_price"] = 0.0
    prices_divergence = generate_prices(date(2025, 1, 1), 30, 100.0, 0.003)
    for i in range(len(prices_divergence) - 5, len(prices_divergence)):
        prices_divergence[i]["volume"] = prices_divergence[i]["volume"] // 2
    
    generate_test_data("test_normal_momentum", prices_normal)
    generate_test_data("test_strong_upward", prices_strong_up)
    generate_test_data("test_strong_downward", prices_strong_down)
    generate_test_data("test_insufficient_data", prices_insufficient)
    generate_test_data("test_zero_price", prices_zero)
    generate_test_data("test_volume_divergence", prices_divergence)
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-baseline", action="store_true")
    args = parser.parse_args()
    
    failures = []
    
    errs = run_test("test_normal_momentum", prices_normal, args.generate_baseline)
    failures.extend(errs)
    
    errs = run_test("test_strong_upward", prices_strong_up, args.generate_baseline)
    failures.extend(errs)
    
    errs = run_test("test_strong_downward", prices_strong_down, args.generate_baseline)
    failures.extend(errs)
    
    errs = run_test("test_insufficient_data", prices_insufficient, args.generate_baseline)
    failures.extend(errs)
    
    errs = run_test("test_zero_price", prices_zero, args.generate_baseline)
    failures.extend(errs)
    
    errs = run_test("test_volume_divergence", prices_divergence, args.generate_baseline)
    failures.extend(errs)
    
    test_ranking()
    
    if failures:
        print(f"\nGolden Suite FAILED: {failures}")
        exit(1)
    else:
        print("\nGolden Suite PASSED")
        exit(0)