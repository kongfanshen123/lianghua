from datetime import date, timedelta, datetime
from typing import List, Dict
import logging
from sqlalchemy import text
from app.database import session_scope
from app.models import Symbol, DailyPrice, StrategyResult
from app.fetchers import MockFetcher, LudeFetcher, SinaFetcher, get_akshare_fetcher, get_yfinance_fetcher
from app.validators import DataValidator
from app.strategies import MomentumStrategy
from app.notifiers import FeishuNotifier
from app.config import config
from app.utils.date_utils import get_previous_trading_day, get_n_trading_days_ago, is_trading_day
from app.utils.logger import get_logger

logger = get_logger(__name__)


def run_pipeline(trade_date: date = None) -> bool:
    if trade_date is None:
        trade_date = date.today()

    if not is_trading_day(trade_date):
        logger.info(f"{trade_date} is not a trading day, skipping")
        return True

    logger.info(f"Starting pipeline for {trade_date}")

    try:
        with session_scope() as session:
            success, message = fetch_data(session, trade_date)
            if not success:
                logger.error(f"Fetch data failed: {message}")
                send_alert(f"数据获取失败 - {message}")
                return False

            success, message = validate_data(session, trade_date)
            if not success:
                logger.error(f"Validate data failed: {message}")
                send_alert(f"数据校验失败 - {message}")
                return False

            success, message = calculate_strategy(session, trade_date)
            if not success:
                logger.error(f"Calculate strategy failed: {message}")
                send_alert(f"策略计算失败 - {message}")
                return False

            success, message = push_results(session, trade_date)
            if not success:
                logger.error(f"Push results failed: {message}")
                send_alert(f"结果推送失败 - {message}")
                return False

        logger.info(f"Pipeline completed successfully for {trade_date}")
        return True

    except Exception as e:
        logger.error(f"Pipeline failed with exception: {e}", exc_info=True)
        send_alert(f"Pipeline异常 - {str(e)}")
        return False


def fetch_data(session, trade_date: date) -> tuple:
    logger.info(f"Fetching data for {trade_date}")
    symbols = session.query(Symbol).filter(Symbol.status == 1).all()

    if not symbols:
        return False, "No active symbols found"

    AkShareFetcher = get_akshare_fetcher()
    YFinanceFetcher = get_yfinance_fetcher()

    akshare_fetcher = None
    yfinance_fetcher = None
    mock_fetcher = MockFetcher()
    lude_fetcher = LudeFetcher()
    sina_fetcher = SinaFetcher()

    if AkShareFetcher:
        akshare_fetcher = AkShareFetcher(
            request_interval=config.REQUEST_INTERVAL,
            max_retry=config.MAX_RETRY,
            retry_delay=config.RETRY_DELAY
        )

    if YFinanceFetcher:
        yfinance_fetcher = YFinanceFetcher(
            request_interval=config.REQUEST_INTERVAL,
            max_retry=config.MAX_RETRY,
            retry_delay=config.RETRY_DELAY
        )

    success_count = 0
    fail_count = 0

    for symbol in symbols:
        try:
            if symbol.data_source == "akshare" and akshare_fetcher:
                result = akshare_fetcher.fetch_daily_price(symbol.symbol, trade_date)
            elif symbol.data_source == "yfinance" and yfinance_fetcher:
                result = yfinance_fetcher.fetch_daily_price(symbol.symbol, trade_date)
            elif symbol.data_source == "mock":
                result = mock_fetcher.fetch_daily_price(symbol.symbol, trade_date)
            elif symbol.data_source == "lude":
                result = lude_fetcher.fetch_daily_price(symbol.symbol, trade_date)
            elif symbol.data_source == "sina":
                result = sina_fetcher.fetch_daily_price(symbol.symbol, trade_date)
            else:
                logger.warning(f"Data source {symbol.data_source} not available for {symbol.name}")
                fail_count += 1
                continue

            if result.success and result.data:
                # 数据源切换保护：检测是否与历史数据源不一致
                existing_source = session.query(DailyPrice.data_source).filter(
                    DailyPrice.symbol_id == symbol.id
                ).first()
                if existing_source and existing_source[0] and existing_source[0] != result.data_source:
                    logger.warning(
                        f"Data source change detected for {symbol.name}: "
                        f"{existing_source[0]} -> {result.data_source}. "
                        f"Clearing old data to prevent mixing."
                    )
                    session.query(DailyPrice).filter(
                        DailyPrice.symbol_id == symbol.id
                    ).delete()
                    session.commit()

                for item in result.data:
                    trade_date_obj = datetime.strptime(item["trade_date"], "%Y-%m-%d").date()

                    existing = session.query(DailyPrice).filter(
                        DailyPrice.symbol_id == symbol.id,
                        DailyPrice.trade_date == trade_date_obj
                    ).first()

                    if existing:
                        existing.close_price = item["close_price"]
                        existing.open_price = item["open_price"]
                        existing.high_price = item["high_price"]
                        existing.low_price = item["low_price"]
                        existing.volume = item["volume"]
                        existing.amount = item["amount"]
                        existing.adjusted_factor = item["adjusted_factor"]
                        existing.is_suspended = item["is_suspended"]
                        existing.is_ex_dividend = item["is_ex_dividend"]
                        existing.data_source = result.data_source
                    else:
                        daily_price = DailyPrice(
                            symbol_id=symbol.id,
                            trade_date=trade_date_obj,
                            close_price=item["close_price"],
                            open_price=item["open_price"],
                            high_price=item["high_price"],
                            low_price=item["low_price"],
                            volume=item["volume"],
                            amount=item["amount"],
                            adjusted_factor=item["adjusted_factor"],
                            is_suspended=item["is_suspended"],
                            is_ex_dividend=item["is_ex_dividend"],
                            data_source=result.data_source
                        )
                        session.add(daily_price)

                session.commit()
                success_count += 1
                logger.info(f"Successfully fetched data for {symbol.name}")
            else:
                fail_count += 1
                logger.warning(f"Failed to fetch data for {symbol.name}: {result.error_message}")

        except Exception as e:
            fail_count += 1
            logger.error(f"Error fetching data for {symbol.name}: {e}")

    if success_count == 0:
        return False, f"Failed to fetch data for all {len(symbols)} symbols"

    logger.info(f"Data fetch completed: {success_count} success, {fail_count} failed")
    return True, f"Fetched {success_count}/{len(symbols)} symbols"


def validate_data(session, trade_date: date) -> tuple:
    logger.info(f"Validating data for {trade_date}")
    validator = DataValidator()

    daily_prices = session.query(DailyPrice).filter(
        DailyPrice.trade_date == trade_date
    ).all()

    if not daily_prices:
        return False, "No daily prices found for validation"

    valid_count = 0
    invalid_count = 0
    abnormal_symbols = set()

    for dp in daily_prices:
        data = {
            "trade_date": dp.trade_date.strftime("%Y-%m-%d"),
            "close_price": float(dp.close_price),
            "open_price": float(dp.open_price) if dp.open_price else None,
            "volume": dp.volume or 0,
            "is_suspended": dp.is_suspended or 0,
            "is_ex_dividend": dp.is_ex_dividend or 0,
        }

        history_prices = session.query(DailyPrice).filter(
            DailyPrice.symbol_id == dp.symbol_id,
            DailyPrice.trade_date < trade_date
        ).order_by(DailyPrice.trade_date.desc()).limit(20).all()

        history_data = []
        for hp in reversed(history_prices):
            history_data.append({
                "trade_date": hp.trade_date.strftime("%Y-%m-%d"),
                "close_price": float(hp.close_price),
                "volume": hp.volume or 0,
                "amount": float(hp.amount) if hp.amount else 0,
            })

        result = validator.validate_with_history(data, history_data)
        if result.valid:
            valid_count += 1
        else:
            invalid_count += 1
            abnormal_symbols.add(dp.symbol_id)
            logger.warning(f"Validation failed for symbol_id {dp.symbol_id}: {result.message}")

    # 将异常标的对应的策略结果标记为 invalid
    if abnormal_symbols:
        session.query(StrategyResult).filter(
            StrategyResult.symbol_id.in_(abnormal_symbols),
            StrategyResult.trade_date == trade_date
        ).update({StrategyResult.status: "invalid"}, synchronize_session=False)
        session.commit()

    logger.info(f"Data validation completed: {valid_count} valid, {invalid_count} invalid")
    return True, f"Validated {valid_count}/{valid_count + invalid_count} records"


def calculate_strategy(session, trade_date: date) -> tuple:
    logger.info(f"Calculating strategy for {trade_date}")
    strategy = MomentumStrategy()

    symbols = session.query(Symbol).filter(Symbol.status == 1).all()

    previous_day = get_previous_trading_day(trade_date)
    previous_results = session.query(StrategyResult).filter(
        StrategyResult.trade_date == previous_day
    ).all()
    previous_rank_map = {r.symbol_id: r.ranking for r in previous_results}

    results = []
    for symbol in symbols:
        prices = session.query(DailyPrice).filter(
            DailyPrice.symbol_id == symbol.id
        ).order_by(DailyPrice.trade_date).all()

        if not prices:
            logger.warning(f"No price data for {symbol.name}")
            continue

        price_list = []
        for p in prices:
            price_list.append({
                "trade_date": p.trade_date.strftime("%Y-%m-%d"),
                "close_price": float(p.close_price),
                "volume": p.volume or 0,
                "amount": float(p.amount) if p.amount else 0,
            })

        result = strategy.calculate(symbol.id, price_list, trade_date)
        results.append(result)

        # 计算连续趋势天数
        if result.status == "valid":
            prev_results = session.query(StrategyResult).filter(
                StrategyResult.symbol_id == symbol.id,
                StrategyResult.trade_date < trade_date,
                StrategyResult.status == "valid"
            ).order_by(StrategyResult.trade_date.asc()).limit(500).all()
            historical_momentums = [float(r.momentum_20d) for r in prev_results]
            result.consecutive_days = strategy.calculate_consecutive_days(result.momentum_20d, historical_momentums)

    ranked_results = strategy.rank(results)
    ranked_results = strategy.calculate_ranking_change(ranked_results, previous_rank_map)

    for result in ranked_results:
        existing = session.query(StrategyResult).filter(
            StrategyResult.symbol_id == result.symbol_id,
            StrategyResult.trade_date == result.trade_date
        ).first()

        if existing:
            existing.momentum_20d = result.momentum_20d
            existing.volume_confirmed = result.volume_confirmed
            existing.volume_change_pct = result.volume_change_pct
            existing.ranking = result.ranking
            existing.ranking_change = result.ranking_change
            existing.trend_strength = result.trend_strength
            existing.consecutive_days = result.consecutive_days
            existing.status = result.status
        else:
            db_result = StrategyResult(
                symbol_id=result.symbol_id,
                trade_date=result.trade_date,
                momentum_20d=result.momentum_20d,
                volume_confirmed=result.volume_confirmed,
                volume_change_pct=result.volume_change_pct,
                ranking=result.ranking,
                ranking_change=result.ranking_change,
                trend_strength=result.trend_strength,
                consecutive_days=result.consecutive_days,
                status=result.status
            )
            session.add(db_result)

    session.commit()

    logger.info(f"Strategy calculation completed: {len(ranked_results)} results")
    return True, f"Calculated {len(ranked_results)} strategy results"


def push_results(session, trade_date: date) -> tuple:
    logger.info(f"Pushing results for {trade_date}")
    notifier = FeishuNotifier()

    results = session.query(StrategyResult).filter(
        StrategyResult.trade_date == trade_date,
        StrategyResult.status == "valid"
    ).order_by(StrategyResult.ranking).all()

    if not results:
        return False, "No valid strategy results to push"

    symbol_map = {}
    for r in results:
        symbol = session.query(Symbol).filter(Symbol.id == r.symbol_id).first()
        if symbol:
            symbol_map[r.symbol_id] = symbol

    strong_stocks = []
    weak_stocks = []

    for result in results[:config.TOP_N]:
        symbol = symbol_map.get(result.symbol_id)
        if symbol:
            strong_stocks.append({
                "name": symbol.name,
                "symbol": symbol.symbol,
                "momentum_20d": float(result.momentum_20d) if result.momentum_20d else 0,
                "trend_strength": result.trend_strength,
                "ranking": result.ranking,
                "ranking_change": result.ranking_change,
            })

    for result in reversed(results[-config.TOP_N:]):
        symbol = symbol_map.get(result.symbol_id)
        if symbol:
            weak_stocks.append({
                "name": symbol.name,
                "symbol": symbol.symbol,
                "momentum_20d": float(result.momentum_20d) if result.momentum_20d else 0,
                "trend_strength": result.trend_strength,
                "ranking": result.ranking,
                "ranking_change": result.ranking_change,
            })

    card_data = {
        "trade_date": trade_date.strftime("%Y-%m-%d"),
        "strong_stocks": strong_stocks,
        "weak_stocks": weak_stocks,
        "total_count": len(results),
        "abnormal_count": invalid_count,
    }

    if config.PUSH_MODE == "card":
        result = notifier.send_card(card_data)
    else:
        text_message = build_text_message(card_data)
        result = notifier.send(text_message)

    if result.success:
        logger.info(f"Successfully pushed results to Feishu")
        return True, "Push successful"
    else:
        logger.error(f"Failed to push results: {result.error_message}")
        return False, result.error_message


def build_text_message(card_data: Dict) -> str:
    message = f"📊 【每日动量策略报告】\n"
    message += f"📅 日期：{card_data['trade_date']}\n\n"

    message += "🏆 强势标的TOP5：\n"
    for i, stock in enumerate(card_data["strong_stocks"], 1):
        change_icon = "→"
        if stock.get("ranking_change", 0) > 0:
            change_icon = f"↑{stock['ranking_change']}"
        elif stock.get("ranking_change", 0) < 0:
            change_icon = f"↓{abs(stock['ranking_change'])}"
        message += f"{i}. {stock['name']}({stock['symbol']}) - 动量: {stock['momentum_20d']:+.2f}% - 趋势: {stock['trend_strength']} - {change_icon}\n"

    message += "\n📉 弱势标的TOP5：\n"
    for i, stock in enumerate(card_data["weak_stocks"], 1):
        change_icon = "→"
        if stock.get("ranking_change", 0) > 0:
            change_icon = f"↑{stock['ranking_change']}"
        elif stock.get("ranking_change", 0) < 0:
            change_icon = f"↓{abs(stock['ranking_change'])}"
        message += f"{i}. {stock['name']}({stock['symbol']}) - 动量: {stock['momentum_20d']:+.2f}% - 趋势: {stock['trend_strength']} - {change_icon}\n"

    message += "\n💡 策略说明：基于20日动量策略计算，采用前复权价格\n"
    message += "⚠️ 免责声明：本报告仅供参考，不构成投资建议"

    return message


def send_alert(message: str) -> None:
    try:
        notifier = FeishuNotifier()
        notifier.send(f"⚠️ 动量策略告警\n{message}")
    except Exception as e:
        logger.error(f"Failed to send alert: {e}")


def backfill_data(days: int = 60, symbol_filter: str = None) -> bool:
    logger.info(f"Starting backfill for last {days} days{' for ' + symbol_filter if symbol_filter else ''}")

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    try:
        with session_scope() as session:
            query = session.query(Symbol).filter(Symbol.status == 1)
            if symbol_filter:
                query = query.filter(Symbol.symbol == symbol_filter)
            symbols = query.all()

            if not symbols:
                logger.error("No active symbols found for backfill")
                return False

            AkShareFetcher = get_akshare_fetcher()
            YFinanceFetcher = get_yfinance_fetcher()

            akshare_fetcher = None
            yfinance_fetcher = None
            mock_fetcher = MockFetcher()
            lude_fetcher = LudeFetcher()
            sina_fetcher = SinaFetcher()

            if AkShareFetcher:
                akshare_fetcher = AkShareFetcher(
                    request_interval=config.REQUEST_INTERVAL,
                    max_retry=config.MAX_RETRY,
                    retry_delay=config.RETRY_DELAY
                )

            if YFinanceFetcher:
                yfinance_fetcher = YFinanceFetcher(
                    request_interval=config.REQUEST_INTERVAL,
                    max_retry=config.MAX_RETRY,
                    retry_delay=config.RETRY_DELAY
                )

            success_count = 0
            fail_count = 0

            for symbol in symbols:
                try:
                    if symbol.data_source == "akshare" and akshare_fetcher:
                        result = akshare_fetcher.fetch_price_history(symbol.symbol, start_date, end_date)
                    elif symbol.data_source == "yfinance" and yfinance_fetcher:
                        result = yfinance_fetcher.fetch_price_history(symbol.symbol, start_date, end_date)
                    elif symbol.data_source == "mock":
                        result = mock_fetcher.fetch_price_history(symbol.symbol, start_date, end_date)
                    elif symbol.data_source == "lude":
                        result = lude_fetcher.fetch_price_history(symbol.symbol, start_date, end_date)
                    elif symbol.data_source == "sina":
                        result = sina_fetcher.fetch_price_history(symbol.symbol, start_date, end_date)
                    else:
                        logger.warning(f"Data source {symbol.data_source} not available for {symbol.name}")
                        fail_count += 1
                        continue

                    if result.success and result.data:
                        for item in result.data:
                            trade_date_obj = datetime.strptime(item["trade_date"], "%Y-%m-%d").date()

                            existing = session.query(DailyPrice).filter(
                                DailyPrice.symbol_id == symbol.id,
                                DailyPrice.trade_date == trade_date_obj
                            ).first()

                            if not existing:
                                daily_price = DailyPrice(
                                    symbol_id=symbol.id,
                                    trade_date=trade_date_obj,
                                    close_price=item["close_price"],
                                    open_price=item["open_price"],
                                    high_price=item["high_price"],
                                    low_price=item["low_price"],
                                    volume=item["volume"],
                                    amount=item["amount"],
                                    adjusted_factor=item["adjusted_factor"],
                                    is_suspended=item["is_suspended"],
                                    is_ex_dividend=item["is_ex_dividend"],
                                    data_source=result.data_source
                                )
                                session.add(daily_price)

                        session.commit()
                        success_count += 1
                        logger.info(f"Successfully backfilled {len(result.data)} records for {symbol.name}")
                    else:
                        fail_count += 1
                        logger.warning(f"Failed to backfill data for {symbol.name}: {result.error_message}")

                except Exception as e:
                    fail_count += 1
                    logger.error(f"Error backfilling data for {symbol.name}: {e}")

            if success_count == 0:
                logger.error(f"Failed to backfill data for all {len(symbols)} symbols")
                return False

            logger.info(f"Backfill completed: {success_count} success, {fail_count} failed")
            return True

    except Exception as e:
        logger.error(f"Backfill failed with exception: {e}", exc_info=True)
        return False


def backfill_momentum(symbol_filter: str = None) -> bool:
    """回溯所有标的在历史数据范围内的每日动量，落表存储。"""
    logger.info(f"Starting momentum backfill{' for ' + symbol_filter if symbol_filter else ''}")

    try:
        with session_scope() as session:
            query = session.query(Symbol).filter(Symbol.status == 1)
            if symbol_filter:
                query = query.filter(Symbol.symbol == symbol_filter)
            symbols = query.all()

            if not symbols:
                logger.error("No active symbols found for momentum backfill")
                return False

            strategy = MomentumStrategy()

            for symbol in symbols:
                prices = session.query(DailyPrice).filter(
                    DailyPrice.symbol_id == symbol.id
                ).order_by(DailyPrice.trade_date).all()

                if not prices or len(prices) < strategy.period + 1:
                    logger.warning(f"Not enough price data for {symbol.name} ({len(prices) if prices else 0} records)")
                    continue

                price_list = []
                for p in prices:
                    price_list.append({
                        "trade_date": p.trade_date.strftime("%Y-%m-%d"),
                        "close_price": float(p.close_price),
                        "volume": p.volume or 0,
                        "amount": float(p.amount) if p.amount else 0,
                    })

                # 计算每个有足够数据的日期的动量
                results_by_date = {}
                for i in range(strategy.period, len(price_list)):
                    trade_date_str = price_list[i]["trade_date"]
                    trade_date_obj = datetime.strptime(trade_date_str, "%Y-%m-%d").date()
                    prices_up_to = price_list[:i + 1]
                    result = strategy.calculate(symbol.id, prices_up_to, trade_date_obj)
                    results_by_date[trade_date_str] = result

                # 计算连续趋势天数
                sorted_dates = sorted(results_by_date.keys())
                all_momentums = [results_by_date[d].momentum_20d for d in sorted_dates]
                for i, date_str in enumerate(sorted_dates):
                    result = results_by_date[date_str]
                    if result.status == "valid":
                        result.consecutive_days = strategy.calculate_consecutive_days(
                            result.momentum_20d, all_momentums[:i]
                        )

                # 存储结果（不计算排名，排名在后续单独计算）
                for date_str, result in results_by_date.items():
                    trade_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

                    existing = session.query(StrategyResult).filter(
                        StrategyResult.symbol_id == result.symbol_id,
                        StrategyResult.trade_date == trade_date_obj
                    ).first()

                    if existing:
                        existing.momentum_20d = result.momentum_20d
                        existing.volume_confirmed = result.volume_confirmed
                        existing.volume_change_pct = result.volume_change_pct
                        existing.trend_strength = result.trend_strength
                        existing.consecutive_days = result.consecutive_days
                        existing.status = result.status
                    else:
                        db_result = StrategyResult(
                            symbol_id=result.symbol_id,
                            trade_date=trade_date_obj,
                            momentum_20d=result.momentum_20d,
                            volume_confirmed=result.volume_confirmed,
                            volume_change_pct=result.volume_change_pct,
                            trend_strength=result.trend_strength,
                            consecutive_days=result.consecutive_days,
                            status=result.status
                        )
                        session.add(db_result)

                session.commit()
                logger.info(f"Backfilled momentum for {symbol.name}: {len(results_by_date)} dates")

            # 为每个日期计算排名和排名变化
            all_dates = [r[0] for r in session.query(StrategyResult.trade_date).distinct().all()]
            all_dates.sort()

            for trade_date_obj in all_dates:
                results = session.query(StrategyResult).filter(
                    StrategyResult.trade_date == trade_date_obj,
                    StrategyResult.status == "valid"
                ).order_by(StrategyResult.momentum_20d.desc()).all()

                for idx, result in enumerate(results):
                    result.ranking = idx + 1

                # 排名变化
                prev_day = get_previous_trading_day(trade_date_obj)
                prev_results = session.query(StrategyResult).filter(
                    StrategyResult.trade_date == prev_day
                ).all()
                prev_rank_map = {r.symbol_id: r.ranking for r in prev_results}

                for result in results:
                    prev_rank = prev_rank_map.get(result.symbol_id)
                    result.ranking_change = prev_rank - result.ranking if prev_rank is not None else 0

                session.commit()

            logger.info(f"Momentum backfill completed: {len(all_dates)} dates processed")
            return True

    except Exception as e:
        logger.error(f"Momentum backfill failed with exception: {e}", exc_info=True)
        return False
