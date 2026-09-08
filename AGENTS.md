# AGENTS.md

> 面向在 KLineReview 仓库协作的开发者和 Agent。本文基于 V1.0 收尾状态更新（2026-09-08，`release/1.0`，已合入 `master` dc07eed）。路径均相对项目根目录；未确认事项标 `TODO`，不猜测。

## 项目概览

- 定位：A 股 **K 线回放复盘 + 模拟交易**桌面工具（PyQt5），支持自定义指标参数、亮/暗主题与中/繁/英多语言。
- 版本：`VERSION = "1.0.0"`（见 [src/common/config.py](src/common/config.py)）。
- 许可证：项目采用 **GPL-3.0**（[LICENSE](LICENSE)）；内置 qfluentwidgets 亦为 GPL-3.0，商用需按上游要求另行授权（见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)）。
- 技术栈：PyQt5、PyQtGraph、Pandas/NumPy；行情与股票列表通过 **Baostock** 联网获取；qfluentwidgets 已**内置**在 [src/gui/qt_widgets/MComponents/qfluentwidgets](src/gui/qt_widgets/MComponents/qfluentwidgets)；`src/db_base/` 保留 SQLite 读写层。
- Python：README 要求 3.10+，本地 `.venv` 为 3.12（已确认 [.venv/pyvenv.cfg](.venv/pyvenv.cfg)）。

## 关键约定

1. **必须从项目根目录启动**：`python ./src/main.py`。`.ui` 文件按 `./src/...` 相对路径加载，UI 配置读写 `app/config/config.json`、日志写入 `./data/logs`，从其它目录启动会失败。
2. **主程序联网运行**：启动时登录 Baostock 并后台获取股票代码/名称；复盘页按需远程拉取基周期（当前日线），周线/月线由日线本地聚合。分钟级周期在代码中默认注释、可扩展（见 [docs/设计文档](docs/设计文档)）。
3. **文档同步**：新增需求先建 `docs/需求文档/<版本>/<模块>/` 文档；改动影响目录结构、入口、运行命令或规范时，同步更新 [docs/项目导读.md](docs/项目导读.md)、[docs/开发规范](docs/开发规范) 与本文件。
4. **分支与提交**：按 [docs/开发规范/版本控制.md](docs/开发规范/版本控制.md) 使用 `release/`、`feature/`、`fix/`、`hotfix/`；提交使用 Conventional Commits。

## 目录职责（已按当前代码确认）

| 目录/文件 | 职责 |
| --- | --- |
| `src/main.py` | 入口：设置进程标识、日志、DPI、国际化，创建 `MainWindow` |
| `src/common/` | 应用配置 `cfg`（主题/语言/DPI）、翻译、图标、样式、公共工具 |
| `src/gui/qt_widgets/main/` | `MainWindow`（FluentWindow 导航）+ `HomeInterface`（首页弹幕选股） |
| `src/gui/qt_widgets/review/` | 复盘页面包装与 `ReviewDialog`（嵌入 IndicatorsViewWidget 的复盘弹窗） |
| `src/gui/qt_widgets/setting/` | 设置页（个性化/毛玻璃/关于/反馈等） |
| `src/gui/qt_widgets/MComponents/` | 可复用组件：指标图（K 线/MA/MACD/KDJ/RSI/BOLL/成交量等）、复盘/弹幕/模拟交易卡片、内置 qfluentwidgets |
| `src/manager/` | 业务管理：Baostock 数据缓存与查询、复盘周期、模拟交易、指标配置（用户目录）、日志 |
| `src/processor/` | Baostock 数据源适配（日/周/分钟线、股票列表）；`period_aggregator.py` 通用周期聚合 |
| `src/db_base/` | SQLite 封装（通用连接池、个股 K 线库、股票信息库） |
| `src/indicators/` | 技术指标计算 |
| `src/thread/` | Qt 任务池、可暂停/取消任务基类、Baostock 取数与股票信息任务 |
| `src/resources/` | `resources.qrc`/`resources_rc.py`（生成文件）、主题 QSS、i18n `.ts/.qm` 与更新脚本 |
| `scripts/` | 仅保留 `smoke_review_baostock.py`（联网真实数据冒烟，可选） |
| `packaging/` | 发布打包：PyInstaller spec、图标生成脚本 |
| `tests/` | `test_period_aggregator.py`、`test_review_period_switch.py`（合成数据/离屏 Qt） |
| `data/` | 运行时数据与日志（`.gitignore` 忽略；`data/database/stocks/db/baostock/stocks.db` 仍被 git 跟踪） |
| `docs/` | 项目导读、开发规范、需求文档（v1.0）、设计文档、效果图 |
| `.github/workflows/` | `unittest.yml`（测试 CI）、`release.yml`（打 v* tag 时构建 exe/dmg 并发布 GitHub Release） |

## 运行与测试

```bash
# 安装依赖
pip install -r requirements.txt

# 从项目根目录启动
python ./src/main.py

# 自动化测试（合成数据、无网络）
python -m unittest discover -s tests -v

# 复盘真实数据冒烟（可选、需联网）
python scripts/smoke_review_baostock.py --code sz.000615 --date YYYY-MM-DD

# 修改 resources.qrc / 图标 / QSS 后重新编译（勿手改生成文件）
python src/resources/auto_recompile_resources.py

# 生成应用图标（PyInstaller 前）
python packaging/make_icons.py

# 本地打包（需先 pip install pyinstaller）
pyinstaller --noconfirm --clean packaging/KLineReview.spec
```

## 禁止事项

1. 禁止手改 `src/resources/resources_rc.py`；改 `resources.qrc` 后运行编译脚本。
2. 禁止只改 `.py` 不同步 `.ui`：界面按 `.ui` 运行时加载（`uic.loadUi`）。
3. 禁止从非项目根目录运行 `python ./src/main.py`（含 `src` 目录）。
4. 禁止随意改动 `src/db_base/` 的建表/加列逻辑；如需 schema 变更先确认迁移方案（`TODO`：暂无迁移机制文档）。
5. 禁止把运行时产物当普通代码提交：`app/`、`data/logs/`、`.venv/` 已被忽略，但 `data/database/.../stocks.db` 仍被 git 跟踪，其改动会出现在 `git status`。
6. 禁止随意增删依赖：`requirements.txt` 未锁版本，增删需在提交说明注明。

## 待确认事项（TODO）

- `requirements.txt` 中 `akshare`、`PyQtChart` 未被业务代码引用（确认是否移除）。
- 内置 qfluentwidgets 源码是否持续跟随上游、是否需裁剪。
- `data/database/.../stocks.db` 仍被跟踪与 `.gitignore` 忽略 `data` 的矛盾（确认是否取消跟踪或补充说明）。
- `src/gui/qt_widgets/review/ReviewDialog.ui`/`review_dialog.py` 仅被 IndicatorsViewWidget 的复盘按钮使用，确认 V1.0 是否需要保留该入口。
