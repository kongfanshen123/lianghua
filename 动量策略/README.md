# 动量策略量化分析平台

基于 20 日动量交易原理的量化策略系统，支持多数据源自动获取、动量计算与排序、Web 可视化管理、飞书推送。

---

## 功能概览

- **动量信号**：20 日量价动量计算、趋势分级、成交量确认、连续天数统计
- **加权评分策略**：年化收益率 × R² 拟合优度，衡量趋势稳定性
- **多数据源支持**：Sina（主）、AkShare、yfinance、Lude、Mock（测试），自动降级
- **数据质量管理**：覆盖率统计、异常检测、价格跳变修复、一键数据修复
- **Web 管理界面**：暗色主题、动量排名图、K 线图、历史信号查询、标的增删改查
- **飞书推送**：卡片消息 / 文本消息，支持排名变化指示（↑↓→）
- **定时调度**：APScheduler 每日 16:00 自动执行 Pipeline（fetch → validate → calc → push）
- **幂等设计**：数据库唯一约束 + 执行前检查，重复执行不产生脏数据

---

## 标的分类

### 大盘指标（market）

| 代码 | 名称 | 数据源 |
|------|------|--------|
| 000001 | 上证指数 | akshare |
| 000300 | 沪深300 | akshare |
| 000905 | 中证500 | akshare |
| 000852 | 中证1000 | sina |
| 932000 | 中证2000 | sina |
| 000688 | 科创50 | sina |
| 399006 | 创业板指 | akshare |
| 510300 | 沪深300ETF | sina |
| 510050 | 上证50ETF | sina |
| 510500 | 中证500ETF | sina |
| 159915 | 创业板ETF | sina |
| 588000 | 科创50ETF | sina |
| 513100 | 纳指ETF | sina |
| 513500 | 标普500ETF | sina |
| SPY | 标普500 | yfinance |
| QQQ | 纳指100 | yfinance |
| GLD | 黄金 | yfinance |

### 行业指标（industry）— 基于万德一级行业分类

| Wind一级行业 | 代码 | 名称 | 数据源 |
|---|------|------|--------|
| 能源 | 159930 | 能源ETF | sina |
| 材料 | 159944 | 材料ETF | sina |
| 工业 | 512660 | 军工ETF | sina |
| 可选消费 | 515030 | 新能源车ETF | sina |
| 可选消费 | 159928 | 消费ETF | sina |
| 日常消费 | 512690 | 酒ETF | sina |
| 医疗保健 | 512010 | 医药ETF | sina |
| 医疗保健 | 512170 | 医疗ETF | sina |
| 金融 | 512880 | 证券ETF | sina |
| 金融 | 512800 | 银行ETF | sina |
| 信息技术 | 512480 | 半导体ETF | sina |
| 信息技术 | 512760 | 芯片ETF | sina |
| 电信服务 | 515880 | 通信ETF | sina |
| 公用事业 | 159611 | 电力ETF | sina |
| 房地产 | 512200 | 地产ETF | sina |

### 债券指标（bond）

| 代码 | 名称 | 数据源 |
|------|------|--------|
| TLT | 长期国债ETF | yfinance |

---

## 快速开始

### 环境要求

- Python ≥ 3.8
- pip

### 安装步骤

```bash
# 1. 克隆项目
git clone <repository_url>
cd 量化工具/动量策略

# 2. 安装依赖
pip install -r requirements.txt

# 3. 创建数据/日志目录
mkdir -p data logs

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填写飞书配置等

# 5. 初始化数据库
python main.py db init

# 6. 导入初始标的
python main.py symbol import symbols_initial.json

# 7. 回填历史数据（90天）
python main.py backfill --days 90

# 8. 计算策略
python main.py calculate

# 9. 启动 Web 服务
python main.py scheduler
# 或仅启动 API 服务：
# uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

浏览器访问 `http://localhost:8000` 即可打开管理界面。

---

## CLI 命令

```bash
# 完整 Pipeline（fetch → validate → calc → push）
python main.py run [--date YYYY-MM-DD]

# 单步操作
python main.py fetch [--date YYYY-MM-DD]       # 获取数据
python main.py calculate [--date YYYY-MM-DD]    # 计算策略（动量 + 加权评分）
python main.py push [--date YYYY-MM-DD]         # 推送飞书

# 数据回填
python main.py backfill --days 90 [--symbol 000300]

# 策略回填
python main.py backfill-momentum [--symbol 000300]
python main.py backfill-weighted [--symbol 000300]

# 数据修复
python main.py repair [--symbol 000300]
python main.py repair-jumps [--symbol 000300] [--threshold 15.0]

# 标的管理
python main.py symbol list
python main.py symbol add --code 510300 --name 沪深300ETF --market A --data-source sina
python main.py symbol remove --code 510300
python main.py symbol update --code 510300 --status disable
python main.py symbol import symbols_initial.json
python main.py symbol verify

# 数据库
python main.py db init
python main.py db reset

# 启动定时调度
python main.py scheduler
```

---

## 策略说明

### 20 日量价动量

```
动量值 = (今日收盘价 - 20日前收盘价) / 20日前收盘价 × 100%
```

| 动量值范围 | 趋势强度 | 信号 |
|------------|----------|------|
| ≥ 15% | 热 | 强烈看多 |
| 5% ~ 15% | 温 | 看多 |
| 0% ~ 5% | 平 | 弱看多 |
| -5% ~ 0% | 平 | 弱看空 |
| -15% ~ -5% | 凉 | 看空 |
| ≤ -15% | 寒 | 强烈看空 |

**成交量确认**：计算近 5 日与前 15 日均量变化率，量价一致为有效信号。

### 加权评分策略（年收益 × R²）

```
年化收益率 = (今日收盘 / N日前收盘) ^ (252/N) - 1
R² = 线性回归拟合优度
评分 = 年化收益率 × R²
```

R² 越高表示趋势线性度越好，过滤高波动假突破。

---

## 数据架构

### 数据源

| 数据源 | 适用标的 | 复权支持 | 说明 |
|--------|----------|----------|------|
| Sina | A股指数、ETF | 不复权 | 主数据源，稳定性好 |
| AkShare | A股指数 | 前复权 | 部分接口不稳定 |
| yfinance | 美股、海外ETF | 自动复权 | 网络延迟较高 |
| Lude | A股 | - | 备用数据源 |
| Mock | 测试 | - | 模拟数据 |

### 数据校验规则

| 校验项 | 规则 | 处理 |
|--------|------|------|
| 价格异常 | 日间涨跌幅 > ±30% | 标记异常，跳过计算 |
| 停牌 | 成交量 = 0 | 标记停牌，跳过计算 |
| 流动性 | 20日均量 < 阈值 | 标记过滤，跳过计算 |
| 数据完整性 | 缺少必填字段 | 标记缺失，跳过计算 |
| 数据源切换 | 检测到数据源变更 | 清空旧数据，防止混合 |

---

## Web 界面

| 页面 | 功能 |
|------|------|
| 动量信号 | 最新排名、动量柱状图、策略切换（动量/加权评分）、分类筛选（大盘/行业/债券） |
| 历史信号 | 日期范围查询、标的/分类筛选、分页浏览 |
| 质量监控 | 覆盖率统计、异常列表、自动刷新 |
| 数据管理 | 标的列表、价格数据查询、K 线图、数据源标识 |

---

## 项目结构

```
动量策略/
├── main.py                     # 入口
├── cli.py → app/cli.py         # 命令行工具
├── symbols_initial.json        # 初始标的配置
├── requirements.txt            # 依赖清单
├── .env.example                # 环境变量模板
├── app/
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库连接
│   ├── models.py               # ORM 模型（Symbol/DailyPrice/StrategyResult）
│   ├── pipeline.py             # Pipeline 链式触发
│   ├── scheduler.py            # APScheduler 定时调度
│   ├── fetchers/               # 数据获取器
│   │   ├── base_fetcher.py
│   │   ├── sina_fetcher.py     # 新浪财经（主数据源）
│   │   ├── akshare_fetcher.py
│   │   ├── yfinance_fetcher.py
│   │   ├── lude_fetcher.py
│   │   └── mock_fetcher.py
│   ├── validators/
│   │   └── data_validator.py   # 数据校验（价格异常/停牌/流动性/日间跳变）
│   ├── strategies/
│   │   ├── momentum_strategy.py    # 20日动量策略
│   │   └── weighted_score_strategy.py  # 加权评分策略
│   ├── notifiers/
│   │   └── feishu_notifier.py  # 飞书推送
│   └── utils/
│       ├── date_utils.py       # 交易日判断（含2024-2026中国节假日）
│       └── logger.py
├── backend/
│   └── api.py                  # FastAPI 后端
├── frontend/
│   ├── index.html
│   └── static/
│       ├── css/style.css
│       └── js/
│           ├── api.js          # API 封装
│           ├── charts.js       # ECharts 图表
│           └── main.js         # 页面逻辑
├── tests/
│   ├── test_golden.py          # 黄金测试
│   └── golden/                 # 测试基线数据
└── data/                       # SQLite 数据库（运行时生成）
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.8+, FastAPI, SQLAlchemy, APScheduler |
| 数据源 | AkShare, yfinance, Sina Finance API |
| 数据库 | SQLite（可平滑迁移 PostgreSQL） |
| 前端 | 原生 JS + CSS, ECharts 5.4 |
| 通知 | 飞书开放平台 API |
| 测试 | pytest, pytest-cov |

---

## 免责声明

本系统提供的动量策略分析报告仅供参考，不构成任何投资建议或投资指导。

1. 历史表现不代表未来收益
2. 证券市场存在系统性风险，任何策略都可能失效
3. 本系统依赖第三方数据源，数据准确性不做保证
4. 投资有风险，交易需谨慎
