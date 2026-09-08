# AGENTS.md

> 本文件面向在 KLineReview 仓库中协作的开发者/代理，内容仅来自对仓库的只读分析（2026-08-19）。
> 所有路径均为相对项目根目录；未确认的事项统一标注 `TODO`，不做猜测。

## 项目概览

- 定位：A 股股票数据处理与技术分析桌面工具，自带 K 线回放复盘与模拟交易功能（确认自 [README.md](README.md) 首句与 [src/gui/qt_widgets/MComponents/review_widget.py](src/gui/qt_widgets/MComponents/review_widget.py)）。
- 技术栈：PyQt5（界面）、PyQtGraph（K 线/指标绘图）、Pandas/NumPy（数据处理）、SQLite（本地存储）、baostock 与 akshare（数据源）（确认自 [requirements.txt](requirements.txt) 与 `src/` 代码结构）。
- 许可证：MIT（确认自 [LICENSE](LICENSE) 与 README）。
- 编码：源码/文案为 UTF-8 编码（按 UTF-8 读取正常，README 中文亦为 UTF-8）。
- Python 版本：README 要求 3.10+；当前仓库 `.venv` 实际为 Python 3.12.10（确认自 [.venv/pyvenv.cfg](.venv/pyvenv.cfg)）。

## 重要约定（新手必读）

1. **必须从项目根目录启动程序**。代码大量使用相对路径（如 `./src/gui/qt_widgets/main/MainWidget.ui`、`./data/logs`），从 `src` 目录或其它目录运行会失败（确认自 [src/main.py](src/main.py) 及各 widget 中的 `uic.loadUi('./src/...')`）。
2. **首次运行前必须有本地数据**：可运行 `scripts/run_baostock_data_update.bat` 下载，或按 README 使用网盘备份把 `stocks` 目录放入 `data/database/`（确认自 [README.md](README.md)）。
3. **数据更新脚本与主程序互斥**：主程序运行期间不要执行 `scripts/*.bat`/`*.sh` 数据更新脚本（确认自 [scripts/check_process.py](scripts/check_process.py) 与 [scripts/auto_update_baostrock_data.py](scripts/auto_update_baostrock_data.py) 的互斥检查逻辑）。

## 日常开发与维护流程（Agent 必须遵守）

1. **新需求/功能必须先生成需求文档**：接到新增需求/功能任务时，若 `docs/需求文档/<版本>/<模块>/` 下没有对应文档，先按 [docs/需求文档/需求文档模板.md](docs/需求文档/需求文档模板.md) 创建 `docs/需求文档/<版本>/<模块>/<YYYYMMDD>-<功能名>.md`（模块归类见 [docs/需求文档/模块划分说明.md](docs/需求文档/模块划分说明.md)），开发完成后更新其状态。
2. **开发前必读**：[docs/项目导读.md](docs/项目导读.md)、[docs/开发规范/版本控制.md](docs/开发规范/版本控制.md)、[docs/开发规范/日常开发维护流程.md](docs/开发规范/日常开发维护流程.md) 与本文件。
3. **分支与提交规范**：按 [docs/开发规范/版本控制.md](docs/开发规范/版本控制.md) 创建分支（`release/`、`feature/`、`fix/`、`hotfix/`）；提交信息使用 Conventional Commits（`feat`/`fix`/`docs`/`refactor`/`test`/`chore`）。
4. **自测**：先运行 `python -m unittest discover -s tests -v`（如有相关测试），再从项目根目录运行 `python ./src/main.py` 冒烟验证，并检查 `data/logs/` 是否有新报错。
5. **文档同步**：若改动影响目录结构、程序入口、运行命令或规范，同步更新 [docs/项目导读.md](docs/项目导读.md) 与本文件；需求文档标记“已完成”并记录分支/提交。
6. **不确定事项**：一律标注 TODO，不猜测。

## 目录说明

| 目录/文件 | 职责（均已从代码确认） |
| --- | --- |
| `src/main.py` | 程序入口：日志初始化 → QApplication → MainWidget → 三个页面（默认行情页） |
| `src/gui/qt_widgets/` | 界面：`main/`（首页、主窗口）、`market/`（行情页）、`MComponents/`（K 线、指标、复盘、模拟交易卡片等可复用组件） |
| `src/gui/qml/` | 疑似遗留：`MainBridge` 在 `main.py` 被 import 但从未实例化使用（TODO：确认是否删除） |
| `src/manager/` | 业务管理：`bao_stock_data_manager.py`（数据缓存与查询）、`review_demo_trading_manager.py`（模拟交易引擎）、`period_manager.py`（周期枚举）、`indicators_config_manager.py`、`config_manager.py`、`logging_manager.py` |
| `src/processor/` | 数据源适配：`baostock_processor.py`（日/周/分钟线）、`ak_stock_data_processor.py`（股票列表/板块/市值/筹码等）、`period_aggregator.py`（通用周期聚合：复盘上级周期由基周期本地生成）；`efinance_processor.py` 为几行示例、未被其他模块引用（TODO：确认是否删除） |
| `src/db_base/` | SQLite 封装：`common_db_base.py`（通用连接池+CRUD）、`stock_db_base.py`（每只股票一个 K 线库）、`stock_info_db_base.py`（股票列表/板块/市值信息库） |
| `src/indicators/` | 技术指标计算：`stock_data_indicators.py`（MACD/KDJ/RSI/BOLL/MA/量比等） |
| `src/thread/` | 后台任务：`task_pool.py`（Qt 线程池）、`base_task.py`（可暂停/取消任务）、`base_thread_worker.py`、`baostock_data_fetch_task.py` |
| `src/controller/` | 当前**未接入主流程**：`home_widget.py` 中对其 import 处于注释状态（确认） |
| `src/common/` | 通用工具：`common_api.py`（股票代码识别、板块归类、涨跌停价、文件保存等） |
| `src/utils/` | 进程检查：`process_checker.py`（供数据脚本与主程序互斥使用） |
| `src/resources/` | 图标、QSS 主题、`resources.qrc` 与生成文件 `resources_rc.py`、`auto_recompile_resources.py` 编译脚本、`config/config.ini` |
| `src/config/` | `logging_config.yaml`：**未被任何代码引用**（main.py 通过参数调用 `setup_logging`）（TODO：确认用途或删除） |
| `scripts/` | 数据更新与进程检查脚本：`run_baostock_data_update.bat`、`run_akshare.update.bat`、`run_akshare_update.sh`、`auto_update_baostrock_data.py`、`auto_update_akshare_board_data.py`、`check_process.py`；`smoke_review_baostock.py`（复盘真实数据冒烟，可选/联网） |
| `data/` | 运行时数据：`database/stocks/db/baostock|akshare` 为 SQLite 行情库，`logs` 为日志 |
| `docs/` | 文档体系：项目导读、开发规范（版本控制/日常流程）、需求文档（按版本/模块划分，含模板与划分说明）、设计文档（复盘周期切换与聚合、维护与扩展指南）、效果图素材 |
| `tests/` | 自动化测试（unittest，纯合成数据、无网络依赖）：周期聚合器单测、复盘周期切换集成测试（离屏 Qt） |
| `.github/workflows/` | CI：GitHub Actions 在 push/PR 到 `master`/`release/*` 时运行 unittest |
| `.venv/` | 本地虚拟环境（已 gitignore） |
| 根目录 | `README.md`、`LICENSE`、`requirements.txt`（未锁版本）、`create_venv.bat/.sh`、空 `__init__.py` |

## 运行命令

以下均确认自 [README.md](README.md) 与仓库脚本：

```bash
# 1. 创建并激活虚拟环境（README 要求 Python 3.10+）
py -3.10 -m venv .venv
.venv\Scripts\activate            # Windows
# 或 conda create --name myenv python=3.10 && conda activate myenv

# 2. 安装依赖
pip install -r requirements.txt

# 3. 首次准备数据（二选一）
scripts\run_baostock_data_update.bat   # 联网下载（较慢）
# 或按 README 从网盘下载备份，解压 stocks 到 data/database/ 下

# 4. 启动程序（必须在项目根目录）
python ./src/main.py

# 5. 修改 resources.qrc 或图标/QSS 后，重新编译资源（不要手改生成文件）
python src/resources/auto_recompile_resources.py
```

## 测试命令

- 自动化测试（`unittest`，纯合成数据、无网络依赖，**从项目根目录运行**）：

  ```bash
  python -m unittest discover -s tests -v
  ```

  - `tests/test_period_aggregator.py`：周期聚合器单测（交易时段切槽、跨午休 120m、部分槽、
    多日/多周/多月倍数、自定义分钟）；
  - `tests/test_review_period_switch.py`：复盘周期切换集成测试（离屏 Qt，覆盖加载锚定、
    全矩阵位置保持、盘中边界、进行中/自动走完、时间跨周期传播、未覆盖回退）。
- CI：`.github/workflows/unittest.yml`（GitHub Actions，push/PR 到 `master`/`release/*` 自动运行 unittest）。
- 真实数据冒烟（可选，需联网）：`python scripts/smoke_review_baostock.py [--code sz.000615] [--date YYYY-MM-DD]`
- 冒烟验证：从项目根目录运行 `python ./src/main.py`，并检查 `data/logs/` 是否有新报错。
- TODO：后续为以下核心逻辑补充单测：
  - `src/indicators/stock_data_indicators.py`（指标计算）
  - `src/manager/review_demo_trading_manager.py`（模拟交易撮合/资金计算）
  - `src/db_base/`（SQLite 读写）

## 禁止事项

1. **禁止手改 `src/resources/resources_rc.py`**：它是 Qt 资源编译生成文件（约 912KB，且已被 git 跟踪）。需改 `resources.qrc` 后运行 `python src/resources/auto_recompile_resources.py` 重新生成（确认自 [src/resources/auto_recompile_resources.py](src/resources/auto_recompile_resources.py) 与 `resources.qrc` 旁的说明文件）。
2. **禁止在主程序运行期间执行 `scripts/` 下的数据更新脚本**（确认自 [scripts/check_process.py](scripts/check_process.py) 的互斥检查）。
3. **禁止从非项目根目录启动 `src/main.py`**（相对路径依赖，确认自代码）。
4. **禁止随意改动 `src/db_base/` 中的建表/加列逻辑**：仓库内已存在大量 SQLite 数据文件（含被 git 跟踪的 `.db` 文件），schema 变更可能破坏现有数据；如需变更应先确认迁移方案（TODO：目前无迁移机制文档）。
5. **禁止只改 `.py` 不同步 `.ui`**：界面控件由 `uic.loadUi` 在运行时按 `.ui` 文件加载，`main_widget.py`、`home_widget.py` 等均有此用法（确认）。
6. **禁止把运行时产生的数据/日志变更当作普通代码提交**：`.gitignore` 已包含 `data`、`logs`、`*.log`，但对**已被 git 跟踪的 `data/database` 下 `.db` 文件无效**，其变更仍会出现在 `git status` 中（确认自 `git ls-files` 与 [.gitignore](.gitignore)）。
7. **禁止随意增删依赖**：`requirements.txt` 未锁版本（确认），增删依赖需在提交说明中注明；`PyQtChart` 已在 requirements 中声明但全仓未检索到使用（TODO：确认是否移除）。

## 提交前检查

1. `git status` 检查意外变更，重点核对：
   - `src/resources/resources_rc.py` 仅在 `resources.qrc` 变更并重新编译后发生变化；
   - `data/database/` 下已跟踪的 `.db` 文件是否出现改动（确认是否是有意更新数据）。
2. 若改动了 `resources.qrc` / 图标 / QSS：先运行 `python src/resources/auto_recompile_resources.py`，确认 `resources_rc.py` 已重新生成。
3. 若改动了界面控件：确认对应 `.ui` 文件已同步（运行时按 `.ui` 加载，确认）。
4. 冒烟验证：先运行 `python -m unittest discover -s tests -v`（如改动涉及复盘周期/聚合），再从项目根目录手动运行 `python ./src/main.py`，确认程序能启动、无 `data/logs` 中新报错。
5. TODO：仓库无 lint/format/CI 配置（未检索到），待引入后再补充对应检查项。

## 待确认事项（TODO 汇总）

- `src/gui/qml/`（`MainBridge`、QML 页面）与 `src/processor/efinance_processor.py` 是否删除：前者仅被 import 未使用，后者未被其他模块引用（`stock_info_db_base.py` 中另有 efinance 数据库初始化逻辑，需一并确认）。
- `src/controller/` 是否保留：当前未接入主流程，`home_widget.py` 中 import 被注释。
- `src/config/logging_config.yaml` 是否保留：全仓无引用，`main.py` 使用参数配置。
- `src/resources/config/config.ini` 的用途：代码中未检索到读取该文件，`ConfigManager` 默认读写 `%APPDATA%\MPolicy\config.ini`（确认自 [src/manager/config_manager.py](src/manager/config_manager.py)）。
- `requirements.txt` 中的 `PyQtChart` 是否需要：全仓未检索到使用。
- `data/database` 下的 `.db` 数据是否应继续纳入版本控制（当前已被 git 跟踪，但 `.gitignore` 又声明忽略 `data`，存在矛盾）。
- README 引用的 `CONTRIBUTING.md` 在仓库中不存在（确认文件列表），需补充或修正。
- 无打包配置（无 `setup.py`/`pyproject.toml`/`.spec`），是否需要补充构建/打包方案。
