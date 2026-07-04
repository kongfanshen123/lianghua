import math
from datetime import date
from typing import List, Dict
import logging
from .base_strategy import BaseStrategy, StrategyResult
from app.config import config

logger = logging.getLogger(__name__)


class WeightedScoreStrategy(BaseStrategy):
    """加权动量评分策略。

    核心思路:
    1. 取对数价格消除复利影响
    2. 线性递增权重（近期权重更高）
    3. 加权线性回归拟合趋势斜率
    4. R²衡量趋势稳定性
    5. 评分 = 年化收益率 × R²

    交易规则:
    - 评分 > 0 且 ≤ 5（安全区间）的标的可入选
    - 取评分排名第一的标的
    - 所有标的评分 ≤ 0 或 > 5 → 空仓
    """

    def __init__(self):
        super().__init__()
        self.name = "weighted_score"
        self.period = 25  # 默认25个交易日（约一个月）
        self.trading_days_per_year = 252  # 年化天数

    def calculate(self, symbol_id: int, prices: List[Dict], trade_date: date) -> StrategyResult:
        result = StrategyResult()
        result.symbol_id = symbol_id
        result.trade_date = trade_date

        if len(prices) < self.period + 1:
            result.status = "insufficient_data"
            result.message = f"Need at least {self.period + 1} price points, got {len(prices)}"
            return result

        prices_sorted = sorted(prices, key=lambda x: x["trade_date"])

        # 取最近 period+1 个价格点
        window = prices_sorted[-(self.period + 1):]

        # 检查价格有效性
        close_prices = [p["close_price"] for p in window]
        if any(p <= 0 for p in close_prices):
            result.status = "invalid_data"
            result.message = "Non-positive price found in window"
            return result

        # Step 1: 对数价格
        log_prices = [math.log(p) for p in close_prices]
        n = len(log_prices)

        # Step 2: 线性递增权重 (第1天权重1, 最后一天权重2)
        weights = [1.0 + (i / (n - 1)) for i in range(n)]

        # Step 3: 加权线性回归
        slope, intercept, r_squared = self._weighted_linear_regression(log_prices, weights)

        if slope is None:
            result.status = "invalid_data"
            result.message = "Regression failed"
            return result

        # Step 4: 计算年化收益率
        # slope 是对数价格的日变化率，年化 = slope * 252 * 100 (百分比)
        annualized_return = slope * self.trading_days_per_year * 100

        # Step 5: 评分 = 年化收益 × R²
        score = annualized_return * r_squared

        result.momentum_20d = round(score, 4)
        result.volume_confirmed = self._check_volume(prices_sorted)
        result.volume_change_pct = self._volume_change_pct(prices_sorted)
        result.trend_strength = self._evaluate_trend_strength(score)
        result.status = "valid"

        return result

    def rank(self, results: List[StrategyResult]) -> List[StrategyResult]:
        """按评分降序排名，只排名有效结果。"""
        valid_results = [r for r in results if r.status == "valid"]
        valid_results.sort(key=lambda x: x.momentum_20d, reverse=True)

        for idx, result in enumerate(valid_results):
            result.ranking = idx + 1

        return valid_results

    def calculate_ranking_change(self, current_results: List[StrategyResult],
                                  previous_results: Dict[int, int]) -> List[StrategyResult]:
        for result in current_results:
            previous_rank = previous_results.get(result.symbol_id)
            if previous_rank is not None:
                result.ranking_change = previous_rank - result.ranking
            else:
                result.ranking_change = 0
        return current_results

    def _weighted_linear_regression(self, y: List[float], weights: List[float]):
        """加权线性回归，返回 (slope, intercept, r_squared)。"""
        n = len(y)
        x = list(range(n))

        w_sum = sum(weights)
        wx_sum = sum(weights[i] * x[i] for i in range(n))
        wy_sum = sum(weights[i] * y[i] for i in range(n))
        wxx_sum = sum(weights[i] * x[i] * x[i] for i in range(n))
        wxy_sum = sum(weights[i] * x[i] * y[i] for i in range(n))

        denom = w_sum * wxx_sum - wx_sum * wx_sum
        if abs(denom) < 1e-12:
            return None, None, 0.0

        slope = (w_sum * wxy_sum - wx_sum * wy_sum) / denom
        intercept = (wy_sum - slope * wx_sum) / w_sum

        # 计算 R²
        y_mean = wy_sum / w_sum
        ss_tot = sum(weights[i] * (y[i] - y_mean) ** 2 for i in range(n))
        ss_res = sum(weights[i] * (y[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))

        if ss_tot < 1e-12:
            r_squared = 0.0
        else:
            r_squared = 1.0 - (ss_res / ss_tot)
            r_squared = max(0.0, min(1.0, r_squared))  # 限制在 [0, 1]

        return slope, intercept, r_squared

    def _evaluate_trend_strength(self, score: float) -> str:
        """温度计体系评估趋势强度。"""
        if score >= 15:
            return "热"
        elif score >= 5:
            return "温"
        elif score > 0:
            return "平"
        elif score >= -5:
            return "凉"
        else:
            return "寒"

    def _check_volume(self, prices: List[Dict]) -> int:
        """成交量确认: 近5日均量 vs 前15日均量。"""
        if len(prices) < 20:
            return 0

        recent_volumes = [p.get("volume", 0) for p in prices[-5:]]
        earlier_volumes = [p.get("volume", 0) for p in prices[-20:-5]]

        avg_recent = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
        avg_earlier = sum(earlier_volumes) / len(earlier_volumes) if earlier_volumes else 0

        if avg_earlier == 0:
            return 0

        return 1 if avg_recent > avg_earlier else 0

    def _volume_change_pct(self, prices: List[Dict]) -> float:
        """成交量变化百分比。"""
        if len(prices) < 20:
            return 0.0

        recent_volumes = [p.get("volume", 0) for p in prices[-5:]]
        earlier_volumes = [p.get("volume", 0) for p in prices[-20:-5]]

        avg_recent = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
        avg_earlier = sum(earlier_volumes) / len(earlier_volumes) if earlier_volumes else 0

        if avg_earlier == 0:
            return 0.0

        return round((avg_recent - avg_earlier) / avg_earlier * 100, 4)
