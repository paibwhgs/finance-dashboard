# -*- coding: utf-8 -*-
"""
金融数据可视化看板 - Streamlit Web 应用
深色科技风，类似会议室预约系统风格
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="金融数据可视化看板",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 自定义 CSS 样式（深色科技风）====================
st.markdown("""
<style>
    /* 主背景色 */
    .stApp {
        background-color: #0d1117;
    }
    
    /* 侧边栏背景 */
    [data-testid="stSidebar"] {
        background-color: #161b22;
    }
    
    /* 卡片背景 */
    .stMetric {
        background-color: #21262d;
        border-radius: 10px;
        padding: 20px;
        border: 1px solid #30363d;
    }
    
    /* 文字颜色 */
    .stMarkdown, .stDataFrame, .stMetric {
        color: #f0f6fc;
    }
    
    /* 标题颜色 */
    h1, h2, h3 {
        color: #58a6ff !important;
    }
    
    /* 指标数字颜色 */
    [data-testid="stMetricValue"] {
        color: #58a6ff !important;
    }
    
    /* 指标标签颜色 */
    [data-testid="stMetricLabel"] {
        color: #8b949e !important;
    }
    
    /* 指标 delta 颜色 */
    [data-testid="stMetricDelta"] {
        color: #3fb950 !important;
    }
    
    /* 表格样式 */
    .dataframe {
        background-color: #21262d !important;
        color: #f0f6fc !important;
        border-radius: 8px;
    }
    
    /* 输入框样式 */
    .stTextInput > div > div > input, .stSelectbox > div > div > select {
        background-color: #0d1117;
        color: #f0f6fc;
        border: 1px solid #30363d;
    }
    
    /* 按钮样式 */
    .stButton > button {
        background-color: #238636;
        color: #ffffff;
        border: 1px solid #30363d;
        border-radius: 6px;
    }
    
    .stButton > button:hover {
        background-color: #2ea043;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 侧边栏配置 ====================
with st.sidebar:
    st.title("⚙️ 配置面板")
    st.markdown("---")
    
    # 股票选择
    st.subheader("📊 股票/指数选择")
    default_symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "^GSPC", "^DJI", "^IXIC"]
    selected_symbols = st.multiselect(
        "选择要查看的股票/指数",
        options=default_symbols,
        default=["AAPL", "GOOGL", "MSFT"],
        help="可以多选"
    )
    
    st.markdown("---")
    
    # 时间范围
    st.subheader("📅 时间范围")
    time_range = st.selectbox(
        "选择时间范围",
        options=["1 个月", "3 个月", "6 个月", "1 年", "2 年", "5 年", "最大"],
        index=2
    )
    
    # 时间范围映射
    time_range_map = {
        "1 个月": 30,
        "3 个月": 90,
        "6 个月": 180,
        "1 年": 365,
        "2 年": 730,
        "5 年": 1825,
        "最大": None
    }
    
    days = time_range_map[time_range]
    
    if days:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
    else:
        start_date = datetime(2000, 1, 1)
        end_date = datetime.now()
    
    st.markdown("---")
    
    # 技术指标
    st.subheader("📈 技术指标")
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
    
    # 信息
    st.markdown("### ℹ️ 关于")
    st.markdown("""
    **数据来源**: Yahoo Finance
    
    **更新频率**: 实时（市场开盘时）
    
    **技术栈**: Streamlit + Plotly
    
    **风格**: 深色科技风
    """)

# ==================== 主页面 ====================
st.title("📈 金融数据可视化看板")
st.markdown("---")

# 检查是否有选择
if not selected_symbols:
    st.warning("⚠️ 请至少在侧边栏选择一个股票或指数")
    st.stop()

# ==================== 数据获取函数 ====================
@st.cache_data
def get_stock_data(symbols, start, end):
    """获取股票数据"""
    data = yf.download(symbols, start=start, end=end, progress=False)
    return data

# 获取数据
with st.spinner("📊 正在获取数据..."):
    try:
        stock_data = get_stock_data(selected_symbols, start_date, end_date)
        data_loaded = True
    except Exception as e:
        st.error(f"❌ 数据获取失败：{str(e)}")
        data_loaded = False

if data_loaded:
    # ==================== 关键指标展示 ====================
    st.subheader("💹 实时行情概览")
    
    # 获取最新数据
    if len(stock_data) > 0:
        # 处理多层列名（yfinance 新版本）
        if isinstance(stock_data.columns, pd.MultiIndex):
            # 多层列名格式：('Close', 'AAPL')
            first_symbol = selected_symbols[0]
            current_price = stock_data.iloc[-1][('Close', first_symbol)]
            prev_price = stock_data.iloc[-2][('Close', first_symbol)] if len(stock_data) > 1 else current_price
        else:
            # 单层列名格式：'Close'
            current_price = stock_data.iloc[-1]['Close']
            prev_price = stock_data.iloc[-2]['Close'] if len(stock_data) > 1 else current_price
        
        price_change = current_price - prev_price
        price_change_pct = (price_change / prev_price) * 100
        
        # 创建指标列
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="当前价格",
                value=f"${current_price:.2f}",
                delta=f"{price_change:+.2f} ({price_change_pct:+.2f}%)"
            )
        
        with col2:
            if isinstance(stock_data.columns, pd.MultiIndex):
                high = stock_data.iloc[-1][('High', first_symbol)]
                low = stock_data.iloc[-1][('Low', first_symbol)]
            else:
                high = stock_data.iloc[-1]['High']
                low = stock_data.iloc[-1]['Low']
            st.metric(
                label="今日区间",
                value=f"${low:.2f} - ${high:.2f}",
                delta=None
            )
        
        with col3:
            if isinstance(stock_data.columns, pd.MultiIndex):
                volume = stock_data.iloc[-1][('Volume', first_symbol)]
            else:
                volume = stock_data.iloc[-1]['Volume']
            st.metric(
                label="成交量",
                value=f"{volume/1e6:.2f}M",
                delta=None
            )
        
        with col4:
            if isinstance(stock_data.columns, pd.MultiIndex):
                open_price = stock_data.iloc[-1][('Open', first_symbol)]
            else:
                open_price = stock_data.iloc[-1]['Open']
            st.metric(
                label="开盘价",
                value=f"${open_price:.2f}",
                delta=None
            )
    
    st.markdown("---")
    
    # ==================== 主图表：K 线图 ====================
    st.subheader(f"📊 K 线图 - {', '.join(selected_symbols)}")
    
    # 创建 K 线图
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=('价格走势', '成交量')
    )
    
    # 为每个选中的股票添加数据
    colors = ['#58a6ff', '#3fb950', '#d29922', '#a371f7', '#f78166', '#56d364', '#2ea043']
    
    for idx, symbol in enumerate(selected_symbols):
        color = colors[idx % len(colors)]
        
        # 获取单个股票数据 - 处理多层列名
        if isinstance(stock_data.columns, pd.MultiIndex):
            # 多层列名：需要用 (列名，股票代码) 访问
            symbol_data = pd.DataFrame()
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                symbol_data[col] = stock_data[(col, symbol)]
        else:
            symbol_data = stock_data
        
        # K 线图
        fig.add_trace(
            go.Candlestick(
                x=symbol_data.index,
                open=symbol_data['Open'],
                high=symbol_data['High'],
                low=symbol_data['Low'],
                close=symbol_data['Close'],
                name=symbol,
                increasing_line_color=color,
                decreasing_line_color='#ff7b72'
            ),
            row=1, col=1
        )
        
        # 移动平均线
        if show_ma:
            ma = symbol_data['Close'].rolling(window=ma_period).mean()
            fig.add_trace(
                go.Scatter(
                    x=symbol_data.index,
                    y=ma,
                    name=f'{symbol} MA{ma_period}',
                    line=dict(color=color, width=1, dash='dash'),
                    opacity=0.7
                ),
                row=1, col=1
            )
        
        # 成交量
        if show_volume:
            colors_volume = ['#3fb950' if symbol_data['Close'].iloc[i] >= symbol_data['Open'].iloc[i] else '#ff7b72' 
                           for i in range(len(symbol_data))]
            fig.add_trace(
                go.Bar(
                    x=symbol_data.index,
                    y=symbol_data['Volume'],
                    name=f'{symbol} 成交量',
                    marker_color=colors_volume,
                    opacity=0.5
                ),
                row=2, col=1
            )
    
    # 更新布局 - 深色科技风
    fig.update_layout(
        height=800,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0.5)',
            font=dict(color='#f0f6fc', size=10)
        ),
        plot_bgcolor='#0d1117',
        paper_bgcolor='#0d1117',
        margin=dict(l=50, r=50, t=80, b=50),
        xaxis_rangeslider_visible=False,
        hovermode='x unified'
    )
    
    # 更新坐标轴样式
    fig.update_xaxes(
        showgrid=True,
        gridcolor='#21262d',
        linecolor='#30363d',
        tickfont=dict(color='#8b949e')
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridcolor='#21262d',
        linecolor='#30363d',
        tickfont=dict(color='#8b949e')
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ==================== 多股票对比 ====================
    if len(selected_symbols) > 1:
        st.markdown("---")
        st.subheader("📊 多股票价格对比")
        
        # 创建对比图表
        fig_compare = go.Figure()
        
        for idx, symbol in enumerate(selected_symbols):
            color = colors[idx % len(colors)]
            
            # 获取单个股票数据 - 处理多层列名
            if isinstance(stock_data.columns, pd.MultiIndex):
                symbol_data = pd.DataFrame()
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    symbol_data[col] = stock_data[(col, symbol)]
            else:
                symbol_data = stock_data
            
            # 归一化价格（以第一个数据点为基准）
            normalized = symbol_data['Close'] / symbol_data['Close'].iloc[0] * 100
            
            fig_compare.add_trace(
                go.Scatter(
                    x=symbol_data.index,
                    y=normalized,
                    name=symbol,
                    line=dict(color=color, width=2)
                )
            )
        
        fig_compare.update_layout(
            height=500,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            plot_bgcolor='#0d1117',
            paper_bgcolor='#0d1117',
            xaxis_rangeslider_visible=False,
            hovermode='x unified'
        )
        
        fig_compare.update_xaxes(showgrid=True, gridcolor='#21262d', linecolor='#30363d')
        fig_compare.update_yaxes(showgrid=True, gridcolor='#21262d', linecolor='#30363d', title="归一化价格 (%)")
        
        st.plotly_chart(fig_compare, use_container_width=True)
    
    # ==================== 数据统计表 ====================
    st.markdown("---")
    st.subheader("📋 详细数据")
    
    # 显示原始数据
    if isinstance(stock_data.columns, pd.MultiIndex):
        st.dataframe(stock_data.tail(20), use_container_width=True)
    else:
        st.dataframe(stock_data.tail(20), use_container_width=True)
    
    # 下载按钮
    csv = stock_data.to_csv()
    st.download_button(
        label="📥 下载 CSV 数据",
        data=csv,
        file_name=f"stock_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# ==================== 页脚 ====================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #8b949e; padding: 20px;'>
        <p>📈 金融数据可视化看板 | 数据来源：Yahoo Finance | 更新时间：{}</p>
        <p style='font-size: 12px;'>深色科技风设计 | Streamlit + Plotly</p>
    </div>
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
    unsafe_allow_html=True
)
