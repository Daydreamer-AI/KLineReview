"""开发态与 PyInstaller 打包态共用的路径解析。

约定：
- 冻结态（frozen）：只读资源放在 PyInstaller 的 _MEIPASS 下；
- 开发态：只读资源直接使用仓库内 src/ 目录；
- 配置、日志等可写数据一律放到用户应用数据目录（冻结态）或仓库 app|data（开发态）。
"""

import os
import sys
from pathlib import Path

APP_NAME = "KLineReview"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False) or getattr(sys, "_MEIPASS", None))


def get_repo_root() -> Path:
    """仓库根目录；冻结态下为 PyInstaller 解包根（_MEIPASS）。"""
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def get_runtime_src_root() -> Path:
    """源码/只读资源根目录：开发态与冻结态均为 <根>/src。"""
    return get_repo_root() / "src"


def get_user_app_dir() -> Path:
    """冻结态下可写的用户应用数据目录。"""
    home = Path.home()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", home)) / APP_NAME
    elif sys.platform == "darwin":
        base = home / "Library" / "Application Support" / APP_NAME
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / APP_NAME
    return base


def get_config_dir() -> Path:
    """UI 配置目录：冻结态为用户数据目录，开发态保持仓库 app/config。"""
    if is_frozen():
        return get_user_app_dir()
    return get_repo_root() / "app" / "config"


def get_config_file() -> Path:
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"


def get_log_dir() -> Path:
    """日志目录：冻结态为用户数据目录/logs，开发态保持仓库 data/logs。"""
    if is_frozen():
        log_dir = get_user_app_dir() / "logs"
    else:
        log_dir = get_repo_root() / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_database_root(source: str = "baostock") -> Path:
    """SQLite 数据库根目录：冻结态为用户数据目录，开发态保持仓库 data/database。"""
    if is_frozen():
        db_root = get_user_app_dir() / "database"
    else:
        db_root = get_repo_root() / "data" / "database"
    db_root = db_root / "stocks" / "db" / source
    db_root.mkdir(parents=True, exist_ok=True)
    return db_root


def get_bundle_relative(relative_path) -> Path:
    """解析相对 _MEIPASS/仓库根目录的资源路径。"""
    return get_repo_root() / relative_path


def get_module_relative_file(module_file, file_name: str) -> Path:
    """按模块文件所在目录解析同目录资源（主要是 .ui）。

    开发态模块位于 <root>/src/gui/...，直接使用其目录；
    冻结态模块 __file__ 位于 _MEIPASS/gui/...，而资源打包在
    _MEIPASS/src/gui/...，因此自动补上 src/ 前缀。
    """
    module_dir = Path(module_file).resolve().parent
    try:
        rel = module_dir.relative_to(get_repo_root())
        if rel.parts and rel.parts[0] != "src":
            module_dir = get_repo_root() / "src" / rel
    except ValueError:
        pass
    return module_dir / file_name
