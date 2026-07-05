from datetime import date
from typing import List, Dict
import logging
from .base_strategy import BaseStrategy, StrategyResult
from app.config import config

logger = logging.getLogger(__name__)


class MomentumStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.period = config.MOMENTUM_PERIOD
        self.use_ewma = config.USE_EWMA
        self.ewma_alpha = config.EWMA_ALPHA

    def calculate(self, symbol_id: int, prices: List[Dict], trade_date: date) -> StrategyResult:
        result = StrategyResult()
        result.symbol_id = symbol_id
        result.trade_date = trade_date

        if len(prices) < self.period + 1:
            result.status = "insufficient_data"
            result.message = f"Need at least {self.period + 1} price points, got {len(prices)}"
            return result

        prices_sorted = sorted(prices, key=lambda x: x["trade_date"])
        latest_price = prices_sorted[-1]["close_price"]
        period_ago_price = prices_sorted[-(self.period + 1)]["close_price"]

        if period_ago_price == 0:
            result.status = "invalid_data"
            result.message = "Zero price in history"
            return result

        if self.use_ewma:
            momentum = self._calculate_ewma_momentum(prices_sorted)
        else:
            momentum = (latest_price - period_ago_price) / period_ago_price * 100

        result.momentum_20d = round(momentum, 4)
        result.trend_strength = self._evaluate_trend_strength(momentum)
        result.volume_confirmed, result.volume_change_pct = self._confirm_volume(prices_sorted)

        return result

    def rank(self, results: List[StrategyResult]) -> List[StrategyResult]:
        valid_results = [r for r in results if r.status == "valid"]
        valid_results.sort(key=lambda x: x.momentum_20d, reverse=True)

        for idx, result in enumerate(valid_results):
            result.ranking = idx + 1

        return valid_results

    def calculate_ranking_change(self, current_results: List[StrategyResult], previous_results: Dict[int, int]) -> List[StrategyResult]:
        for result in current_results:
            previous_rank = previous_results.get(result.symbol_id)
            if previous_rank is not None:
                result.ranking_change = previous_rank - result.ranking
            else:
                result.ranking_change = 0
        return current_results

    def _calculate_ewma_momentum(self, prices: List[Dict]) -> float:
        returns = []
        for i in range(1, len(prices)):
            prev_price = prices[i-1]["close_price"]
            curr_price = prices[i]["close_price"]
            if prev_price > 0:
                returns.append((curr_price - prev_price) / prev_price)

        if len(returns) == 0:
            return 0.0

        ewma = returns[-1]
        for i in range(len(returns)-2, -1, -1):
            ewma = self.ewma_alpha * returns[i] + (1 - self.ewma_alpha) * ewma

        return ewma * 100

    def _evaluate_trend_strength(self, momentum: float) -> str:
        if momentum >= 15:
            return "热"
        elif momentum >= 5:
            return "温"
        elif momentum >= 0:
            return "平"
        elif momentum >= -5:
            return "凉"
        else:
            return "寒"

    def calculate_consecutive_days(self, current_momentum: float,
                                    historical_momentums: List[float],
                                    current_date: date = None,
                                    historical_dates: List[date] = None) -> int:
        """计算当前趋势方向的连续交易日天数（含当天）。

        以0为分界线，从当前日期往前连续统计同方向动量的交易日天数。
        当提供了日期信息时，会验证交易日连续性——遇到数据断档
        （非相邻交易日）即停止计数，避免将不连续的数据误判为连续。

        Args:
            current_momentum: 当日动量值
            historical_momentums: 历史动量值列表（按日期升序）
            current_date: 当日日期（可选，用于交易日连续性验证）
            historical_dates: 历史日期列表（可选，与 historical_momentums 一一对应）

        Returns:
            连续同方向交易日天数（含当天）
        """
        from app.utils.date_utils import are_consecutive_trading_days

        current_direction = current_momentum > 0
        consecutive = 1  # 当天计入

        # 逆序遍历历史动量（从最近一天开始）
        for i in range(len(historical_momentums) - 1, -1, -1):
            prev_momentum = historical_momentums[i]
            prev_direction = prev_momentum > 0

            # 方向不一致则停止
            if prev_direction != current_direction:
                break

            # 如果提供了日期信息，验证交易日连续性
            if current_date is not None and historical_dates is not None:
                if i < len(historical_dates):
                    prev_date = historical_dates[i]
                    # 验证前一个日期是否是当前日期的前一个交易日
                    if not are_consecutive_trading_days(prev_date, current_date):
                        break  # 数据断档，停止计数
                    current_date = prev_date  # 向前推进

            consecutive += 1

        return consecutive

    def _confirm_volume(self, prices: List[Dict]) -> tuple:
        if len(prices) < 20:
            return 0, 0.0

        recent_volumes = [p.get("volume", 0) for p in prices[-5:]]
        earlier_volumes = [p.get("volume", 0) for p in prices[-20:-5]]

        avg_recent = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
        avg_earlier = sum(earlier_volumes) / len(earlier_volumes) if earlier_volumes else 0

        if avg_earlier == 0:
            return 0, 0.0

        volume_change = (avg_recent - avg_earlier) / avg_earlier * 100

        momentum = prices[-1]["close_price"] - prices[-(self.period + 1)]["close_price"]
        price_up = momentum > 0
        volume_up = volume_change > 0

        if price_up and volume_up:
            return 1, round(volume_change, 4)
        elif not price_up and not volume_up:
            return 1, round(volume_change, 4)
        else:
            return 0, round(volume_change, 4)
