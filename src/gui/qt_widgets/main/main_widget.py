from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.QtCore import pyqtSlot, QFile

from manager.logging_manager import get_logger

from gui.qt_widgets.main.home_widget import HomeWidget
from gui.qt_widgets.market.market_home_widget import MarketHomeWidget
from gui.qt_widgets.MComponents.review_widget import ReviewWidget
from thread.task_pool import get_default_task_pool

class MainWidget(QWidget):
    def __init__(self):
        super().__init__()

        # 加载 UI 文件，第二个参数 self 表示将控件加载到当前窗口
        # 注意：PyQt5 在加载 .ui文件时，如果发现槽函数名称符合 on_对象名_信号名的格式，​​会自动连接​​信号和槽
        uic.loadUi('./src/gui/qt_widgets/main/MainWidget.ui', self)  # 确保路径正确

        self.init_para()
        self.init_ui()
        self.init_connect()

    def init_para(self):
        self.logger = get_logger(__name__)

    def init_ui(self):
        self.main_button_group = QtWidgets.QButtonGroup(self)
        self.main_button_group.addButton(self.btn_home, 0)
        self.main_button_group.addButton(self.btn_market, 1)
        self.main_button_group.addButton(self.btn_review, 2)


        self.home_page = HomeWidget()
        self.market_page = MarketHomeWidget()
        self.review_page = ReviewWidget()

        self.stackedWidget.addWidget(self.home_page)
        self.stackedWidget.addWidget(self.market_page)

        self.stackedWidget.addWidget(self.review_page)

        self.stackedWidget.setCurrentWidget(self.market_page)

        self.load_qss()

    def init_connect(self):
        self.btn_home.clicked.connect(self.slot_btn_home_clicked)
        self.btn_market.clicked.connect(self.slot_btn_market_clicked)
        self.btn_review.clicked.connect(self.slot_btn_review_clicked)


    def load_qss(self, theme="default"):
        qss_file_name = f":/theme/{theme}/main/home.qss"
        self.logger.info(f"样式表文件路径：{qss_file_name}")
        qssFile = QFile(qss_file_name)
        if qssFile.open(QFile.ReadOnly):
            self.setStyleSheet(str(qssFile.readAll(), encoding='utf-8'))
        else:
            self.logger.warning("无法打开主页模块样式表文件")
        qssFile.close()


    # ---------------重写----------------
    def closeEvent(self, event):
        """
        处理窗口关闭事件
        """
        # 创建消息框
        reply = QMessageBox.question(
            self,
            '退出确认',
            '确定要退出MPolicy吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        # 根据用户选择决定是否关闭
        if reply == QMessageBox.Yes:
            # 可以在这里添加清理操作
            task_pool = get_default_task_pool()
            task_pool.shutdown(wait=True, cancel_running=True)
            print("应用程序正在退出...")
            event.accept()  # 接受关闭事件
        else:
            event.ignore()  # 忽略关闭事件，取消关闭操作


    # --------------槽函数---------------

    @pyqtSlot()
    def slot_btn_home_clicked(self):
        self.stackedWidget.setCurrentWidget(self.home_page)

    @pyqtSlot()
    def slot_btn_market_clicked(self):
        self.stackedWidget.setCurrentWidget(self.market_page)

    def slot_btn_review_clicked(self):
        self.stackedWidget.setCurrentWidget(self.review_page)
