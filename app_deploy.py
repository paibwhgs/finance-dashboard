# -*- coding: utf-8 -*-
"""
金融数据可视化看板 v4.0 - 量化回测版
深色科技风，包含完整回测引擎、绩效评估、交易信号
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.tsa.arima.model import ARIMA
import warnings
warnings.filterwarnings('ignore')

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="金融数据可视化看板 v4.0 - 量化回测版",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 自定义 CSS 样式（深色科技风）====================
st.markdown("""
<style>
    .stApp { background-color: #0d1117; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    .stMetric {
        background-color: #21262d;
        border-radius: 10px;
        padding: 20px;
        border: 1px solid #30363d;
    }
    .stMarkdown, .stDataFrame, .stMetric { color: #f0f6fc; }
    h1, h2, h3 { color: #58a6ff !important; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; }
    [data-testid="stMetricLabel"] { color: #8b949e !important; }
    [data-testid="stMetricDelta"] { color: #3fb950 !important; }
    .dataframe {
        background-color: #21262d !important;
        color: #f0f6fc !important;
        border-radius: 8px;
    }
    .stTextInput > div > div > input, .stSelectbox > div > div > select {
        background-color: #0d1117;
        color: #f0f6fc;
        border: 1px solid #30363d;
    }
    .stButton > button {
        background-color: #238636;
        color: #ffffff;
        border: 1px solid #30363d;
        border-radius: 6px;
    }
    .stButton > button:hover { background-color: #2ea043; }
    
    /* 绩效指标卡片 */
    .metric-card {
        background: linear-gradient(135deg, #21262d 0%, #161b22 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }
    .metric-positive { color: #3fb950; }
    .metric-negative { color: #ff7b72; }
</style>
""", unsafe_allow_html=True)

# ==================== 工具函数 ====================

@st.cache_data
def check_data_quality(df, symbol):
    """数据质量检查"""
    issues = []
    score = 100
    
    if df.empty:
        return [], 0, "数据为空"
    
    missing_pct = df.isna().sum() / len(df) * 100
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col in df.columns and missing_pct.get(col, 0) > 0:
            pct = missing_pct[col]
            issues.append(f"⚠️ {col} 列缺失 {pct:.1f}% 数据")
            score -= min(20, pct * 2)
    
    if 'Close' in df.columns:
        daily_return = df['Close'].pct_change()
        outliers = (daily_return.abs() > 0.3).sum()
        if outliers > 0:
            outlier_dates = daily_return[daily_return.abs() > 0.3].index.strftime('%Y-%m-%d').tolist()[:3]
            issues.append(f"⚠️ 异常涨跌幅：{outliers} 天")
            score -= min(30, outliers * 5)
    
    if score >= 90:
        rating = "优秀"
        rating_color = "🟢"
    elif score >= 70:
        rating = "良好"
        rating_color = "🟡"
    elif score >= 50:
        rating = "一般"
        rating_color = "🟠"
    else:
        rating = "较差"
        rating_color = "🔴"
    
    return issues, score, f"{rating_color} {rating} ({score}分)"


@st.cache_data
def get_financial_info(symbol):
    """获取财务信息"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        financial_data = {
            '市值': info.get('marketCap', 'N/A'),
            '市盈率 (TTM)': info.get('trailingPE', 'N/A'),
            '市净率': info.get('priceToBook', 'N/A'),
            '股息率': info.get('dividendYield', 'N/A'),
            '贝塔系数': info.get('beta', 'N/A'),
            '52 周最高': info.get('fiftyTwoWeekHigh', 'N/A'),
            '52 周最低': info.get('fiftyTwoWeekLow', 'N/A'),
            '行业': info.get('industry', 'N/A'),
            '板块': info.get('sector', 'N/A'),
        }
        
        return financial_data, info.get('longBusinessSummary', 'N/A')
    except Exception as e:
        return {'错误': str(e)}, 'N/A'


def format_large_number(value):
    """格式化大数字"""
    if value == 'N/A' or value is None:
        return 'N/A'
    try:
        if isinstance(value, (int, float)):
            if value >= 1e12:
                return f"{value/1e12:.2f}T"
            elif value >= 1e9:
                return f"{value/1e9:.2f}B"
            elif value >= 1e6:
                return f"{value/1e6:.2f}M"
            elif value >= 1e3:
                return f"{value/1e3:.2f}K"
            else:
                return f"{value:.2f}"
        return str(value)
    except:
        return str(value)


# ==================== 回测引擎 ====================

def backtest_ma_crossover(data, short_window=20, long_window=50, initial_capital=100000):
    """
    均线交叉策略回测
    金叉买入（短期均线上穿长期均线），死叉卖出（短期均线下穿长期均线）
    """
    df = data.copy()
    
    # 计算均线
    df['MA_short'] = df['Close'].rolling(window=short_window).mean()
    df['MA_long'] = df['Close'].rolling(window=long_window).mean()
    
    # 生成信号 - 检测交叉动作（不是状态）
    df['signal'] = 0
    
    # 金叉：今天短期>长期，且昨天短期<长期
    golden_cross = (df['MA_short'] > df['MA_long']) & (df['MA_short'].shift(1) <= df['MA_long'].shift(1))
    df.loc[golden_cross, 'signal'] = 1
    
    # 死叉：今天短期<长期，且昨天短期>长期
    death_cross = (df['MA_short'] < df['MA_long']) & (df['MA_short'].shift(1) >= df['MA_long'].shift(1))
    df.loc[death_cross, 'signal'] = -1
    
    # 计算持仓（信号后一天执行）
    df['position'] = df['signal'].shift(1)
    
    # 计算收益
    df['returns'] = df['Close'].pct_change()
    df['strategy_returns'] = df['position'].shift(1) * df['returns']
    
    # 累计收益
    df['cumulative_returns'] = (1 + df['returns']).cumprod()
    df['cumulative_strategy_returns'] = (1 + df['strategy_returns']).cumprod()
    df['portfolio_value'] = initial_capital * df['cumulative_strategy_returns']
    
    # 生成交易记录
    trades = []
    position = 0
    entry_price = 0
    entry_date = None
    
    for idx, row in df.iterrows():
        if row['signal'] == 1 and position == 0:  # 金叉买入
            position = 1
            entry_price = row['Close']
            entry_date = idx
        elif row['signal'] == -1 and position == 1:  # 死叉卖出
            position = 0
            exit_price = row['Close']
            exit_date = idx
            pnl = (exit_price - entry_price) / entry_price * 100
            trades.append({
                '买入日期': entry_date.strftime('%Y-%m-%d'),
                '卖出日期': exit_date.strftime('%Y-%m-%d'),
                '买入价格': f"${entry_price:.2f}",
                '卖出价格': f"${exit_price:.2f}",
                '盈亏 (%)': f"{pnl:+.2f}%",
                '盈亏方向': '🟢' if pnl > 0 else '🔴'
            })
            entry_price = 0
            entry_date = None
    
    return df, trades


def backtest_rsi_strategy(data, rsi_period=14, oversold=30, overbought=70, initial_capital=100000):
    """
    RSI 超买超卖策略回测
    RSI < 30 买入，RSI > 70 卖出
    """
    df = data.copy()
    
    # 计算 RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 生成信号
    df['signal'] = 0
    df.loc[df['RSI'] < oversold, 'signal'] = 1  # 超卖买入
    df.loc[df['RSI'] > overbought, 'signal'] = -1  # 超买卖出
    
    # 计算持仓
    df['position'] = df['signal'].shift(1)
    
    # 计算收益
    df['returns'] = df['Close'].pct_change()
    df['strategy_returns'] = df['position'].shift(1) * df['returns']
    
    # 累计收益
    df['cumulative_returns'] = (1 + df['returns']).cumprod()
    df['cumulative_strategy_returns'] = (1 + df['strategy_returns']).cumprod()
    df['portfolio_value'] = initial_capital * df['cumulative_strategy_returns']
    
    # 生成交易记录
    trades = []
    position = 0
    entry_price = 0
    entry_date = None
    
    for idx, row in df.iterrows():
        if row['signal'] == 1 and position == 0:
            position = 1
            entry_price = row['Close']
            entry_date = idx
        elif row['signal'] == -1 and position == 1:
            position = 0
            exit_price = row['Close']
            exit_date = idx
            pnl = (exit_price - entry_price) / entry_price * 100
            trades.append({
                '买入日期': entry_date.strftime('%Y-%m-%d'),
                '卖出日期': exit_date.strftime('%Y-%m-%d'),
                '买入价格': f"${entry_price:.2f}",
                '卖出价格': f"${exit_price:.2f}",
                '盈亏 (%)': f"{pnl:+.2f}%",
                '盈亏方向': '🟢' if pnl > 0 else '🔴'
            })
            entry_price = 0
            entry_date = None
    
    return df, trades


def backtest_bollinger_strategy(data, bb_period=20, bb_std=2, initial_capital=100000):
    """
    布林带策略回测
    跌破下轨买入，突破上轨卖出
    """
    df = data.copy()
    
    # 计算布林带
    df['MA'] = df['Close'].rolling(window=bb_period).mean()
    df['STD'] = df['Close'].rolling(window=bb_period).std()
    df['Upper'] = df['MA'] + (bb_std * df['STD'])
    df['Lower'] = df['MA'] - (bb_std * df['STD'])
    
    # 生成信号
    df['signal'] = 0
    df.loc[df['Close'] < df['Lower'], 'signal'] = 1  # 跌破下轨买入
    df.loc[df['Close'] > df['Upper'], 'signal'] = -1  # 突破上轨卖出
    
    # 计算持仓
    df['position'] = df['signal'].shift(1)
    
    # 计算收益
    df['returns'] = df['Close'].pct_change()
    df['strategy_returns'] = df['position'].shift(1) * df['returns']
    
    # 累计收益
    df['cumulative_returns'] = (1 + df['returns']).cumprod()
    df['cumulative_strategy_returns'] = (1 + df['strategy_returns']).cumprod()
    df['portfolio_value'] = initial_capital * df['cumulative_strategy_returns']
    
    # 生成交易记录
    trades = []
    position = 0
    entry_price = 0
    entry_date = None
    
    for idx, row in df.iterrows():
        if row['signal'] == 1 and position == 0:
            position = 1
            entry_price = row['Close']
            entry_date = idx
        elif row['signal'] == -1 and position == 1:
            position = 0
            exit_price = row['Close']
            exit_date = idx
            pnl = (exit_price - entry_price) / entry_price * 100
            trades.append({
                '买入日期': entry_date.strftime('%Y-%m-%d'),
                '卖出日期': exit_date.strftime('%Y-%m-%d'),
                '买入价格': f"${entry_price:.2f}",
                '卖出价格': f"${exit_price:.2f}",
                '盈亏 (%)': f"{pnl:+.2f}%",
                '盈亏方向': '🟢' if pnl > 0 else '🔴'
            })
            entry_price = 0
            entry_date = None
    
    return df, trades


def calculate_performance_metrics(df, trades, initial_capital=100000):
    """计算绩效指标"""
    if df.empty or len(df) < 2:
        return {}
    
    # 基础数据
    total_days = len(df)
    total_returns = df['cumulative_strategy_returns'].iloc[-1] - 1
    
    # 年化收益率（假设 252 个交易日）
    years = total_days / 252
    annual_return = (1 + total_returns) ** (1 / years) - 1 if years > 0 else 0
    
    # 波动率
    daily_vol = df['strategy_returns'].std()
    annual_vol = daily_vol * np.sqrt(252)
    
    # 夏普比率（假设无风险利率 2%）
    risk_free_rate = 0.02
    sharpe_ratio = (annual_return - risk_free_rate) / annual_vol if annual_vol > 0 else 0
    
    # 最大回撤
    cumulative = df['cumulative_strategy_returns']
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # 胜率
    winning_trades = len([t for t in trades if '🟢' in t['盈亏方向']])
    total_trades = len(trades)
    win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
    
    # 平均盈亏比
    if trades:
        winning_pnls = [float(t['盈亏 (%)'].replace('%', '').replace('+', '')) for t in trades if '🟢' in t['盈亏方向']]
        losing_pnls = [float(t['盈亏 (%)'].replace('%', '')) for t in trades if '🔴' in t['盈亏方向']]
        avg_win = np.mean(winning_pnls) if winning_pnls else 0
        avg_loss = abs(np.mean(losing_pnls)) if losing_pnls else 1
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
    else:
        profit_loss_ratio = 0
    
    return {
        '总收益率': f"{total_returns * 100:.2f}%",
        '年化收益率': f"{annual_return * 100:.2f}%",
        '夏普比率': f"{sharpe_ratio:.2f}",
        '最大回撤': f"{max_drawdown * 100:.2f}%",
        '年化波动率': f"{annual_vol * 100:.2f}%",
        '交易次数': total_trades,
        '胜率': f"{win_rate:.1f}%",
        '盈亏比': f"{profit_loss_ratio:.2f}",
        '最终资金': f"${df['portfolio_value'].iloc[-1]:,.2f}",
        '总天数': total_days
    }


# ==================== 侧边栏配置 ====================
with st.sidebar:
    st.title("⚙️ 配置面板")
    st.markdown("---")
    
    # 功能模式选择
    st.subheader("🎯 功能模式")
    mode = st.radio(
        "选择工作模式",
        options=["📊 数据查看", "🔬 量化回测"],
        index=0,
        help="数据查看：查看行情、财务数据、时间序列分析\n量化回测：策略回测、绩效评估"
    )
    
    st.markdown("---")
    
    # 股票选择
    st.subheader("📊 股票/指数选择")
    default_symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "^GSPC", "^DJI", "^IXIC"]
    selected_symbol = st.selectbox(
        "选择要查看的股票/指数",
        options=default_symbols,
        index=0
    )
    
    # 自定义股票代码输入
    st.subheader("🔤 自定义股票代码")
    custom_symbol = st.text_input(
        "输入股票代码",
        placeholder="如：600519.SS, BTC-USD",
        help="A 股：600519.SS | 港股：0700.HK | 加密货币：BTC-USD"
    )
    
    if custom_symbol:
        selected_symbol = custom_symbol
    
    st.markdown("---")
    
    # 时间周期选择
    st.subheader("🕐 时间周期")
    timeframe_map = {
        "日线": "1d",
        "周线": "1wk",
        "月线": "1mo"
    }
    
    timeframe_display = st.selectbox(
        "选择 K 线周期",
        options=list(timeframe_map.keys()),
        index=0
    )
    timeframe = timeframe_map[timeframe_display]
    
    st.markdown("---")
    
    # 时间范围
    st.subheader("📅 时间范围")
    time_range = st.selectbox(
        "选择时间范围",
        options=["1 个月", "3 个月", "6 个月", "1 年", "2 年", "5 年", "全部"],
        index=3
    )
    
    time_range_map = {
        "1 个月": 30,
        "3 个月": 90,
        "6 个月": 180,
        "1 年": 365,
        "2 年": 730,
        "5 年": 1825,
        "全部": None
    }
    
    days = time_range_map[time_range]
    
    if days:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
    else:
        start_date = datetime(2000, 1, 1)
        end_date = datetime.now()
    
    st.markdown("---")
    
    # 复权处理
    st.subheader("🔄 复权处理")
    adjust_type = st.radio(
        "价格调整方式",
        options=["前复权", "后复权", "不复权"],
        index=0
    )
    
    adjust_map = {"前复权": True, "后复权": False, "不复权": False}
    auto_adjust = adjust_map[adjust_type]
    
    st.markdown("---")
    
    # 高级模式开关
    st.subheader("🔓 高级模式")
    advanced_mode = st.checkbox("启用高级模式", value=False, help="开启后显示时间序列分析、平稳性检验等专业功能")
    
    st.markdown("---")
    
    # 技术指标
    st.subheader("📉 技术指标")
    show_ma = st.checkbox("显示移动平均线", value=True)
    ma_period = st.slider("移动平均周期", min_value=5, max_value=200, value=20)
    show_volume = st.checkbox("显示成交量", value=True)
    
    st.markdown("---")
    
    # 刷新按钮
    st.subheader("🔄 数据刷新")
    if st.button("刷新数据", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    
    # 关于
    st.markdown("### ℹ️ 关于")
    st.markdown("""
    **版本**: v4.0 (量化回测版)
    
    **数据来源**: Yahoo Finance
    
    **技术栈**: Streamlit + Plotly + statsmodels
    
    **核心功能**:
    - ✅ 均线交叉/RSI/布林带策略回测
    - ✅ 完整绩效评估（夏普、回撤、胜率）
    - ✅ 交易记录分析
    
    **高级模式** (需手动开启):
    - ✅ 趋势分解
    - ✅ ACF/PACF 自相关分析
    - ✅ ADF 平稳性检验
    - ✅ ARIMA 预测
    """)

# ==================== 主页面 ====================
st.title("📈 金融数据可视化看板 v4.0")
st.markdown("### 量化回测版 - 策略回测 · 绩效评估 · 交易信号")
st.markdown("---")

# ==================== 数据获取 ====================
@st.cache_data(ttl=1800)  # 缓存 30 分钟
def get_stock_data(symbol, start, end, interval, auto_adjust):
    """获取股票数据（使用 Alpha Vantage API 避免速率限制）"""
    import time
    import requests
    
    # Alpha Vantage API Key
    API_KEY = "N112YKPQ3O5P6PYA"
    MAX_RETRIES = 3
    
    for attempt in range(MAX_RETRIES):
        try:
            # 确定数据量
            days = (end - start).days
            if days <= 30:
                outputsize = 'compact'
            else:
                outputsize = 'full'
            
            # 调用 Alpha Vantage API
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize={outputsize}&datatype=json&apikey={API_KEY}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 检查是否触发 API 限制
            if "Note" in data:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(5)
                    continue
                return pd.DataFrame(), "Alpha Vantage API 速率限制，请等待 1 分钟后重试"
            
            # 提取时间序列数据
            if "Time Series (Daily)" not in data:
                return pd.DataFrame(), f"无法获取 {symbol} 的数据"
            
            time_series = data["Time Series (Daily)"]
            
            # 转换为 DataFrame
            df = pd.DataFrame.from_dict(time_series, orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            
            # 重命名列
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            df = df.astype(float)
            
            # 筛选时间范围
            df = df[(df.index >= start) & (df.index <= end)]
            
            if df.empty:
                return pd.DataFrame(), f"无法获取 {symbol} 的数据"
            
            return df, None
            
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
                continue
            return pd.DataFrame(), f"数据获取失败：{str(e)}"
    
    return pd.DataFrame(), "数据获取失败"

with st.spinner(f"📡 正在获取 {selected_symbol} 的数据..."):
    stock_data, error = get_stock_data(selected_symbol, start_date, end_date, timeframe, auto_adjust)
    
    if error or stock_data.empty:
        st.error(f"❌ 数据获取失败：{error if error else '数据为空'}")
        st.stop()

# ==================== 数据质量检查 ====================
st.subheader("📋 数据质量报告")
quality_issues, quality_score, quality_rating = check_data_quality(stock_data, selected_symbol)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown(f"#### 质量评级：{quality_rating}")
with col2:
    st.metric("数据完整性", f"{max(0, 100 - len(quality_issues) * 10)}%")
with col3:
    st.metric("记录数", f"{len(stock_data)} 条")

if quality_score < 70:
    with st.expander("📋 查看详细问题", expanded=False):
        for issue in quality_issues:
            st.write(issue)

st.markdown("---")

# ==================== 模式选择 ====================
if mode == "📊 数据查看":
    # ========== 数据查看模式 ==========
    
    # 财务数据
    st.subheader("💰 财务数据概览")
    with st.spinner("📊 正在获取财务数据..."):
        financial_data, business_summary = get_financial_info(selected_symbol)
    
    fin_col1, fin_col2 = st.columns(2)
    with fin_col1:
        st.markdown("#### 📊 关键指标")
        if '错误' not in financial_data:
            fin_df = pd.DataFrame({
                '指标': list(financial_data.keys()),
                '数值': [format_large_number(v) for v in financial_data.values()]
            })
            st.dataframe(fin_df, use_container_width=True, height=300)
        else:
            st.warning(f"⚠️ 财务数据获取失败：{financial_data['错误']}")
    
    with fin_col2:
        st.markdown("#### 📝 公司简介")
        if business_summary != 'N/A':
            st.markdown(f"<div style='background-color: #21262d; padding: 15px; border-radius: 8px; height: 300px; overflow-y: auto;'>{business_summary}</div>", unsafe_allow_html=True)
        else:
            st.info("暂无公司简介信息")
    
    st.markdown("---")
    
    # 行情概览
    st.subheader("💹 实时行情")
    current_price = stock_data['Close'].iloc[-1]
    prev_price = stock_data['Close'].iloc[-2] if len(stock_data) > 1 else current_price
    price_change = current_price - prev_price
    price_change_pct = (price_change / prev_price) * 100
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("当前价格", f"${current_price:.2f}", f"{price_change:+.2f} ({price_change_pct:+.2f}%)")
    with col2:
        st.metric("今日区间", f"${stock_data['Low'].iloc[-1]:.2f} - ${stock_data['High'].iloc[-1]:.2f}")
    with col3:
        vol = stock_data['Volume'].iloc[-1]
        st.metric("成交量", f"{vol/1e6:.2f}M" if vol > 0 else "N/A")
    with col4:
        st.metric("开盘价", f"${stock_data['Open'].iloc[-1]:.2f}")
    
    st.markdown("---")
    
    # K 线图
    st.subheader(f"📊 K 线图 - {selected_symbol}")
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3], subplot_titles=('价格走势', '成交量'))
    
    fig.add_trace(go.Candlestick(x=stock_data.index, open=stock_data['Open'], high=stock_data['High'], low=stock_data['Low'], close=stock_data['Close'], name='价格', increasing_line_color='#58a6ff', decreasing_line_color='#ff7b72'), row=1, col=1)
    
    if show_ma and len(stock_data) >= ma_period:
        ma = stock_data['Close'].rolling(window=ma_period).mean()
        fig.add_trace(go.Scatter(x=stock_data.index, y=ma, name=f'MA{ma_period}', line=dict(color='#3fb950', width=2, dash='dash')), row=1, col=1)
    
    if show_volume:
        colors_volume = ['#3fb950' if stock_data['Close'].iloc[i] >= stock_data['Open'].iloc[i] else '#ff7b72' for i in range(len(stock_data))]
        fig.add_trace(go.Bar(x=stock_data.index, y=stock_data['Volume'], name='成交量', marker_color=colors_volume, opacity=0.5), row=2, col=1)
    
    fig.update_layout(height=700, showlegend=True, plot_bgcolor='#0d1117', paper_bgcolor='#0d1117')
    fig.update_xaxes(showgrid=True, gridcolor='#21262d', linecolor='#30363d')
    fig.update_yaxes(showgrid=True, gridcolor='#21262d', linecolor='#30363d')
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ========== 高级模式：时间序列分析 ==========
    if advanced_mode:
        st.markdown("---")
        st.subheader(" 时间序列分析（高级模式）")
        
        ts_data = stock_data.copy()
        ts_data['log_return'] = np.log(ts_data['Close'] / ts_data['Close'].shift(1)).dropna()
        
        ts_tab1, ts_tab2, ts_tab3, ts_tab4 = st.tabs(["📊 趋势分解", "📈 ACF/PACF", "📉 平稳性检验", "🔮 预测"])
        
        with ts_tab1:
            st.markdown("### 趋势分解 (Trend Decomposition)")
            if len(ts_data) >= 30:
                try:
                    decomp = seasonal_decompose(ts_data['Close'].dropna(), model='additive', period=min(30, len(ts_data)//2), extrapolate_trend='freq')
                    fig_decomp = make_subplots(rows=4, cols=1, shared_xaxes=True, subplot_titles=('原始序列', '趋势项', '季节项', '残差项'), row_heights=[0.25, 0.25, 0.25, 0.25])
                    fig_decomp.add_trace(go.Scatter(x=decomp.observed.index, y=decomp.observed.values, line=dict(color='#58a6ff')), row=1, col=1)
                    fig_decomp.add_trace(go.Scatter(x=decomp.trend.index, y=decomp.trend.values, line=dict(color='#3fb950')), row=2, col=1)
                    fig_decomp.add_trace(go.Scatter(x=decomp.seasonal.index, y=decomp.seasonal.values, line=dict(color='#d29922')), row=3, col=1)
                    fig_decomp.add_trace(go.Scatter(x=decomp.resid.index, y=decomp.resid.values, line=dict(color='#f78166')), row=4, col=1)
                    fig_decomp.update_layout(height=700, showlegend=False, plot_bgcolor='#0d1117', paper_bgcolor='#0d1117')
                    st.plotly_chart(fig_decomp, use_container_width=True)
                except Exception as e:
                    st.warning(f"⚠️ 分解失败：{e}")
            else:
                st.warning("⚠️ 数据不足 30 条")
        
        with ts_tab2:
            st.markdown("### 自相关分析 (ACF / PACF)")
            returns = ts_data['log_return'].dropna()
            if len(returns) > 10:
                max_lag = min(40, len(returns)//4)
                acf_vals = acf(returns, nlags=max_lag, fft=True)
                pacf_vals = pacf(returns, nlags=max_lag, method='ywadjusted')
                conf = 1.96 / np.sqrt(len(returns))
                
                fig_acf = make_subplots(rows=2, cols=1, subplot_titles=('ACF', 'PACF'))
                fig_acf.add_trace(go.Bar(x=list(range(len(acf_vals))), y=acf_vals, marker_color=['#3fb950' if v>0 else '#ff7b72' for v in acf_vals], name='ACF'), row=1, col=1)
                fig_acf.add_hline(y=conf, line_dash='dash', line_color='#8b949e', row=1, col=1)
                fig_acf.add_hline(y=-conf, line_dash='dash', line_color='#8b949e', row=1, col=1)
                fig_acf.add_trace(go.Bar(x=list(range(len(pacf_vals))), y=pacf_vals, marker_color=['#3fb950' if v>0 else '#ff7b72' for v in pacf_vals], name='PACF'), row=2, col=1)
                fig_acf.add_hline(y=conf, line_dash='dash', line_color='#8b949e', row=2, col=1)
                fig_acf.add_hline(y=-conf, line_dash='dash', line_color='#8b949e', row=2, col=1)
                fig_acf.update_layout(height=500, showlegend=False, plot_bgcolor='#0d1117', paper_bgcolor='#0d1117')
                st.plotly_chart(fig_acf, use_container_width=True)
                
                st.info("""
                **解读提示**:
                - ACF 缓慢衰减 → 序列可能不平稳
                - ACF/PACF 截尾位置 → 帮助确定 ARIMA 参数 (p,d,q)
                """)
            else:
                st.warning("⚠️ 数据不足")
        
        with ts_tab3:
            st.markdown("### ADF 平稳性检验")
            close_prices = ts_data['Close'].dropna()
            adf_result = adfuller(close_prices, regression='c', autolag='AIC')
            returns = ts_data['log_return'].dropna()
            adf_ret = adfuller(returns, regression='c', autolag='AIC')
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 收盘价")
                st.markdown(f"ADF 统计量：`{adf_result[0]:.4f}`\np 值：`{adf_result[1]:.6f}`")
                st.success("✅ 平稳") if adf_result[1] < 0.05 else st.error("❌ 不平稳")
            with col2:
                st.markdown("#### 收益率")
                st.markdown(f"ADF 统计量：`{adf_ret[0]:.4f}`\np 值：`{adf_ret[1]:.6f}`")
                st.success("✅ 平稳") if adf_ret[1] < 0.05 else st.error("❌ 不平稳")
            
            st.info("""
            **结论**: 通常收盘价不平稳（有趋势），但收益率平稳。
            这意味着可以对收益率建模，或对价格差分后再建模。
            """)
        
        with ts_tab4:
            st.markdown("### ARIMA 预测")
            if len(ts_data['Close'].dropna()) > 50:
                with st.spinner("🔄 拟合 ARIMA 模型..."):
                    try:
                        model = ARIMA(ts_data['Close'].dropna(), order=(5,1,5))
                        model_fit = model.fit()
                        forecast_days = st.slider("预测天数", 5, 60, 30)
                        forecast = model_fit.get_forecast(steps=forecast_days)
                        forecast_mean = forecast.predicted_mean
                        forecast_ci = forecast.conf_int(alpha=0.05)
                        
                        fig_fc = go.Figure()
                        fig_fc.add_trace(go.Scatter(x=ts_data['Close'].dropna().index, y=ts_data['Close'].dropna().values, name='历史', line=dict(color='#58a6ff')))
                        fig_fc.add_trace(go.Scatter(x=forecast_mean.index, y=forecast_mean.values, name='预测', line=dict(color='#3fb950', dash='dash')))
                        fig_fc.add_trace(go.Scatter(x=list(forecast_ci.index)+list(forecast_ci.index)[::-1],
                                                    y=list(forecast_ci.iloc[:,0])+list(forecast_ci.iloc[:,1])[::-1],
                                                    fill='toself', fillcolor='rgba(210,153,34,0.3)', line=dict(color='rgba(0,0,0,0)'), name='95% 置信区间'))
                        fig_fc.update_layout(height=400, showlegend=True, plot_bgcolor='#0d1117', paper_bgcolor='#0d1117')
                        st.plotly_chart(fig_fc, use_container_width=True)
                        
                        st.info(f"预测终点价格：${forecast_mean.iloc[-1]:.2f} (95% CI: ${forecast_ci.iloc[-1,0]:.2f} - ${forecast_ci.iloc[-1,1]:.2f})")
                        st.warning("⚠️ 预测仅供参考，不构成投资建议")
                    except Exception as e:
                        st.error(f"❌ 预测失败：{e}")
            else:
                st.warning("⚠️ 需要至少 50 条数据")
    
    st.markdown("---")

elif mode == "🔬 量化回测":
    # ========== 量化回测模式 ==========
    
    st.subheader("🔬 策略配置")
    
    # 策略选择
    strategy = st.selectbox(
        "选择回测策略",
        options=["均线交叉策略", "RSI 超买超卖策略", "布林带策略"],
        index=0
    )
    
    # 策略参数
    st.markdown("#### ⚙️ 策略参数")
    
    if strategy == "均线交叉策略":
        col1, col2 = st.columns(2)
        with col1:
            short_window = st.slider("短期均线周期", min_value=5, max_value=50, value=20)
        with col2:
            long_window = st.slider("长期均线周期", min_value=20, max_value=200, value=50)
        strategy_params = {'short_window': short_window, 'long_window': long_window}
        
    elif strategy == "RSI 超买超卖策略":
        col1, col2, col3 = st.columns(3)
        with col1:
            rsi_period = st.slider("RSI 周期", min_value=7, max_value=28, value=14)
        with col2:
            oversold = st.slider("超卖阈值", min_value=20, max_value=40, value=30)
        with col3:
            overbought = st.slider("超买阈值", min_value=60, max_value=80, value=70)
        strategy_params = {'rsi_period': rsi_period, 'oversold': oversold, 'overbought': overbought}
        
    elif strategy == "布林带策略":
        col1, col2 = st.columns(2)
        with col1:
            bb_period = st.slider("布林带周期", min_value=10, max_value=50, value=20)
        with col2:
            bb_std = st.slider("标准差倍数", min_value=1.5, max_value=3.0, value=2.0)
        strategy_params = {'bb_period': bb_period, 'bb_std': bb_std}
    
    # 初始资金
    initial_capital = st.number_input("初始资金 ($)", min_value=10000, max_value=10000000, value=100000, step=10000)
    
    # 开始回测按钮
    st.markdown("---")
    if st.button("🚀 开始回测", use_container_width=True, type="primary"):
        with st.spinner(" 正在运行回测..."):
            # 执行回测
            if strategy == "均线交叉策略":
                backtest_data, trades = backtest_ma_crossover(stock_data, **strategy_params, initial_capital=initial_capital)
            elif strategy == "RSI 超买超卖策略":
                backtest_data, trades = backtest_rsi_strategy(stock_data, **strategy_params, initial_capital=initial_capital)
            elif strategy == "布林带策略":
                backtest_data, trades = backtest_bollinger_strategy(stock_data, **strategy_params, initial_capital=initial_capital)
            
            # 计算绩效指标
            metrics = calculate_performance_metrics(backtest_data, trades, initial_capital)
            
            st.success("✅ 回测完成！")
            
            # 绩效指标
            st.subheader("📊 绩效评估")
            
            # 关键指标卡片
            metric_cols = st.columns(4)
            with metric_cols[0]:
                total_return = metrics.get('总收益率', 'N/A')
                is_positive = '+' in total_return or float(total_return.replace('%', '').replace('-', '')) > 0
                st.markdown(f"""
                <div class='metric-card'>
                    <div style='color: #8b949e; font-size: 14px;'>总收益率</div>
                    <div style='font-size: 24px; font-weight: bold; color: {"#3fb950" if is_positive else "#ff7b72"}'>{total_return}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with metric_cols[1]:
                annual_return = metrics.get('年化收益率', 'N/A')
                is_positive = '+' in annual_return or float(annual_return.replace('%', '').replace('-', '')) > 0
                st.markdown(f"""
                <div class='metric-card'>
                    <div style='color: #8b949e; font-size: 14px;'>年化收益率</div>
                    <div style='font-size: 24px; font-weight: bold; color: {"#3fb950" if is_positive else "#ff7b72"}'>{annual_return}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with metric_cols[2]:
                sharpe = metrics.get('夏普比率', 'N/A')
                sharpe_val = float(sharpe) if sharpe != 'N/A' else 0
                st.markdown(f"""
                <div class='metric-card'>
                    <div style='color: #8b949e; font-size: 14px;'>夏普比率</div>
                    <div style='font-size: 24px; font-weight: bold; color: {"#3fb950" if sharpe_val > 1 else "#ff7b72" if sharpe_val < 0 else "#d29922"}'>{sharpe}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with metric_cols[3]:
                max_dd = metrics.get('最大回撤', 'N/A')
                st.markdown(f"""
                <div class='metric-card'>
                    <div style='color: #8b949e; font-size: 14px;'>最大回撤</div>
                    <div style='font-size: 24px; font-weight: bold; color: #ff7b72'>{max_dd}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # 详细指标
            st.markdown("#### 📈 详细指标")
            detail_col1, detail_col2 = st.columns(2)
            with detail_col1:
                st.metric("交易次数", metrics.get('交易次数', 'N/A'))
                st.metric("胜率", metrics.get('胜率', 'N/A'))
                st.metric("盈亏比", metrics.get('盈亏比', 'N/A'))
            with detail_col2:
                st.metric("年化波动率", metrics.get('年化波动率', 'N/A'))
                st.metric("最终资金", metrics.get('最终资金', 'N/A'))
                st.metric("回测天数", metrics.get('总天数', 'N/A'))
            
            st.markdown("---")
            
            # 资金曲线图
            st.subheader("💰 资金曲线")
            
            fig_equity = go.Figure()
            fig_equity.add_trace(go.Scatter(x=backtest_data.index, y=backtest_data['portfolio_value'], name='策略资金', line=dict(color='#58a6ff', width=2)))
            fig_equity.add_trace(go.Scatter(x=backtest_data.index, y=backtest_data['cumulative_returns'] * initial_capital, name='买入持有', line=dict(color='#8b949e', width=2, dash='dash')))
            fig_equity.update_layout(height=400, showlegend=True, plot_bgcolor='#0d1117', paper_bgcolor='#0d1117')
            fig_equity.update_xaxes(showgrid=True, gridcolor='#21262d', linecolor='#30363d')
            fig_equity.update_yaxes(showgrid=True, gridcolor='#21262d', linecolor='#30363d', title="资金 ($)")
            
            st.plotly_chart(fig_equity, use_container_width=True)
            
            # 带交易信号的 K 线图
            st.subheader("📊 交易信号图")
            
            fig_signal = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3], subplot_titles=('价格与交易信号', '成交量'))
            
            # K 线
            fig_signal.add_trace(go.Candlestick(x=stock_data.index, open=stock_data['Open'], high=stock_data['High'], low=stock_data['Low'], close=stock_data['Close'], name='价格', increasing_line_color='#58a6ff', decreasing_line_color='#ff7b72'), row=1, col=1)
            
            # 买入信号
            buy_signals = backtest_data[backtest_data['signal'] == 1]
            if len(buy_signals) > 0:
                fig_signal.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Close'], mode='markers', name='买入信号', marker=dict(symbol='triangle-up', size=12, color='#3fb950')), row=1, col=1)
            
            # 卖出信号
            sell_signals = backtest_data[backtest_data['signal'] == -1]
            if len(sell_signals) > 0:
                fig_signal.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['Close'], mode='markers', name='卖出信号', marker=dict(symbol='triangle-down', size=12, color='#ff7b72')), row=1, col=1)
            
            # 成交量
            colors_volume = ['#3fb950' if stock_data['Close'].iloc[i] >= stock_data['Open'].iloc[i] else '#ff7b72' for i in range(len(stock_data))]
            fig_signal.add_trace(go.Bar(x=stock_data.index, y=stock_data['Volume'], name='成交量', marker_color=colors_volume, opacity=0.5), row=2, col=1)
            
            fig_signal.update_layout(height=700, showlegend=True, plot_bgcolor='#0d1117', paper_bgcolor='#0d1117')
            fig_signal.update_xaxes(showgrid=True, gridcolor='#21262d', linecolor='#30363d')
            fig_signal.update_yaxes(showgrid=True, gridcolor='#21262d', linecolor='#30363d')
            
            st.plotly_chart(fig_signal, use_container_width=True)
            
            # 交易记录
            st.subheader("📋 交易记录")
            if trades:
                trades_df = pd.DataFrame(trades)
                st.dataframe(trades_df, use_container_width=True, height=300)
                
                # 下载交易记录
                csv = trades_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 下载交易记录 CSV",
                    data=csv,
                    file_name=f"{selected_symbol}_{strategy}_trades_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("ℹ️ 回测期间无交易记录")
            
            # 风险提示
            st.warning("""
            ⚠️ **风险提示**: 
            - 回测结果基于历史数据，不代表未来表现
            - 未考虑交易成本（佣金、滑点等）
            - 过往业绩不预示未来结果
            - 投资有风险，入市需谨慎
            """)

# ==================== 页脚 ====================
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: #8b949e; padding: 20px;'>
        <p>📈 金融数据可视化看板 v4.0 | 数据来源：Yahoo Finance | 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p style='font-size: 12px;'>深色科技风设计 | Streamlit + Plotly + 量化回测引擎</p>
    </div>
    """,
    unsafe_allow_html=True
)
