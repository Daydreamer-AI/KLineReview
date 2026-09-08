# IndicatorsViewWidget 数据外部注入重构

## 基本信息

- 需求编号：TODO（编号规则未定）
- 提出日期：2026-08-20
- 提出人：TODO
- 优先级：P1（重要）
- 状态：已完成
- 关联分支：feature/indicators-data-injection

## 1. 背景与目标

- 背景：`IndicatorsViewWidget` 目前内部直接依赖 `BaostockDataManager` 与后台取数任务（`BaostockDataFetchTask`），既负责数据获取又负责缓存维护与绘制，职责混杂；本地无数据时还会自行触发网络拉取并显示 Loading，外部难以复用/替换数据来源。
- 目标：将该类改造为纯展示/维护组件——数据由外部注入，内部只做多周期缓存维护、图表更新与复盘动画维护，不再发起任何数据获取。

## 2. 需求描述（功能点）

- [x] 移除 `IndicatorsViewWidget` 内部对 `BaostockDataManager`、`BaostockDataFetchTask`、默认线程池的直接使用。
- [x] 新增外部数据注入接口（如 `set_stock_data(code, dict_period_data)`），外部按 `{TimePeriod: DataFrame}` 结构传入各周期 K 线数据。
- [x] 内部多周期缓存（`dict_stock_data`）、选中股票（`current_selected_code`）、复盘周期状态（`dict_period_process_data`）等维护逻辑保留。
- [x] `update_chart()` / `init_animation()` 等原有对外方法签名保持稳定，但不再内部取数；未注入数据时给出明确日志并安全返回。
- [x] 行情页 `market_widget.py` 适配：点击股票/周期切换时由外部取数并注入（2026-08-20）。
- [x] 复盘页 `review_widget.py` 适配：加载数据/周期切换时由外部取数并注入，废弃桩 `update_stock_data_dict` 已删除（2026-08-20）。
- [x] 同步更新 `docs/项目导读.md` 5.1 行情与 5.3 复盘数据流章节。

## 3. 验收标准

- [x] `indicators_view_widget.py` 中检索不到 `BaostockDataManager` / `BaostockDataFetchTask` / `get_default_task_pool` 的引用。
- [x] 注入数据后，行情展示、指标绘制、周期切换行为与改造前一致（行情页、复盘页真实冒烟均通过）。
- [x] 未注入数据时调用 `update_chart` / `init_animation` 不崩溃，日志中有明确提示。
- [x] 模块可正常 import，语法自检通过。

## 4. 影响范围

- 涉及模块/文件：
  - `src/gui/qt_widgets/MComponents/indicators/indicators_view_widget.py`（本次重构）
  - 后续外部适配待用户确认：`src/gui/qt_widgets/market/market_widget.py`、`src/gui/qt_widgets/MComponents/review_widget.py`
  - 间接引用：`src/thread/baostock_data_fetch_task.py`、`src/thread/task_pool.py`（取数调用方将随外部适配变化）
  - 文档：`docs/项目导读.md`（数据流章节，待外部适配后同步）
- 涉及数据/数据库：无 schema 变更。
- 兼容性与风险：行情页、复盘页均已适配并通过离屏冒烟；复盘页待用户真实冒烟复验。`market_widget.py` 与 `review_widget.py` 各有一份相同的取数辅助方法 `_load_stock_data_with_indicators`，后续可考虑提取公共封装。

## 5. 开发记录

- 开发分支：feature/indicators-data-injection
- 关键提交：b23afe1（行情页适配）；复盘页适配提交（本次）
- 自测结果：py_compile 通过；模块 import 通过；离屏功能冒烟（注入数据→update_chart / init_animation / 周期切换 / 失败信号 / 行情页点击与周期切换注入 / 复盘页加载与周期切换注入）通过（2026-08-20）
- 冒烟验证：用户已从项目根目录运行 `python ./src/main.py`：行情页点击多只股票并切换日线/周线/15/30/60 分周期，复盘页验证加载数据、切周期、播放/暂停、买卖挂单，表现均与改造前一致；检查 `data/logs/app_20260820_*.log` 无 ERROR/异常，仅有周期切换首轮“未注入”的预期 WARNING（2026-08-20）

## 6. 完成状态与备注

- 完成日期：2026-08-20
- 遗留问题/TODO：
  - 外部调用已采用“周期切换信号按需回填”方案；如需改为一次性全量注入可再评估。
  - `market_widget.py` 与 `review_widget.py` 的 `_load_stock_data_with_indicators` 重复，待后续提取公共封装。
  - 复盘页 `comboBox_period` 目前仅记录日志、未实际驱动周期切换（改造前即如此），是否接入待确认。
- 备注：
