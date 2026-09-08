# ReviewWidget 数据加载流程重构

## 基本信息

- 需求编号：TODO（编号规则未定）
- 提出日期：2026-08-20
- 提出人：TODO
- 优先级：P1（重要）
- 状态：已完成
- 关联分支：feature/review-data-loading（从 feature/indicators-data-injection 切出）

## 1. 背景与目标

- 背景：ReviewWidget 目前的数据加载存在多个触发入口（“加载”按钮、“随机加载”按钮、图表内部周期切换按钮），职责混乱；本地无数据时 `BaostockDataFetchTask` 下载完成后只隐藏 Loading、不回填数据，后台加载链路实际是断的；顶部 `comboBox_period` 仅记录日志，未实际参与加载。
- 目标：复盘数据加载统一由“加载 / 随机加载”按钮触发，一次性在后台加载**所有配置周期**（默认 15/30/60 分钟、日线、周线，预留调整接口）的数据，全部加载完成后再统一同步到 `indicators_view_widget`；`comboBox_period` 选择的是“加载完成后初始显示哪个周期”；后台加载期间禁用图表内部周期切换按钮，同步完成后再启用；图表内部周期切换按钮不再触发上层数据加载。

## 2. 需求描述（功能点）

- [x] 统一入口：`load_data(code, date)` 仅由两个按钮触发；移除 `sig_period_changed → 上层取数` 的链路。
- [x] 全周期远程加载：一次加载动作覆盖所有配置周期（默认日线、周线；分钟级数据获取暂屏蔽，拉取链会跳过分钟级配置），全部从远程 Baostock 获取、不再读取本地 K 线库；因 baostock 为全局单会话、并发查询不安全，各周期按顺序串行提交 `BaostockDataFetchTask`，任务随结果返回已补名称与指标列的 DataFrame。
- [x] 预留周期列表调整接口：`get_load_periods()` / `set_load_periods(periods)`，调整后同步刷新 `comboBox_period` 选项。
- [x] 周期选择：`comboBox_period` 仅决定加载完成后 `IndicatorsViewWidget` 的初始显示周期；所选周期无数据时回退到第一个可用周期并同步下拉框。
- [ ] 周期切换逻辑：当前实现较复杂、暂不符合预期（如分钟级精确日期匹配失败时图表不更新、切换后图表数据与周期可能不一致），兜底实现已撤销，待方案确认后另行处理。
- [x] 异步回填：全部周期加载完成后统一 `set_stock_data(code, {所有周期: df})` → `set_period_buttons_enabled(已加载周期)` → `set_current_period(显示周期)` → `init_animation`，自动出图。
- [x] 加载期间禁用 `IndicatorsViewWidget` 全部周期切换按钮（`set_period_buttons_enabled([])`）；同步完成后仅启用已加载周期的按钮。
- [x] 修复 `BaostockDataFetchTask` 日线/周线分支恒为 `False` 的 bug（`TimePeriod == TimePeriod.DAY` 为类与枚举成员比较）。
- [x] 图表内部周期按钮：仅在已注入周期数据之间切换；点击未注入周期时回退到原周期并提示，不触发任何上层取数。
- [x] 加载完成后同步图表内部周期按钮（新增 `IndicatorsViewWidget.set_current_period`）。
- [x] 同股票全部配置周期均已加载时重复点击：仅按新日期重新定位动画，不重复下载。
- [x] 不再读取本地 K 线库：动画锚点行取自远程显示周期数据的最后一行，名称取自本地股票信息库；远程返回空数据时按无数据处理并提示。
- [x] 修复远程数据 `date`（`datetime.date`）/ `time`（Timestamp）与字符串比较的类型错误：任务层统一转为 ISO 字符串（`init_animation` 的防御性 `str()` 转换随周期切换改动一并撤销）。
- [x] 远程拉取起始日期按复盘日期计算：日/周线往前 400 天（覆盖 MA60/MA52 等指标预热），分钟线以复盘日期为起点并受近两年下限约束；所选日期超出数据范围时自动回退到边界日期，避免“未找到匹配日期、界面空白”。
- [x] 远程复盘拉取保持前复权（`adjustflag=2`）：baostock 前复权仅提供最近约三年数据，故随机复盘日期限定在近三年窗口内（最早日期再向后预留约 250 天指标预热）；`process_*` 与 `BaostockDataFetchTask` 新增 `adjustflag` 参数，数据脚本等既有调用不受影响。
- [x] 修复 `set_current_period` 误匹配“分时”按钮的问题（`TimePeriod.from_label('分时')` 默认返回日线，导致日线按钮未被选中），加载完成后周期按钮正确处于选中状态。
- [x] 随机加载与代码校验不依赖本地 K 线数据：`BaostockDataManager.get_all_stock_code_name_dict()` 提供“个股代码-名称”映射，随机选股后日期由 `common_api.get_random_date()` 生成，K 线数据统一在加载时远程获取。

## 3. 验收标准

- [ ] 点击“加载 / 随机加载”后，后台按顺序从远程 Baostock 获取全部配置周期（不再读取本地 K 线库），全部完成后统一出图。
- [ ] `comboBox_period` 选择的周期即加载完成后图表初始显示周期；图表内部周期按钮在已加载周期之间的切换行为待确认（分钟级精确日期匹配失败等暂未兜底处理）。
- [ ] 后台加载期间图表内部周期切换按钮全部禁用；加载完成后仅已加载周期按钮可点击。
- [ ] 日线/周线无需本地数据，全部周期直接远程获取（原恒 `False` bug 已修复）。
- [ ] 同股票重复点击加载仅按新日期重新定位动画，不触发重复下载。
- [ ] 冒烟验证：从项目根目录运行 `python ./src/main.py`，`data/logs` 无新增 ERROR/异常。

## 4. 影响范围

- 涉及模块/文件：
  - `src/gui/qt_widgets/MComponents/review_widget.py`（本次重构主体）
  - `src/gui/qt_widgets/MComponents/indicators/indicators_view_widget.py`（新增 `set_current_period`、`set_period_buttons_enabled`；复盘模式周期切换守卫；`init_animation` 初始周期状态修正）
  - `src/manager/bao_stock_data_manager.py`（新增 `get_all_stock_code_name_dict`）
  - `src/thread/baostock_data_fetch_task.py`（改为远程拉取并随结果返回已补名称/指标的 DataFrame，不再写库；修复日线/周线分支）
  - `docs/项目导读.md`（5.3 复盘数据流章节同步）
- 涉及数据/数据库：无 schema 变更。
- 兼容性与风险：行情页周期切换仍走 `sig_period_changed → 外部取数`，不受影响；`IndicatorsViewWidget` 为共享组件，改动集中在复盘模式分支与非触发式新增接口；baostock 全局单会话，多周期任务必须串行，不可并行提交。

## 5. 开发记录

- 开发分支：feature/review-data-loading
- 关键提交：18e0d0f（复盘数据远程加载并暂屏蔽分钟级获取）；前序 5a85b00（全周期后台加载重构）、b23afe1/f1e1a5f（外部注入适配）
- 自测结果：py_compile 通过；离屏（QT_QPA_PLATFORM=offscreen）实例化 ReviewWidget 通过；默认周期列表与下拉选项（日线、周线，分钟级暂屏蔽）正确；`set_period_buttons_enabled` 禁用/按列表启用通过；`set_load_periods` 调整接口刷新下拉通过（分钟级配置会被拉取链跳过）；以真实线程池 + 模拟远程数据源验证链式远程拉取 → 任务返回远程 DataFrame（含名称与指标）→ 统一 `set_stock_data` → 按所选周期显示 → 动画初始化通过；模拟真实远程数据类型（`datetime.date` 对象 / Timestamp）加载通过，`date` 列统一为字符串；前复权（`adjustflag=2`）三年窗口内 2025-06-24 复盘正常出图（预热 671 根），窗口最早边界 2024-04-30 仍有 251 根预热；随机日期限定在近三年窗口内；日期早于数据起点自动回退不再空白；同股票重复点击走缓存重定位、不重复远程拉取；周期切换行为待用户确认后另行处理（2026-08-23）。
- 冒烟验证：用户已从项目根目录运行 `python ./src/main.py` 复验通过（2026-08-23，复盘页远程加载正常，`data/logs` 无阻塞性 ERROR）。

## 6. 完成状态与备注

- 完成日期：2026-08-23（已合并至 release/1.0）
- 遗留问题/TODO：
  - 默认加载周期已调整为日线、周线（分钟级数据获取暂屏蔽；复盘数据不落库，与本地 `stock_data_*` 表无关）。
  - 分钟级数据获取暂屏蔽：默认仅日线/周线，拉取链会跳过分钟级配置；待分钟级数据范围与周期切换逻辑确认后恢复。
  - 周期切换逻辑待确认：分钟级精确日期匹配失败时图表不更新、切换后图表数据与周期可能不一致（`time` 列缺失导致日期文本报错）等问题，待用户确认方案后另行处理；本轮兜底实现已撤销。
  - `ReviewWidget.get_random_date` 类方法已不再被引用（随机日期改用 `common_api.get_random_date`），可考虑后续删除。
- 备注：本需求为 `20260820-IndicatorsViewWidget数据外部注入重构.md` 的复盘页数据流后续规划。
