# coding: utf-8
from PyQt5.QtCore import QUrl, QSize, QTimer
from PyQt5.QtGui import QIcon, QDesktopServices, QColor
from PyQt5.QtWidgets import QApplication, QMessageBox

from gui.qt_widgets.MComponents.qfluentwidgets import(NavigationAvatarWidget, NavigationItemPosition, MessageBox, FluentWindow,
                            SplashScreen, SystemThemeListener, isDarkTheme)

from gui.qt_widgets.MComponents.qfluentwidgets import FluentIcon as FIF


# from .gallery_interface import GalleryInterface
from .home_interface import HomeInterface
# from .basic_input_interface import BasicInputInterface
# from .date_time_interface import DateTimeInterface
# from .dialog_interface import DialogInterface
# from .layout_interface import LayoutInterface
# from .icon_interface import IconInterface
# from .material_interface import MaterialInterface
# from .menu_interface import MenuInterface
# from .navigation_view_interface import NavigationViewInterface
# from .scroll_interface import ScrollInterface
# from .status_info_interface import StatusInfoInterface
from ..setting.setting_interface import SettingInterface
# from .text_interface import TextInterface
# from .view_interface import ViewInterface

from ..review.review_interface import ReviewInterface

from ..common.config import ZH_SUPPORT_URL, EN_SUPPORT_URL, cfg
from ..common.icon import Icon
from ..common.signal_bus import signalBus
from ..common.translator import Translator
from ..common import resource

from thread.task_pool import get_default_task_pool
from processor.baostock_processor import BaoStockProcessor
from thread.baostock_data_fetch_task import *
from manager.logging_manager import get_logger


class MainWindow(FluentWindow):

    def __init__(self):
        super().__init__()

        self.init_para()
        self.init_ui()
        self.init_connect()

        self.init_processors()
        self.init_bao_stock_info()

    def init_para(self):
        self.logger = get_logger(__name__)

        # create system theme listener
        self.themeListener = SystemThemeListener(self)

        # start theme listener
        self.themeListener.start()

    def init_ui(self):
        self.initWindow()

        # create sub interface
        self.homeInterface = HomeInterface(self)
        self.settingInterface = SettingInterface(self)
        self.reviewInterface = ReviewInterface(self)

        # enable acrylic effect
        self.navigationInterface.setAcrylicEnabled(True)

        # add items to navigation interface
        self.initNavigation()
        self.splashScreen.finish()

    def init_connect(self):
        self.connectSignalToSlot()

        self.homeInterface.view.main_button_clicked.connect(self.reviewInterface.view.slot_home_main_button_clicked)
        self.homeInterface.view.manual_select_clicked.connect(lambda: self.switchTo(self.reviewInterface))
        self.homeInterface.view.result_selected.connect(
            lambda item: (
                self.logger.info(f"选中 {item.text}"),
                self.switchTo(self.reviewInterface)
            )
        )

        self.reviewInterface.view.random_data_generated.connect(lambda dict: self.homeInterface.set_fixed_result(dict))

    def connectSignalToSlot(self):
        signalBus.micaEnableChanged.connect(self.setMicaEffectEnabled)
        signalBus.switchToSampleCard.connect(self.switchToSample)
        signalBus.supportSignal.connect(self.onSupport)
        

    def initNavigation(self):

         # add navigation items
        self.addSubInterface(self.homeInterface, FIF.HOME, self.tr('Home'))
        self.addSubInterface(self.reviewInterface, Icon.REVIEW, self.tr('Review'))

        # t = Translator()
        # self.navigationInterface.addSeparator()
        # pos = NavigationItemPosition.SCROLL
        # self.addSubInterface(self.basicInputInterface, FIF.CHECKBOX,t.basicInput, pos)

        # add custom widget to bottom
        self.addSubInterface(
            self.settingInterface, FIF.SETTING, self.tr('Settings'), NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(1366, 768)
        self.setMinimumWidth(760)
        self.setWindowIcon(QIcon(':/app.svg'))
        self.setWindowTitle('KLineReview')

        self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        # create splash screen
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(106, 106))
        self.splashScreen.raise_()

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        self.show()
        QApplication.processEvents()

    def init_processors(self):
        """初始化所有处理器（如Baostock）"""
        self.logger.info("初始化所有处理器")
        try:
            ak_success = True
            success = BaoStockProcessor().initialize()
            if ak_success and success:
                self.logger.info("所有处理器初始化成功")

            else:
                self.logger.info("处理器初始化失败")
                quit()
        except Exception as e:
            self.logger.info(f"初始化过程中发生错误: {e}")
            quit()

    def init_bao_stock_info(self):
        baostock_info_fetch_task = BaostockInfoFetchTask()

        baostock_info_fetch_task.task_started.connect(self.homeInterface.slot_bao_stock_info_query_started)
        baostock_info_fetch_task.task_completed.connect(self.homeInterface.slot_bao_stock_info_query_finished)
        baostock_info_fetch_task.task_error.connect(self.homeInterface.slot_bao_stock_info_query_error)

        baostock_info_fetch_task.task_started.connect(self.reviewInterface.slot_bao_stock_info_query_started)
        baostock_info_fetch_task.task_completed.connect(self.reviewInterface.slot_bao_stock_info_query_finished)
        baostock_info_fetch_task.task_error.connect(self.reviewInterface.slot_bao_stock_info_query_error)
        get_default_task_pool().submit(baostock_info_fetch_task)

    def onSupport(self):
        language = cfg.get(cfg.language).value
        if language.name() == "zh_CN":
            QDesktopServices.openUrl(QUrl(ZH_SUPPORT_URL))
        else:
            QDesktopServices.openUrl(QUrl(EN_SUPPORT_URL))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, 'splashScreen'):
            self.splashScreen.resize(self.size())

    def closeEvent(self, e):
        title = self.tr('Prompt')
        content = self.tr(
            "Are you sure you want to exit?")
        w = MessageBox(title, content, self.window())
        w.setContentCopyable(True)

        i_ret = w.exec()
        if i_ret:
            # 可以在这里添加清理操作
            task_pool = get_default_task_pool()
            task_pool.shutdown(wait=True, cancel_running=True)
            self.logger.info("应用程序正在退出...")
            self.logger.info("开始执行清理操作...")
            self.themeListener.terminate()
            self.themeListener.deleteLater()
            super().closeEvent(e)
        else:
            self.logger.info("取消退出")
            e.ignore()
        

    def _onThemeChangedFinished(self):
        super()._onThemeChangedFinished()

        # retry
        if self.isMicaEffectEnabled():
            QTimer.singleShot(100, lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()))

    def switchToSample(self, routeKey, index):
        """ switch to sample """
        pass
        # interfaces = self.findChildren(GalleryInterface)
        # for w in interfaces:
        #     if w.objectName() == routeKey:
        #         self.stackedWidget.setCurrentWidget(w, False)
        #         w.scrollToCard(index)
