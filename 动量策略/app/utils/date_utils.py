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


# ===========================================================================
# 产品机制：交易日感知的时间序列工具
# ===========================================================================
# 所有时间序列相关指标（动量、连续天数、成交量均值等）在计算时，
# 必须考虑节假日与周末的影响。以下工具函数为策略层提供统一保障：
#
# 1. are_consecutive_trading_days(d1, d2):
#    判断两个日期是否为相邻交易日（d2 的前一个交易日恰好是 d1）。
#    用于连续天数计算中验证数据连续性。
#
# 2. get_expected_latest_trade_date():
#    获取"期望的最新交易日"——如果今天是交易日则返回今天，
#    否则返回最近一个已过的交易日。用于系统状态判断。
#
# 3. count_consecutive_trading_days(dates):
#    给定一组按升序排列的日期，从末尾往前统计连续交易日的数量。
#    遇到断档（非相邻交易日）即停止。用于数据完整性校验。
#
# 规则：策略计算基于"交易日"而非"自然日"。
# 例如：周五的下两个交易日是周一（若无节假日），
# 动量20日周期指的是20个交易日而非20个自然日。
# ===========================================================================


def are_consecutive_trading_days(d1: date, d2: date) -> bool:
    """判断 d1 是否是 d2 的前一个交易日（即 d1 和 d2 是相邻交易日）。

    Args:
        d1: 较早的日期
        d2: 较晚的日期

    Returns:
        True 如果 d1 == get_previous_trading_day(d2)
    """
    return d1 == get_previous_trading_day(d2)


def get_expected_latest_trade_date(target_date: date = None) -> date:
    """获取期望的最新交易日。

    如果 target_date 是交易日，返回它本身；
    否则返回 target_date 之前最近的交易日。

    Args:
        target_date: 目标日期，默认为今天

    Returns:
        期望的最新交易日
    """
    if target_date is None:
        target_date = date.today()
    if is_trading_day(target_date):
        return target_date
    return get_previous_trading_day(target_date)


def count_consecutive_trading_days(dates: list) -> int:
    """统计日期列表末尾的连续交易日数量。

    从列表最后一天开始往前数，遇到非相邻交易日即停止。
    用于验证时间序列数据的连续性。

    Args:
        dates: 按升序排列的日期列表

    Returns:
        末尾连续交易日的数量（含最后一天）
    """
    if not dates:
        return 0

    # 确保按升序排列
    sorted_dates = sorted(dates)
    count = 1  # 最后一天计入

    for i in range(len(sorted_dates) - 1, 0, -1):
        if are_consecutive_trading_days(sorted_dates[i - 1], sorted_dates[i]):
            count += 1
        else:
            break

    return count
