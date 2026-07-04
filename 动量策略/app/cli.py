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
    elif args.command == "backfill":
        result = backfill_data(args.days)
        if result:
            print(f"Backfill completed successfully for {args.days} days")
        else:
            print("Backfill failed")
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


def reset_db():
    from app.database import Base, engine
    Base.metadata.drop_all(bind=engine)
    init_db()


if __name__ == "__main__":
    main_cli()
