import argparse
import json
from datetime import date, datetime
import logging
from app.database import init_db, get_session
from app.models import Symbol, DailyPrice, StrategyResult
from app.pipeline import run_pipeline, backfill_data
from app.scheduler import start_scheduler, run_immediately
from app.fetchers.sina_fetcher import SinaFetcher

logger = logging.getLogger(__name__)


def main_cli():
    parser = argparse.ArgumentParser(description="Momentum Strategy CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    parser_run = subparsers.add_parser("run", help="Run the pipeline immediately")
    parser_run.add_argument("--date", type=str, help="Trade date (YYYY-MM-DD)")

    parser_fetch = subparsers.add_parser("fetch", help="Fetch data only")
    parser_fetch.add_argument("--date", type=str, help="Trade date (YYYY-MM-DD)")

    parser_calculate = subparsers.add_parser("calculate", help="Calculate strategy only")
    parser_calculate.add_argument("--date", type=str, help="Trade date (YYYY-MM-DD)")

    parser_push = subparsers.add_parser("push", help="Push results only")
    parser_push.add_argument("--date", type=str, help="Trade date (YYYY-MM-DD)")

    parser_backfill = subparsers.add_parser("backfill", help="Backfill historical data")
    parser_backfill.add_argument("--days", type=int, default=60, help="Number of days to backfill")
    parser_backfill.add_argument("--symbol", type=str, default=None, help="Specific symbol to backfill")

    parser_backfill_momentum = subparsers.add_parser("backfill-momentum", help="Backfill historical momentum results")
    parser_backfill_momentum.add_argument("--symbol", type=str, default=None, help="Specific symbol to backfill")

    parser_backfill_weighted = subparsers.add_parser("backfill-weighted", help="Backfill historical weighted score results")
    parser_backfill_weighted.add_argument("--symbol", type=str, default=None, help="Specific symbol to backfill")

    parser_repair = subparsers.add_parser("repair", help="Repair anomalous data")
    parser_repair.add_argument("--symbol", type=str, default=None, help="Specific symbol to repair")

    parser_repair_jumps = subparsers.add_parser("repair-jumps", help="Detect and repair price jumps using hfq data")
    parser_repair_jumps.add_argument("--symbol", type=str, default=None, help="Specific symbol to repair")
    parser_repair_jumps.add_argument("--threshold", type=float, default=15.0, help="Price jump threshold percentage")

    parser_scheduler = subparsers.add_parser("scheduler", help="Start scheduler")

    parser_db = subparsers.add_parser("db", help="Database operations")
    parser_db.add_argument("action", choices=["init", "reset"], help="Database action")

    parser_symbol = subparsers.add_parser("symbol", help="Symbol management")
    symbol_subparsers = parser_symbol.add_subparsers(dest="symbol_action")

    parser_symbol_add = symbol_subparsers.add_parser("add", help="Add a symbol")
    parser_symbol_add.add_argument("--code", required=True, help="Symbol code")
    parser_symbol_add.add_argument("--name", required=True, help="Symbol name")
    parser_symbol_add.add_argument("--market", required=True, choices=["A", "SH", "HK", "US"], help="Market type")
    parser_symbol_add.add_argument("--data-source", required=True, choices=["akshare", "yfinance", "mock", "lude", "sina"], help="Data source")

    parser_symbol_list = symbol_subparsers.add_parser("list", help="List all symbols")

    parser_symbol_remove = symbol_subparsers.add_parser("remove", help="Remove a symbol")
    parser_symbol_remove.add_argument("--code", required=True, help="Symbol code")

    parser_symbol_update = symbol_subparsers.add_parser("update", help="Update a symbol")
    parser_symbol_update.add_argument("--code", required=True, help="Symbol code")
    parser_symbol_update.add_argument("--name", help="New symbol name")
    parser_symbol_update.add_argument("--status", choices=["enable", "disable"], help="Status")
    parser_symbol_update.add_argument("--data-source", choices=["akshare", "yfinance", "mock", "lude", "sina"], help="Data source")

    parser_symbol_import = symbol_subparsers.add_parser("import", help="Import symbols from JSON file")
    parser_symbol_import.add_argument("file", help="JSON file path")

    parser_symbol_verify = symbol_subparsers.add_parser("verify", help="Verify all symbols in database")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "run":
        trade_date = parse_date(args.date)
        run_pipeline(trade_date)
    elif args.command == "fetch":
        from app.pipeline import fetch_data
        from app.database import session_scope
        trade_date = parse_date(args.date)
        with session_scope() as session:
            success, message = fetch_data(session, trade_date)
            if success:
                print(f"Fetch completed: {message}")
            else:
                print(f"Fetch failed: {message}")
    elif args.command == "calculate":
        from app.pipeline import calculate_strategy, calculate_weighted_score
        from app.database import session_scope
        from app.utils.date_utils import is_trading_day
        trade_date = parse_date(args.date)
        if not is_trading_day(trade_date):
            print(f"{trade_date} 不是交易日（周末或节假日），跳过计算")
            return
        with session_scope() as session:
            success, message = calculate_strategy(session, trade_date)
            if success:
                print(f"Momentum: {message}")
            else:
                print(f"Momentum failed: {message}")
            success2, message2 = calculate_weighted_score(session, trade_date)
            if success2:
                print(f"WeightedScore: {message2}")
            else:
                print(f"WeightedScore failed: {message2}")
    elif args.command == "push":
        from app.pipeline import push_results
        from app.database import session_scope
        trade_date = parse_date(args.date)
        with session_scope() as session:
            success, message = push_results(session, trade_date)
            if success:
                print(f"Push completed: {message}")
            else:
                print(f"Push failed: {message}")
    elif args.command == "backfill":
        result = backfill_data(args.days, args.symbol)
        if result:
            print(f"Backfill completed successfully for {args.days} days")
        else:
            print("Backfill failed")
    elif args.command == "backfill-momentum":
        from app.pipeline import backfill_momentum
        result = backfill_momentum(args.symbol)
        if result:
            print("Momentum backfill completed successfully")
        else:
            print("Momentum backfill failed")
    elif args.command == "backfill-weighted":
        from app.pipeline import backfill_weighted_score
        result = backfill_weighted_score(args.symbol)
        if result:
            print("Weighted score backfill completed successfully")
        else:
            print("Weighted score backfill failed")
    elif args.command == "repair":
        result = repair_data(args.symbol)
        if result:
            print("Repair completed successfully")
        else:
            print("Repair failed")
    elif args.command == "repair-jumps":
        from app.pipeline import detect_and_repair_price_jumps, repair_with_hfq
        from app.database import session_scope
        with session_scope() as session:
            if args.symbol:
                symbol_obj = session.query(Symbol).filter(Symbol.symbol == args.symbol).first()
                if not symbol_obj:
                    print(f"Symbol {args.symbol} not found")
                    return
                success = repair_with_hfq(session, symbol_obj)
                if success:
                    print(f"Price jump repair completed for {args.symbol}")
                else:
                    print(f"Price jump repair failed for {args.symbol}")
            else:
                result = detect_and_repair_price_jumps(session, args.threshold)
                print(f"Detected {result['total_jumps']} jumps, repaired {result['repaired']}, failed {result['failed']}")
                for detail in result['details']:
                    print(f"  {detail['name']} ({detail['symbol']}) {detail['trade_date']} {detail['pct_change']}% -> {detail['status']}")
    elif args.command == "scheduler":
        start_scheduler()
    elif args.command == "db":
        if args.action == "init":
            init_db()
            print("Database initialized successfully")
        elif args.action == "reset":
            reset_db()
            print("Database reset successfully")
    elif args.command == "symbol":
        handle_symbol_command(args)
    else:
        print(f"Unknown command: {args.command}")


def parse_date(date_str: str = None) -> date:
    if date_str:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    return date.today()


def handle_symbol_command(args):
    session = next(get_session())

    try:
        if args.symbol_action == "add":
            existing = session.query(Symbol).filter(Symbol.symbol == args.code).first()
            if existing:
                print(f"Symbol {args.code} already exists")
                return

            symbol = Symbol(
                symbol=args.code,
                name=args.name,
                market=args.market,
                data_source=args.data_source,
                status=1
            )
            session.add(symbol)
            session.commit()
            print(f"Added symbol: {args.name} ({args.code})")

        elif args.symbol_action == "list":
            symbols = session.query(Symbol).order_by(Symbol.market, Symbol.symbol).all()
            print(f"{'Code':<15} {'Name':<20} {'Market':<6} {'Status':<10} {'Data Source':<15}")
            print("-" * 70)
            for s in symbols:
                status = "Enabled" if s.status == 1 else "Disabled"
                print(f"{s.symbol:<15} {s.name:<20} {s.market:<6} {status:<10} {s.data_source:<15}")

        elif args.symbol_action == "remove":
            symbol = session.query(Symbol).filter(Symbol.symbol == args.code).first()
            if not symbol:
                print(f"Symbol {args.code} not found")
                return

            session.delete(symbol)
            session.commit()
            print(f"Removed symbol: {symbol.name} ({symbol.symbol})")

        elif args.symbol_action == "update":
            symbol = session.query(Symbol).filter(Symbol.symbol == args.code).first()
            if not symbol:
                print(f"Symbol {args.code} not found")
                return

            if args.name:
                symbol.name = args.name
            if args.status:
                symbol.status = 1 if args.status == "enable" else 0
            if args.data_source:
                symbol.data_source = args.data_source

            session.commit()
            print(f"Updated symbol: {symbol.name} ({symbol.symbol})")

        elif args.symbol_action == "import":
            try:
                with open(args.file, "r") as f:
                    data = json.load(f)

                for item in data:
                    existing = session.query(Symbol).filter(Symbol.symbol == item["code"]).first()
                    if not existing:
                        symbol = Symbol(
                            symbol=item["code"],
                            name=item["name"],
                            market=item["market"],
                            data_source=item["data_source"],
                            category=item.get("category", "industry"),
                            status=1
                        )
                        session.add(symbol)

                session.commit()
                print(f"Imported {len(data)} symbols")

            except FileNotFoundError:
                print(f"File {args.file} not found")
            except json.JSONDecodeError:
                print(f"Invalid JSON file: {args.file}")

        elif args.symbol_action == "verify":
            symbols = session.query(Symbol).order_by(Symbol.market, Symbol.symbol).all()
            if not symbols:
                print("No symbols found in database")
                return

            print(f"{'Code':<15} {'Stored Name':<20} {'Real Name':<25} {'Status':<10}")
            print("-" * 75)

            fetcher = SinaFetcher()
            match_count = 0
            mismatch_count = 0
            error_count = 0

            for symbol in symbols:
                if symbol.data_source == "sina":
                    validation = fetcher.validate_symbol(symbol.symbol, symbol.name)
                    
                    if validation['valid']:
                        if validation['match']:
                            status = "✓ Match"
                            match_count += 1
                        else:
                            status = "⚠️ Mismatch"
                            mismatch_count += 1
                        real_name = validation['real_name']
                    else:
                        status = f"✗ Error"
                        real_name = "N/A"
                        error_count += 1
                else:
                    status = "⚠️ Skipped"
                    real_name = "N/A"
                    error_count += 1

                print(f"{symbol.symbol:<15} {symbol.name:<20} {real_name:<25} {status:<10}")

            print("-" * 75)
            print(f"Summary: {match_count} matched, {mismatch_count} mismatched, {error_count} errors")

            if mismatch_count > 0:
                print("\n建议修复以下标的:")
                for symbol in symbols:
                    if symbol.data_source == "sina":
                        validation = fetcher.validate_symbol(symbol.symbol, symbol.name)
                        if validation['valid'] and not validation['match']:
                            print(f"  {symbol.symbol}: {symbol.name} → {validation['real_name']}")

    finally:
        session.close()


def repair_data(symbol: str = None) -> bool:
    """检测并修复异常数据：删除重复记录、删除价格异常记录、重新回填缺失数据"""
    from app.database import session_scope
    from sqlalchemy import text

    logger.info(f"Starting data repair{' for ' + symbol if symbol else ''}")

    try:
        with session_scope() as session:
            # 1. 删除重复记录（保留最新一条）
            dup_result = session.execute(text("""
                DELETE FROM daily_prices
                WHERE id NOT IN (
                    SELECT MAX(id) FROM daily_prices
                    GROUP BY symbol_id, trade_date
                )
            """))
            dup_count = dup_result.rowcount
            session.commit()
            logger.info(f"Deleted {dup_count} duplicate records")

            # 2. 删除价格异常记录（close_price <= 0）
            neg_result = session.execute(text("""
                DELETE FROM daily_prices WHERE close_price <= 0
            """))
            neg_count = neg_result.rowcount
            session.commit()
            logger.info(f"Deleted {neg_count} records with invalid prices")

            # 3. 删除日间价格跳变超过 30% 的记录（疑似数据源混用）
            jump_result = session.execute(text("""
                DELETE FROM daily_prices
                WHERE id IN (
                    SELECT dp.id FROM daily_prices dp
                    JOIN (
                        SELECT symbol_id, trade_date, close_price,
                               LAG(close_price) OVER (PARTITION BY symbol_id ORDER BY trade_date) as prev_close
                        FROM daily_prices
                    ) lag_t
                    ON dp.symbol_id = lag_t.symbol_id AND dp.trade_date = lag_t.trade_date
                    WHERE lag_t.prev_close IS NOT NULL
                      AND lag_t.prev_close > 0
                      AND ABS((lag_t.close_price - lag_t.prev_close) / lag_t.prev_close * 100) > 30
                )
            """))
            jump_count = jump_result.rowcount
            session.commit()
            logger.info(f"Deleted {jump_count} records with price jumps > 30%")

            # 4. 标记对应的策略结果为 invalid
            session.execute(text("""
                UPDATE strategy_results
                SET status = 'invalid'
                WHERE symbol_id IN (
                    SELECT DISTINCT symbol_id FROM daily_prices
                    WHERE close_price <= 0
                )
            """))
            session.commit()

        # 5. 重新回填缺失数据
        total_deleted = dup_count + neg_count + jump_count
        if total_deleted > 0 or symbol:
            logger.info("Re-backfilling data to fill gaps...")
            backfill_data(120, symbol)

        logger.info(f"Repair completed: {dup_count} duplicates, {neg_count} invalid prices, {jump_count} price jumps removed")
        return True

    except Exception as e:
        logger.error(f"Repair failed with exception: {e}", exc_info=True)
        return False


def reset_db():
    from app.database import Base, engine
    Base.metadata.drop_all(bind=engine)
    init_db()


if __name__ == "__main__":
    main_cli()
