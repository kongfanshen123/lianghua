from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ValidationResult:
    def __init__(self):
        self.valid = False
        self.status = "unknown"
        self.message = ""


class BaseValidator(ABC):
    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    def validate(self, data: Dict) -> ValidationResult:
        pass

    def validate_batch(self, data_list: List[Dict]) -> List[Dict]:
        results = []
        for data in data_list:
            result = self.validate(data)
            data["validation_status"] = result.status
            data["validation_message"] = result.message
            if result.valid:
                results.append(data)
            else:
                logger.warning(f"Validation failed for {data.get('trade_date')}: {result.message}")
        return results
