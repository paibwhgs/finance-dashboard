# 📈 金融数据可视化看板 v2.0 - 部署指南

## 📦 项目文件

```
金融数据库看板/
├── app.py                          # 原版（已备份）
├── app_v2_timeseries.py            # v2.0 时间序列分析增强版（新版）
├── requirements.txt                # Python 依赖包
└── README_部署指南.md              # 本文件
```

---

## 🚀 本地运行

### 1️⃣ 安装依赖

```bash
cd "C:\Users\Longhao Zhu\.openclaw\workspace\我创建的文件\金融数据库看板"
pip install -r requirements.txt
```

### 2️⃣ 运行应用

```bash
# 运行新版（时间序列分析增强版）
streamlit run app_v2_timeseries.py

# 或运行原版
streamlit run app.py
```

### 3️⃣ 访问网页

浏览器打开：`http://localhost:8501`

---

## 🌐 部署到 Streamlit Cloud（免费）

### 步骤 1: 准备 GitHub 仓库

1. 在 GitHub 创建新仓库（如 `finance-dashboard`）
2. 将以下文件上传到仓库：
   - `app_v2_timeseries.py`（重命名为 `app.py`）
   - `requirements.txt`

### 步骤 2: 连接 Streamlit Cloud

1. 访问 https://share.streamlit.io
2. 点击 **"New app"**
3. 选择你的 GitHub 仓库
4. 主文件路径：`app.py`
5. 点击 **"Deploy!"**

### 步骤 3: 获取分享链接

部署成功后，你会获得类似这样的链接：
```
https://your-username-finance-dashboard-app-xxxxxx.streamlit.app/
```

---

## ⚙️ v2.0 新功能说明

### 时间序列分析模块

在侧边栏勾选 **"启用时间序列分析"** 后，会显示 4 个分析标签页：

| 标签页 | 功能 | 说明 |
|--------|------|------|
| 📊 趋势分解 | 将序列分解为趋势 + 季节 + 残差 | 识别长期趋势和周期性 |
| 📈 ACF/PACF | 自相关/偏自相关图 | 检测动量效应、均值回归 |
| 📉 平稳性检验 | ADF 检验 | 判断序列是否平稳 |
| 🔮 预测 | ARIMA/指数平滑预测 | 未来 N 天价格预测 + 置信区间 |

### 使用建议

1. **趋势分解**：适合识别当前趋势是否健康
2. **ACF/PACF**：适合量化爱好者，判断是否存在可预测模式
3. **平稳性检验**：学术性较强，了解序列特性
4. **预测**：最实用功能，但请注意风险提示 ⚠️

---

## 📝 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2026-03-30 | 初始版本：K 线图、技术指标、多股对比 |
| v2.0 | 2026-04-20 | 新增时间序列分析模块（趋势分解、ACF/PACF、ADF 检验、ARIMA 预测） |

---

## ⚠️ 注意事项

1. **数据源**：Yahoo Finance，免费 API，可能有延迟
2. **预测风险**：预测结果仅供参考，不构成投资建议
3. **数据要求**：
   - 趋势分解：至少 30 个交易日
   - ARIMA 预测：至少 50 个交易日
4. **备份**：原版已备份至 `08-临时文件/备份/` 文件夹

---

## 🆘 常见问题

### Q: 安装 statsmodels 失败？
```bash
# 尝试升级 pip
python -m pip install --upgrade pip

# 或使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: 运行时报错 "No module named 'statsmodels'"？
```bash
# 手动安装
pip install statsmodels
```

### Q: 预测结果不准确？
- 时间序列预测基于历史数据，无法预测突发事件
- 尝试选择更长的时间范围（至少 50 个交易日）
- 预测仅供参考，不建议作为唯一决策依据

---

## 📞 技术支持

如有问题，请联系开发者或查看 Streamlit 文档：
- Streamlit 文档：https://docs.streamlit.io
- statsmodels 文档：https://www.statsmodels.org

---

*最后更新：2026-04-20*
