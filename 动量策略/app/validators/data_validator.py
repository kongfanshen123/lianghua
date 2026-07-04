from typing import Dict, List
import logging
from .base_validator import BaseValidator, ValidationResult
from app.config import config

logger = logging.getLogger(__name__)


class DataValidator(BaseValidator):
    def __init__(self):
        super().__init__()
        self.price_change_threshold = config.PRICE_CHANGE_THRESHOLD
        self.min_volume_20d = config.MIN_VOLUME_20D
        self.min_volume_amount = config.MIN_VOLUME_AMOUNT

    def validate(self, data: Dict) -> ValidationResult:
        result = ValidationResult()

        required_fields = ["trade_date", "close_price"]
        for field in required_fields:
            if field not in data or data[field] is None:
                result.valid = False
                result.status = "missing_field"
                result.message = f"Missing required field: {field}"
                return result

        if data["close_price"] <= 0:
            result.valid = False
            result.status = "invalid_price"
            result.message = f"Invalid close price: {data['close_price']}"
            return result

        if data.get("is_suspended", 0) == 1:
            result.valid = False
            result.status = "suspended"
            result.message = "Stock is suspended"
            return result

        if data.get("volume", 0) == 0:
            result.valid = False
            result.status = "zero_volume"
            result.message = "Zero volume"
            return result

        if data.get("open_price") and data["open_price"] > 0:
            price_change = abs((data["close_price"] - data["open_price"]) / data["open_price"]) * 100
            if price_change > self.price_change_threshold:
                result.valid = False
                result.status = "price_anomaly"
                result.message = f"Price change {price_change:.2f}% exceeds threshold {self.price_change_threshold}%"
                return result

        result.valid = True
        result.status = "valid"
        result.message = "Validation passed"
        return result

    def validate_with_history(self, current_data: Dict, history_data: List[Dict]) -> ValidationResult:
        result = self.validate(current_data)
        if not result.valid:
            return result

        # 日间价格跳变校验：与前一日收盘价对比
        if history_data:
            prev_close = history_data[-1].get("close_price", 0)
            current_close = current_data.get("close_price", 0)
            if prev_close and prev_close > 0 and current_close > 0:
                day_change_pct = abs((current_close - prev_close) / prev_close) * 100
                if day_change_pct > self.price_change_threshold:
                    result.valid = False
                    result.status = "interday_price_anomaly"
                    result.message = (
                        f"Day-over-day price change {day_change_pct:.2f}% "
                        f"exceeds threshold {self.price_change_threshold}% "
                        f"(prev={prev_close}, curr={current_close})"
                    )
                    return result

        if len(history_data) >= 20:
            volumes = [h.get("volume", 0) for h in history_data[-20:]]
            avg_volume = sum(volumes) / len(volumes)
            if avg_volume < self.min_volume_20d:
                result.valid = False
                result.status = "low_liquidity"
                result.message = f"Average volume {int(avg_volume)} below threshold {self.min_volume_20d}"
                return result

            amounts = [h.get("amount", 0) for h in history_data[-20:]]
            avg_amount = sum(amounts) / len(amounts)
            if avg_amount < self.min_volume_amount:
                result.valid = False
                result.status = "low_amount"
                result.message = f"Average amount {avg_amount:.2f} below threshold {self.min_volume_amount}"
                return result

        return result
