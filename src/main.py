import sys
import os
from pathlib import Path
from PyQt5 import uic as qt_uic
from PyQt5.QtCore import QFile, QCoreApplication, Qt, QTranslator
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from resources import resources_rc

from manager.logging_manager import get_logger, setup_logging

from common.paths import get_log_dir, get_repo_root
from common.config import cfg
from gui.qt_widgets.main.main_window import MainWindow

from gui.qt_widgets.MComponents.qfluentwidgets import FluentTranslator
from common.translator import KLineReviewTranslator

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
# 确保能导入自定义组件
components_path = os.path.join(project_root, 'gui', 'qt_widgets', 'MComponents', 'review')
if components_path not in sys.path:
    sys.path.insert(0, components_path)

# 不要再把 qfluentwidgets 各子目录逐一裸加进 sys.path。
# 若把 date_time 等子目录裸加进 sys.path，uic 解析 .ui 中提升的 CalendarPicker 时
# 会把 calendar_picker 当顶层模块加载，导致其内部相对导入 "...common.style_sheet" 报错
# "attempted relative import with no known parent package"。
# qfluentwidgets 包已由上方 "from ...qfluentwidgets import FluentTranslator" 按完整包路径加载。
# 提升控件的裸名映射由共享模块 review/ensure_promoted_widgets.py 集中管理
# （在 review_widget.py 里调用 ensure_promoted_widgets()）。


def _resolve_ui_path(ui_file):
    """把 .ui 路径解析为开发态/冻结态下真实存在的文件路径。"""
    if not isinstance(ui_file, str):
        return ui_file

    path = Path(ui_file)
    if path.is_file():
        return ui_file

    candidates = [
        Path.cwd() / path,
        get_repo_root() / path,
    ]
    relative = str(path).replace("\\", "/")
    if relative.startswith("./"):
        candidates.append(get_repo_root() / relative[2:])

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    # 冻结态：模块 __file__ 通常为 _MEIPASS/gui/...，
    # 而随包资源按 _MEIPASS/src/gui/... 组织，据此补一次换算。
    root = get_repo_root()
    try:
        rel_to_bundle = path.relative_to(root)
        if rel_to_bundle.parts and rel_to_bundle.parts[0] != "src":
            candidate = root / "src" / rel_to_bundle
            if candidate.is_file():
                return str(candidate)
    except ValueError:
        pass

    # 冻结态下模块 __file__ 不一定指向可读目录，最后按文件名在资源树中兜底查找
    try:
        hit = next(root.rglob(path.name))
        return str(hit)
    except StopIteration:
        return ui_file


def _install_ui_path_resolver():
    """统一代理 uic.loadUi，使打包后的 .ui 资源也能被找到。"""
    original_load_ui = qt_uic.loadUi

    def load_ui(*args, **kwargs):
        if args:
            args = (_resolve_ui_path(args[0]),) + args[1:]
        return original_load_ui(*args, **kwargs)

    qt_uic.loadUi = load_ui


def app_run():
    logger = get_logger(__name__)
    logger.info("应用程序启动")

    # enable dpi scale
    if cfg.get(cfg.dpiScale) == "Auto":
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    else:
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))

    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # create application
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(":/app.svg"))
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

    # internationalization
    locale = cfg.get(cfg.language).value
    logger.info(f"使用语言: {locale.name()}")
    qfluent_widgets_translator = FluentTranslator(locale)

    appTranslator = KLineReviewTranslator(locale)
    if not appTranslator.load(locale):
        logger.warning(f"未找到语言包: {locale.name()}")

    app.installTranslator(qfluent_widgets_translator)
    app.installTranslator(appTranslator)

    # create main window
    w = MainWindow()
    w.show()

    ret = -1
    try:
        ret = app.exec_()
        logger.info("应用程序正常退出")
        
    except Exception as e:
        logger.error(f"应用程序异常退出: {e}")

    sys.exit(ret)

def main():
    _install_ui_path_resolver()

    # 设置进程标识环境变量
    os.environ['MPOLICY_PROCESS'] = 'main'
    
    # 初始化日志系统
    setup_logging( 
        log_dir=str(get_log_dir()),
        level="INFO",
        enable_file_log=True,
        max_bytes=10 * 1024 * 1024,
        backup_count=5,
        unique_log_file=True  # 启用唯一日志文件名
    )
    
    app_run()



if __name__ == "__main__":
    main()
