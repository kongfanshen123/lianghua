from datetime import date, timedelta
import calendar
import logging

logger = logging.getLogger(__name__)

# 中国A股市场节假日列表 (2024-2026)
# 来源：上海证券交易所/深圳证券交易所公告
CN_HOLIDAYS = {
    # 2024年
    date(2024, 1, 1),    # 元旦
    date(2024, 2, 9),    # 除夕
    date(2024, 2, 12),   # 春节
    date(2024, 2, 13),   # 春节
    date(2024, 2, 14),   # 春节
    date(2024, 2, 15),   # 春节
    date(2024, 2, 16),   # 春节
    date(2024, 4, 4),    # 清明节
    date(2024, 4, 5),    # 清明节
    date(2024, 5, 1),    # 劳动节
    date(2024, 5, 2),    # 劳动节
    date(2024, 5, 3),    # 劳动节
    date(2024, 6, 10),   # 端午节
    date(2024, 9, 16),   # 中秋节
    date(2024, 9, 17),   # 中秋节
    date(2024, 10, 1),   # 国庆节
    date(2024, 10, 2),   # 国庆节
    date(2024, 10, 3),   # 国庆节
    date(2024, 10, 4),   # 国庆节
    date(2024, 10, 7),   # 国庆节
    # 2025年
    date(2025, 1, 1),    # 元旦
    date(2025, 1, 28),   # 春节
    date(2025, 1, 29),   # 春节
    date(2025, 1, 30),   # 春节
    date(2025, 1, 31),   # 春节
    date(2025, 2, 3),    # 春节
    date(2025, 4, 4),    # 清明节
    date(2025, 5, 1),    # 劳动节
    date(2025, 5, 2),    # 劳动节
    date(2025, 5, 5),    # 劳动节
    date(2025, 6, 2),    # 端午节
    date(2025, 10, 1),   # 国庆节
    date(2025, 10, 2),   # 国庆节
    date(2025, 10, 3),   # 国庆节
    date(2025, 10, 6),   # 国庆节
    date(2025, 10, 7),   # 国庆节
    date(2025, 10, 8),   # 中秋节调休
    # 2026年（预估，待官方公告后更新）
    date(2026, 1, 1),    # 元旦
    date(2026, 2, 16),   # 春节（预估）
    date(2026, 2, 17),   # 春节
    date(2026, 2, 18),   # 春节
    date(2026, 2, 19),   # 春节
    date(2026, 2, 20),   # 春节
    date(2026, 4, 6),    # 清明节
    date(2026, 5, 1),    # 劳动节
    date(2026, 6, 19),   # 端午节
    date(2026, 9, 25),   # 中秋节
    date(2026, 10, 1),   # 国庆节
    date(2026, 10, 2),   # 国庆节
    date(2026, 10, 5),   # 国庆节
    date(2026, 10, 6),   # 国庆节
    date(2026, 10, 7),   # 国庆节
    date(2026, 10, 8),   # 国庆节
}


def is_trading_day(trade_date: date) -> bool:
    """判断是否为交易日（排除周末和中国法定节假日）"""
    if trade_date.weekday() >= 5:
        return False
    if trade_date in CN_HOLIDAYS:
        return False
    return True


def get_trading_dates(start_date: date, end_date: date) -> list:
    dates = []
    current_date = start_date
    while current_date <= end_date:
        if is_trading_day(current_date):
            dates.append(current_date)
        current_date += timedelta(days=1)
    return dates


def get_previous_trading_day(trade_date: date) -> date:
    previous_day = trade_date - timedelta(days=1)
    while not is_trading_day(previous_day):
        previous_day -= timedelta(days=1)
    return previous_day


def get_n_trading_days_ago(trade_date: date, n: int) -> date:
    current_date = trade_date
    count = 0
    while count < n:
        current_date -= timedelta(days=1)
        if is_trading_day(current_date):
            count += 1
    return current_date


def get_last_trading_day_of_month(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    date_candidate = date(year, month, last_day)
    while not is_trading_day(date_candidate):
        date_candidate -= timedelta(days=1)
    return date_candidate


def get_last_trading_day_of_week(trade_date: date) -> date:
    days_until_friday = 4 - trade_date.weekday()
    if days_until_friday < 0:
        days_until_friday += 7
    return trade_date + timedelta(days=days_until_friday)
