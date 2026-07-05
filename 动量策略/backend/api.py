import sqlite3
import json
import os
import subprocess
from datetime import date, datetime, timedelta
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="动量策略数据管理", version="2.0.0")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 使用绝对路径，避免 CWD 依赖
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_BASE_DIR, "data", "momentum_strategy.db")
FRONTEND_DIR = os.path.join(_BASE_DIR, "frontend")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
async def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/api/symbols")
async def get_symbols(
    status: int = Query(None, description="状态筛选"),
    search: str = Query(None, description="搜索名称或代码"),
    category: str = Query(None, description="分类筛选: market/industry")
):
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM symbols"
    params = []
    
    conditions = []
    if status is not None:
        conditions.append("status = ?")
        params.append(status)
    if search:
        conditions.append("(symbol LIKE ? OR name LIKE ?)")
        params.append(f"%{search}%")
        params.append(f"%{search}%")
    if category:
        conditions.append("category = ?")
        params.append(category)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY category, market, symbol"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return {"data": [dict(row) for row in rows]}


@app.get("/api/symbols/categories")
async def get_symbol_categories():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM symbols 
        WHERE status = 1
        GROUP BY category
    """)
    rows = cursor.fetchall()
    conn.close()
    
    return {"data": [dict(row) for row in rows]}


@app.get("/api/symbols/{symbol_id}")
async def get_symbol(symbol_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM symbols WHERE id = ?", (symbol_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    return dict(row)


@app.get("/api/prices")
async def get_prices(
    symbol_id: int = Query(None, description="标的ID"),
    symbol: str = Query(None, description="标的代码"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(50, description="每页大小"),
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期")
):
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT dp.*, s.symbol, s.name, s.category 
        FROM daily_prices dp 
        JOIN symbols s ON dp.symbol_id = s.id
    """
    params = []
    conditions = []
    
    if symbol_id:
        conditions.append("dp.symbol_id = ?")
        params.append(symbol_id)
    if symbol:
        conditions.append("s.symbol = ?")
        params.append(symbol)
    if start_date:
        conditions.append("dp.trade_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("dp.trade_date <= ?")
        params.append(end_date)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query_count = "SELECT COUNT(*) FROM (" + query + ") as t"
    cursor.execute(query_count, params)
    total = cursor.fetchone()[0]
    
    query += " ORDER BY dp.trade_date DESC LIMIT ? OFFSET ?"
    params.append(page_size)
    params.append((page - 1) * page_size)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    conn.close()
    
    return {
        "data": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@app.get("/api/prices/symbol/{symbol_code}")
async def get_prices_by_symbol(symbol_code: str):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM symbols WHERE symbol = ?", (symbol_code,))
    symbol_row = cursor.fetchone()
    if not symbol_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    symbol_id = symbol_row["id"]
    
    cursor.execute(
        """SELECT * FROM daily_prices 
           WHERE symbol_id = ? 
           ORDER BY trade_date ASC""",
        (symbol_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {"data": [dict(row) for row in rows]}


@app.get("/api/prices/count")
async def get_prices_count():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.symbol, s.name, s.category, COUNT(*) as count
        FROM daily_prices dp 
        JOIN symbols s ON dp.symbol_id = s.id
        GROUP BY dp.symbol_id
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    return {"data": [dict(row) for row in rows]}


@app.get("/api/prices/counts")
async def get_prices_counts():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.symbol, COUNT(*) as count
        FROM daily_prices dp 
        JOIN symbols s ON dp.symbol_id = s.id
        GROUP BY dp.symbol_id
    """)
    rows = cursor.fetchall()
    conn.close()
    
    result = {}
    for row in rows:
        result[row["symbol"]] = row["count"]
    
    return {"data": result}


@app.get("/api/results")
async def get_results(
    trade_date: str = Query(None, description="交易日期"),
    category: str = Query(None, description="分类筛选"),
    strategy: str = Query("momentum", description="策略类型: momentum/weighted_score"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(50, description="每页大小")
):
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT sr.*, s.symbol, s.name, s.category 
        FROM strategy_results sr 
        JOIN symbols s ON sr.symbol_id = s.id
        WHERE sr.strategy_type = ?
    """
    params = [strategy]
    conditions = []
    
    if trade_date:
        conditions.append("sr.trade_date = ?")
        params.append(trade_date)
    if category:
        conditions.append("s.category = ?")
        params.append(category)
    
    if conditions:
        query += " AND " + " AND ".join(conditions)
    
    query_count = "SELECT COUNT(*) FROM (" + query + ") as t"
    cursor.execute(query_count, params)
    total = cursor.fetchone()[0]
    
    query += " ORDER BY sr.ranking LIMIT ? OFFSET ?"
    params.append(page_size)
    params.append((page - 1) * page_size)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    conn.close()
    
    return {
        "data": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@app.get("/api/results/history")
async def get_results_history(
    symbol: str = Query(None, description="标的代码"),
    category: str = Query(None, description="分类筛选: market/industry"),
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期"),
    strategy: str = Query("momentum", description="策略类型: momentum/weighted_score"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(50, description="每页大小")
):
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT sr.*, s.symbol, s.name, s.category 
        FROM strategy_results sr 
        JOIN symbols s ON sr.symbol_id = s.id
        WHERE sr.status = 'valid' AND sr.strategy_type = ?
    """
    params = [strategy]
    
    if symbol:
        query += " AND s.symbol = ?"
        params.append(symbol)
    if category and category != "all":
        query += " AND s.category = ?"
        params.append(category)
    if start_date:
        query += " AND sr.trade_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND sr.trade_date <= ?"
        params.append(end_date)
    
    query_count = "SELECT COUNT(*) FROM (" + query + ") as t"
    cursor.execute(query_count, params)
    total = cursor.fetchone()[0]
    
    query += " ORDER BY sr.trade_date DESC, sr.ranking LIMIT ? OFFSET ?"
    params.append(page_size)
    params.append((page - 1) * page_size)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    conn.close()
    
    return {
        "data": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@app.get("/api/results/latest")
async def get_latest_results(
    category: str = Query(None, description="分类筛选: market/industry/all"),
    strategy: str = Query("momentum", description="策略类型: momentum/weighted_score")
):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(trade_date) FROM strategy_results WHERE strategy_type = ?", (strategy,))
    latest_date = cursor.fetchone()[0]
    
    query = """
        SELECT sr.*, s.symbol, s.name, s.category 
        FROM strategy_results sr 
        JOIN symbols s ON sr.symbol_id = s.id
        WHERE sr.trade_date = ? AND sr.strategy_type = ?
    """
    params = [latest_date, strategy]
    
    if category and category != "all":
        query += " AND s.category = ?"
        params.append(category)
    
    query += " ORDER BY sr.ranking"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return {"data": [dict(row) for row in rows], "trade_date": latest_date}


@app.get("/api/results/category-summary")
async def get_results_category_summary(
    strategy: str = Query("momentum", description="策略类型: momentum/weighted_score")
):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(trade_date) FROM strategy_results WHERE strategy_type = ?", (strategy,))
    latest_date = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT s.category, 
               COUNT(*) as total_count,
               SUM(CASE WHEN sr.momentum_20d > 0 THEN 1 ELSE 0 END) as up_count,
               SUM(CASE WHEN sr.momentum_20d < 0 THEN 1 ELSE 0 END) as down_count,
               AVG(sr.momentum_20d) as avg_momentum,
               MAX(sr.momentum_20d) as max_momentum,
               MIN(sr.momentum_20d) as min_momentum
        FROM strategy_results sr 
        JOIN symbols s ON sr.symbol_id = s.id
        WHERE sr.trade_date = ? AND sr.status = 'valid' AND sr.strategy_type = ?
        GROUP BY s.category
    """, (latest_date, strategy))
    rows = cursor.fetchall()
    
    category_map = {
        'market': '大盘指标',
        'industry': '行业指标',
        'bond': '债券指标'
    }
    
    summary = []
    for row in rows:
        summary.append({
            "category": row["category"],
            "category_name": category_map.get(row["category"], row["category"]),
            "total_count": row["total_count"],
            "up_count": row["up_count"],
            "down_count": row["down_count"],
            "avg_momentum": round(float(row["avg_momentum"]), 2) if row["avg_momentum"] else 0,
            "max_momentum": round(float(row["max_momentum"]), 2) if row["max_momentum"] else 0,
            "min_momentum": round(float(row["min_momentum"]), 2) if row["min_momentum"] else 0
        })
    
    conn.close()
    
    return {"data": summary, "trade_date": latest_date}


@app.get("/api/quality/summary")
async def get_quality_summary():
    conn = get_db()
    cursor = conn.cursor()
    
    summary = {}
    
    cursor.execute("SELECT COUNT(*) FROM symbols WHERE status = 1")
    summary["active_symbols"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM daily_prices")
    summary["total_price_records"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT trade_date) FROM daily_prices")
    summary["unique_dates"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
    latest_date = cursor.fetchone()[0]
    summary["latest_date"] = latest_date
    
    from app.utils.date_utils import get_expected_latest_trade_date
    expected_latest = get_expected_latest_trade_date()
    latest_date_obj = datetime.strptime(latest_date, "%Y-%m-%d").date()
    summary["days_since_latest"] = (expected_latest - latest_date_obj).days
    
    cursor.execute("""
        SELECT s.symbol, s.name, COUNT(*) as record_count
        FROM daily_prices dp 
        JOIN symbols s ON dp.symbol_id = s.id
        WHERE s.status = 1
        GROUP BY dp.symbol_id
        HAVING COUNT(*) = 0
    """)
    no_data_rows = cursor.fetchall()
    summary["symbols_without_data"] = len(no_data_rows)
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM (
            SELECT symbol_id, trade_date, COUNT(*) as cnt 
            FROM daily_prices 
            GROUP BY symbol_id, trade_date 
            HAVING cnt > 1
        )
    """)
    summary["duplicate_records"] = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM daily_prices 
        WHERE volume = 0 AND is_suspended = 0
    """)
    summary["zero_volume_non_suspended"] = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM daily_prices 
        WHERE close_price <= 0
    """)
    summary["negative_price"] = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT symbol_id, trade_date,
                   (close_price - LAG(close_price) OVER (PARTITION BY symbol_id ORDER BY trade_date)) / 
                   LAG(close_price) OVER (PARTITION BY symbol_id ORDER BY trade_date) * 100 as change_pct
            FROM daily_prices
        ) t
        WHERE change_pct IS NOT NULL AND ABS(change_pct) > 30
    """)
    summary["price_jumps"] = cursor.fetchone()[0]
    
    conn.close()
    
    return summary


@app.get("/api/quality/details")
async def get_quality_details(
    issue_type: str = Query(None, description="异常类型筛选")
):
    conn = get_db()
    cursor = conn.cursor()
    
    issues = []
    
    cursor.execute("""
        SELECT s.symbol, s.name, COUNT(*) as record_count
        FROM daily_prices dp 
        RIGHT JOIN symbols s ON dp.symbol_id = s.id
        WHERE s.status = 1
        GROUP BY s.id
        HAVING COUNT(dp.id) = 0
    """)
    for row in cursor.fetchall():
        issues.append({
            "type": "no_data",
            "symbol": row["symbol"],
            "name": row["name"],
            "description": "该标的没有任何价格数据"
        })
    
    cursor.execute("""
        SELECT s.symbol, s.name, dp.trade_date, dp.close_price, dp.volume
        FROM daily_prices dp 
        JOIN symbols s ON dp.symbol_id = s.id
        WHERE dp.close_price <= 0
    """)
    for row in cursor.fetchall():
        issues.append({
            "type": "negative_price",
            "symbol": row["symbol"],
            "name": row["name"],
            "trade_date": row["trade_date"],
            "close_price": float(row["close_price"]),
            "description": f"收盘价异常: {row['close_price']}"
        })
    
    cursor.execute("""
        SELECT s.symbol, s.name, dp.trade_date, dp.volume
        FROM daily_prices dp 
        JOIN symbols s ON dp.symbol_id = s.id
        WHERE dp.volume = 0 AND dp.is_suspended = 0
    """)
    for row in cursor.fetchall():
        issues.append({
            "type": "zero_volume",
            "symbol": row["symbol"],
            "name": row["name"],
            "trade_date": row["trade_date"],
            "description": "成交量为0但未停牌"
        })
    
    cursor.execute("""
        SELECT s.symbol, s.name, dp.trade_date, COUNT(*) as cnt
        FROM daily_prices dp 
        JOIN symbols s ON dp.symbol_id = s.id
        GROUP BY dp.symbol_id, dp.trade_date
        HAVING COUNT(*) > 1
    """)
    for row in cursor.fetchall():
        issues.append({
            "type": "duplicate",
            "symbol": row["symbol"],
            "name": row["name"],
            "trade_date": row["trade_date"],
            "count": row["cnt"],
            "description": f"重复数据: {row['cnt']} 条"
        })
    
    cursor.execute("""
        SELECT s.symbol, s.name, 
               (dp.close_price - LAG(dp.close_price) OVER (PARTITION BY dp.symbol_id ORDER BY dp.trade_date)) / 
               LAG(dp.close_price) OVER (PARTITION BY dp.symbol_id ORDER BY dp.trade_date) * 100 as change_pct,
               dp.trade_date, dp.close_price
        FROM daily_prices dp 
        JOIN symbols s ON dp.symbol_id = s.id
    """)
    for row in cursor.fetchall():
        change_pct = row["change_pct"]
        if change_pct is not None and abs(float(change_pct)) > 30:
            issues.append({
                "type": "price_jump",
                "symbol": row["symbol"],
                "name": row["name"],
                "trade_date": row["trade_date"],
                "change_pct": round(float(change_pct), 2),
                "close_price": float(row["close_price"]),
                "description": f"价格跳变: {round(float(change_pct), 2)}%"
            })
    
    conn.close()
    
    if issue_type:
        issues = [i for i in issues if i["type"] == issue_type]
    
    return {"issues": issues}


@app.get("/api/quality/coverage")
async def get_coverage():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.symbol, s.name, s.category, COUNT(*) as record_count,
               MIN(dp.trade_date) as first_date,
               MAX(dp.trade_date) as last_date
        FROM daily_prices dp 
        JOIN symbols s ON dp.symbol_id = s.id
        WHERE s.status = 1
        GROUP BY dp.symbol_id
        ORDER BY record_count DESC
    """)
    rows = cursor.fetchall()
    
    def count_trading_days(start_date, end_date):
        trading_days = 0
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:
                trading_days += 1
            current_date += timedelta(days=1)
        return trading_days

    coverage_data = []
    for row in rows:
        first_date = datetime.strptime(row["first_date"], "%Y-%m-%d").date()
        last_date = datetime.strptime(row["last_date"], "%Y-%m-%d").date()
        
        expected_days = count_trading_days(first_date, last_date)
        
        coverage = min((row["record_count"] / expected_days) * 100, 100) if expected_days > 0 else 0
        
        status = "good"
        if coverage < 60:
            status = "critical"
        elif coverage < 80:
            status = "warning"
        
        coverage_data.append({
            "symbol": row["symbol"],
            "name": row["name"],
            "category": row["category"],
            "record_count": row["record_count"],
            "first_date": row["first_date"],
            "last_date": row["last_date"],
            "coverage": round(coverage, 2),
            "status": status
        })
    
    conn.close()
    
    return {"data": coverage_data}


@app.get("/api/quality/trend")
async def get_quality_trend(days: int = 30):
    conn = get_db()
    cursor = conn.cursor()
    
    from app.utils.date_utils import get_expected_latest_trade_date, get_n_trading_days_ago
    end_date = get_expected_latest_trade_date()
    start_date = get_n_trading_days_ago(end_date, days)
    
    cursor.execute("""
        SELECT dp.trade_date, COUNT(DISTINCT dp.symbol_id) as symbol_count, COUNT(*) as record_count
        FROM daily_prices dp 
        WHERE dp.trade_date >= ? AND dp.trade_date <= ?
        GROUP BY dp.trade_date
        ORDER BY dp.trade_date
    """, (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
    
    rows = cursor.fetchall()
    
    trend_data = []
    for row in rows:
        trend_data.append({
            "date": row["trade_date"],
            "symbol_count": row["symbol_count"],
            "record_count": row["record_count"]
        })
    
    conn.close()
    
    return {"data": trend_data}


@app.post("/api/tasks/fetch")
async def trigger_fetch(
    symbol: str = Query(None, description="指定标的代码，为空则全部更新"),
    days: int = Query(60, description="回溯天数")
):
    try:
        cmd = ["python3", "main.py", "backfill", "--days", str(days)]
        if symbol:
            cmd.extend(["--symbol", symbol])
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=_BASE_DIR, timeout=300)
        
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout}
        else:
            return {"status": "error", "message": result.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/tasks/calculate")
async def trigger_calculate():
    try:
        result = subprocess.run(
            ["python3", "main.py", "calculate"],
            capture_output=True, text=True, cwd=_BASE_DIR, timeout=300
        )
        
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout}
        else:
            return {"status": "error", "message": result.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/tasks/repair")
async def repair_data(
    symbol: str = Query(None, description="指定标的代码，为空则修复全部")
):
    try:
        cmd = ["python3", "main.py", "repair"]
        if symbol:
            cmd.extend(["--symbol", symbol])
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=_BASE_DIR, timeout=300)
        
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout}
        else:
            return {"status": "error", "message": result.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/tasks/full")
async def trigger_full_pipeline():
    try:
        result = subprocess.run(
            ["python3", "main.py", "run"],
            capture_output=True, text=True, cwd=_BASE_DIR, timeout=600
        )
        
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout}
        else:
            return {"status": "error", "message": result.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/tasks/backfill-momentum")
async def trigger_backfill_momentum(
    symbol: str = Query(None, description="指定标的代码，为空则全部回溯")
):
    try:
        cmd = ["python3", "main.py", "backfill-momentum"]
        if symbol:
            cmd.extend(["--symbol", symbol])
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=_BASE_DIR, timeout=600)
        
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout}
        else:
            return {"status": "error", "message": result.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/tasks/backfill-weighted")
async def trigger_backfill_weighted(
    symbol: str = Query(None, description="指定标的代码，为空则全部回溯")
):
    try:
        cmd = ["python3", "main.py", "backfill-weighted"]
        if symbol:
            cmd.extend(["--symbol", symbol])
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=_BASE_DIR, timeout=600)
        
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout}
        else:
            return {"status": "error", "message": result.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/tasks/repair-jumps")
async def trigger_repair_jumps(
    symbol: str = Query(None, description="指定标的代码，为空则检测全部"),
    threshold: float = Query(15.0, description="价格跳变阈值百分比")
):
    try:
        cmd = ["python3", "main.py", "repair-jumps", "--threshold", str(threshold)]
        if symbol:
            cmd.extend(["--symbol", symbol])
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=_BASE_DIR, timeout=600)
        
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout}
        else:
            return {"status": "error", "message": result.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/system/status")
async def get_system_status():
    conn = get_db()
    cursor = conn.cursor()
    
    status = {}
    
    cursor.execute("SELECT COUNT(*) FROM symbols WHERE status = 1")
    status["active_symbols"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM daily_prices")
    status["price_records"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
    latest_price_date = cursor.fetchone()[0]
    status["latest_price_date"] = latest_price_date
    
    cursor.execute("SELECT MAX(trade_date) FROM strategy_results")
    latest_result_date = cursor.fetchone()[0]
    status["latest_result_date"] = latest_result_date
    
    # 使用最近交易日作为基准，避免周末/节假日误报"数据延迟"
    from app.utils.date_utils import get_expected_latest_trade_date
    expected_latest = get_expected_latest_trade_date()

    if latest_price_date:
        latest_date_obj = datetime.strptime(latest_price_date, "%Y-%m-%d").date()
        days_diff = (expected_latest - latest_date_obj).days
        status["price_delay_days"] = days_diff
        status["price_status"] = "up_to_date" if days_diff <= 0 else "delayed"
    
    if latest_result_date:
        latest_date_obj = datetime.strptime(latest_result_date, "%Y-%m-%d").date()
        days_diff = (expected_latest - latest_date_obj).days
        status["result_delay_days"] = days_diff
        status["result_status"] = "up_to_date" if days_diff <= 0 else "delayed"
    
    conn.close()
    
    return status


# ===================== 精选集组合 =====================

@app.get("/api/portfolio/top")
async def get_portfolio_top(
    symbols: str = Query(..., description="逗号分隔的标的代码列表"),
    top_n: int = Query(3, description="每个交易日取动量前N名"),
    strategy: str = Query("momentum", description="策略类型"),
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(50, description="每页大小")
):
    """精选集组合：统计指定标的组合内每日动量 Top N，按时间倒序返回。"""
    conn = get_db()
    cursor = conn.cursor()

    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        return {"data": [], "total": 0, "page": page, "page_size": page_size}

    placeholders = ",".join("?" * len(symbol_list))

    query = f"""
        SELECT sr.*, s.symbol, s.name, s.category
        FROM strategy_results sr
        JOIN symbols s ON sr.symbol_id = s.id
        WHERE sr.status = 'valid' AND sr.strategy_type = ?
          AND s.symbol IN ({placeholders})
    """
    params = [strategy] + symbol_list

    if start_date:
        query += " AND sr.trade_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND sr.trade_date <= ?"
        params.append(end_date)

    query += " ORDER BY sr.trade_date DESC, sr.momentum_20d DESC"

    cursor.execute(query, params)
    all_rows = cursor.fetchall()

    # 按交易日分组，每组取 Top N
    from collections import OrderedDict
    grouped = OrderedDict()
    for row in all_rows:
        d = row["trade_date"]
        if d not in grouped:
            grouped[d] = []
        grouped[d].append(dict(row))

    filtered = []
    for d, items in grouped.items():
        items.sort(key=lambda x: float(x["momentum_20d"]), reverse=True)
        for rank, item in enumerate(items[:top_n], 1):
            item["portfolio_rank"] = rank
            filtered.append(item)

    total = len(filtered)
    start_idx = (page - 1) * page_size
    paged = filtered[start_idx:start_idx + page_size]

    conn.close()
    return {"data": paged, "total": total, "page": page, "page_size": page_size}


app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
