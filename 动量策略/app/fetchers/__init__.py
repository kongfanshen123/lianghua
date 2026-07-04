from .base_fetcher import BaseFetcher
from .mock_fetcher import MockFetcher
from .lude_fetcher import LudeFetcher
from .sina_fetcher import SinaFetcher

__all__ = ['BaseFetcher', 'MockFetcher', 'LudeFetcher', 'SinaFetcher']


def get_akshare_fetcher():
    try:
        from .akshare_fetcher import AkShareFetcher
        return AkShareFetcher
    except ImportError:
        return None


def get_yfinance_fetcher():
    try:
        from .yfinance_fetcher import YFinanceFetcher
        return YFinanceFetcher
    except ImportError:
        return None


def get_lude_fetcher():
    try:
        from .lude_fetcher import LudeFetcher
        return LudeFetcher
    except ImportError:
        return None


def get_sina_fetcher():
    try:
        from .sina_fetcher import SinaFetcher
        return SinaFetcher
    except ImportError:
        return None
