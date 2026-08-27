import sys
import os
from PyQt5.QtCore import QFile, QCoreApplication, Qt, QTranslator
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from resources import resources_rc

from gui.qt_widgets.main.main_widget import MainWidget
from manager.logging_manager import get_logger, setup_logging

from gui.qt_widgets.common.config import cfg
from gui.qt_widgets.main.main_window import MainWindow

from gui.qt_widgets.MComponents.qfluentwidgets import FluentTranslator

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
# 确保能导入自定义组件
components_path = os.path.join(project_root, 'gui', 'qt_widgets', 'MComponents', 'review')
if components_path not in sys.path:
    sys.path.insert(0, components_path)

def setup_high_dpi_support():
    """
    设置高 DPI 支持，兼容不同 Qt 版本和平台
    """

    # 方法1：启用高 DPI 缩放（Qt 5.6+）
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # 方法2： 设置固定缩放比例
    os.environ['QT_SCALE_FACTOR'] = '1'

    # 方法3：设置环境变量 QT_AUTO_SCREEN_SCALE_FACTOR
    if 'QT_AUTO_SCREEN_SCALE_FACTOR' not in os.environ:
        os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'  # 可根据需要调整缩放比例


    # 方法4：启用高 DPI 缩放（Qt 5.14+）
    if hasattr(QCoreApplication, "setHighDpiScaleFactorRoundingPolicy"):
        from PyQt5.QtCore import Qt as QtCoreQt
        QCoreApplication.setHighDpiScaleFactorRoundingPolicy(
            QtCoreQt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    # 禁用缩放（适用于 Qt 5.9+）
    if hasattr(QApplication, "setAttribute") and hasattr(Qt, "AA_Use96Dpi"):
        QApplication.setAttribute(Qt.AA_Use96Dpi)

    # Qt6 强制指定字体 DPI（如果需要兼容 Qt6）
    os.environ["QT_FONT_DPI"] = "96"

def app_run():
    logger = get_logger(__name__)
    logger.info("应用程序启动")
    # PyQt5
    setup_high_dpi_support()
    app = QApplication(sys.argv)  # 创建应用程序对象
    app.setWindowIcon(QIcon(":/app.svg"))

    logger.info(f"Screen scale factor: {app.devicePixelRatio()}")

    qssFile = QFile(":/theme/default/main.qss")
    if qssFile.open(QFile.ReadOnly):
        # 使用 data() 方法获取字节数据并解码
        app.setStyleSheet(str(qssFile.readAll(), encoding='utf-8'))
        # app.setStyleSheet("*{font-family: 'Microsoft YaHei';font-size: 18px;}")
    else:
        logger.warning("无法打开整体样式表文件")
    qssFile.close()

    # qt widgets实现
    # widget = QWidget()           # 创建窗口实例
    widget = MainWidget()
    widget.setWindowTitle("KLineReview")
    widget.show()                  # 显示窗口

    ret = -1
    try:
        ret = app.exec_()
        logger.info("应用程序正常退出")
        
    except Exception as e:
        logger.error(f"应用程序异常退出: {e}")

    sys.exit(ret)


def app_run_2():
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
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

    # internationalization
    locale = cfg.get(cfg.language).value
    translator = FluentTranslator(locale)
    galleryTranslator = QTranslator()
    galleryTranslator.load(locale, "gallery", ".", ":/gallery/i18n")

    app.installTranslator(translator)
    app.installTranslator(galleryTranslator)

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
    # 设置进程标识环境变量
    os.environ['MPOLICY_PROCESS'] = 'main'
    
    # 初始化日志系统
    # 初始化日志系统
    setup_logging( 
        log_dir="./data/logs",
        level="INFO",
        enable_file_log=True,
        max_bytes=10 * 1024 * 1024,
        backup_count=5,
        unique_log_file=True  # 启用唯一日志文件名
    )
    
    # app_run()
    app_run_2()



if __name__ == "__main__":
    main()
