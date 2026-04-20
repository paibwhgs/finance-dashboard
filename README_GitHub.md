# 📈 金融数据可视化看板 v4.0

> 量化回测版 - 策略回测 · 绩效评估 · 交易信号

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-username-finance-dashboard.streamlit.app)

## 🌟 功能特性

### 📊 数据查看模式
- 实时行情数据（Yahoo Finance）
- K 线图 + 技术指标（MA、成交量）
- 财务数据概览（PE、PB、市值等）
- 数据质量检查报告

### 🔬 量化回测模式
**支持 3 种经典策略**：
- **均线交叉策略** - 金叉买入，死叉卖出
- **RSI 超买超卖策略** - RSI<30 买入，RSI>70 卖出
- **布林带策略** - 跌破下轨买入，突破上轨卖出

**完整绩效评估**：
- 总收益率、年化收益率
- 夏普比率、最大回撤
- 年化波动率
- 胜率、盈亏比
- 交易次数

**可视化**：
- 资金曲线图（策略 vs 买入持有）
- 交易信号标记（K 线图上显示买卖点）
- 详细交易记录

## 🚀 快速开始

### 在线使用（推荐）

访问部署链接：[https://your-username-finance-dashboard.streamlit.app](https://your-username-finance-dashboard.streamlit.app)

### 本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/finance-dashboard.git
cd finance-dashboard

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行应用
streamlit run app_deploy.py
```

浏览器打开：http://localhost:8501

## 📋 依赖安装

```bash
pip install streamlit==1.32.0
pip install yfinance>=1.0.0
pip install pandas==2.2.1
pip install numpy==1.26.4
pip install plotly==5.19.0
pip install statsmodels==0.14.1
pip install scikit-learn==1.4.0
```

或使用 requirements.txt：
```bash
pip install -r requirements.txt
```

## 💡 使用指南

### 1. 选择股票
- 预设：AAPL、GOOGL、MSFT、AMZN、TSLA 等
- 自定义：输入股票代码（如 `600519.SS` 贵州茅台）

### 2. 设置时间范围
- 1 个月、3 个月、6 个月、1 年、2 年、5 年、全部

### 3. 选择模式
- **数据查看**：查看行情和财务数据
- **量化回测**：运行策略回测

### 4. 回测配置（量化回测模式）
- 选择策略（均线交叉/RSI/布林带）
- 调整策略参数
- 设置初始资金
- 点击"开始回测"

### 5. 查看结果
- 绩效指标卡片
- 资金曲线图
- 交易信号图
- 详细交易记录

## 📊 绩效指标说明

| 指标 | 说明 | 参考标准 |
|------|------|----------|
| **总收益率** | 回测期间总收益 | >0% 盈利 |
| **年化收益率** | 折算成年化收益 | >10% 优秀 |
| **夏普比率** | 风险调整后收益 | >1 合格，>2 优秀 |
| **最大回撤** | 最大亏损幅度 | <20% 较安全 |
| **胜率** | 盈利交易占比 | >45% 可接受 |
| **盈亏比** | 平均盈利/平均亏损 | >1.5 较好 |

## ⚠️ 免责声明

- **数据来源**：Yahoo Finance（可能有 15 分钟延迟）
- **仅供参考**：不构成投资建议
- **回测局限**：历史表现不代表未来结果
- **风险提示**：投资有风险，入市需谨慎

## 🛠️ 技术栈

- **前端框架**：Streamlit
- **数据获取**：yfinance
- **数据处理**：pandas、numpy
- **可视化**：Plotly
- **时间序列**：statsmodels

## 📝 版本历史

| 版本 | 日期 | 功能 |
|------|------|------|
| v1.0 | 2026-03-30 | 基础 K 线图、技术指标 |
| v2.0 | 2026-04-20 | 时间序列分析 |
| v3.0 | 2026-04-20 | 数据层深化（复权、财务数据） |
| v4.0 | 2026-04-20 | 量化回测（3 种策略、绩效评估） |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📞 联系

- GitHub Issues: [提交问题](https://github.com/your-username/finance-dashboard/issues)
- Email: your-email@example.com

---

**Made with ❤️ using Streamlit**
