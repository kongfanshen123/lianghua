from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import date
import logging

logger = logging.getLogger(__name__)


class StrategyResult:
    def __init__(self):
        self.symbol_id: int = 0
        self.trade_date: date = date.today()
        self.momentum_20d: float = 0.0
        self.volume_confirmed: int = 0
        self.volume_change_pct: float = 0.0
        self.ranking: int = 0
        self.ranking_change: int = 0
        self.trend_strength: str = ""
        self.status: str = "valid"
        self.message: str = ""


class BaseStrategy(ABC):
    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    def calculate(self, symbol_id: int, prices: List[Dict], trade_date: date) -> StrategyResult:
        pass

    @abstractmethod
    def rank(self, results: List[StrategyResult]) -> List[StrategyResult]:
        pass
