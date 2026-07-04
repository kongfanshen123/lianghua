from datetime import date, timedelta
import calendar


def is_trading_day(trade_date: date) -> bool:
    if trade_date.weekday() >= 5:
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
