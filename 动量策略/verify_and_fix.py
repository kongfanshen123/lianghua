import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import get_session, init_db
from app.models import Symbol
from app.fetchers.sina_fetcher import SinaFetcher


def main():
    init_db()
    session = next(get_session())
    fetcher = SinaFetcher()
    
    try:
        symbols = session.query(Symbol).order_by(Symbol.market, Symbol.symbol).all()
        
        if not symbols:
            print("数据库中没有标的数据")
            return
        
        print(f"{'Code':<15} {'Stored Name':<20} {'Real Name':<25} {'Action':<15}")
        print("-" * 80)
        
        fixed_count = 0
        matched_count = 0
        skipped_count = 0
        
        for symbol in symbols:
            if symbol.data_source != "sina":
                print(f"{symbol.symbol:<15} {symbol.name:<20} {'N/A':<25} {'Skipped':<15}")
                skipped_count += 1
                continue
            
            validation = fetcher.validate_symbol(symbol.symbol, symbol.name)
            
            if not validation['valid']:
                error_msg = f"Error: {validation['error']}"
                print(f"{symbol.symbol:<15} {symbol.name:<20} {'Error':<25} {error_msg:<15}")
                skipped_count += 1
                continue
            
            if validation['match']:
                print(f"{symbol.symbol:<15} {symbol.name:<20} {validation['real_name']:<25} {'✓ Matched':<15}")
                matched_count += 1
            else:
                print(f"{symbol.symbol:<15} {symbol.name:<20} {validation['real_name']:<25} {'⚠️ Fixed':<15}")
                symbol.name = validation['real_name']
                fixed_count += 1
        
        session.commit()
        
        print("-" * 80)
        print(f"Summary: {matched_count} matched, {fixed_count} fixed, {skipped_count} skipped")
        
        if fixed_count > 0:
            print(f"\n已自动修复 {fixed_count} 个标的名称")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()
