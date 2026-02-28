from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QVBoxLayout
from PyQt5.QtCore import pyqtSlot, QFile

import threading

from manager.logging_manager import get_logger

from gui.qt_widgets.market.market_wait_widget import MarketWaitWidget
from gui.qt_widgets.market.market_widget import MarketWidget
from processor.baostock_processor import BaoStockProcessor

class MarketHomeWidget(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent) 

        uic.loadUi('./src/gui/qt_widgets/market/MarketHomeWidget.ui', self)

        self.init_para()
        self.init_ui()
        self.init_connect()

    def init_para(self):
        self.logger = get_logger(__name__)

        self.b_bao_stock_data_load_finished = False
        self.lock = threading.Lock()  

    def init_ui(self):
        self.market_wait_widget = MarketWaitWidget(self)
        self.market_widget = MarketWidget(self)

        self.stackedWidget.addWidget(self.market_wait_widget)
        self.stackedWidget.addWidget(self.market_widget)
        self.stackedWidget.setCurrentWidget(self.market_wait_widget)

        self.load_qss()

    def init_connect(self):
        BaoStockProcessor().sig_stock_data_load_finished.connect(self.slot_bao_stock_data_load_finished)
        BaoStockProcessor().sig_stock_data_load_progress.connect(self.slot_bao_stock_data_load_progress)
        BaoStockProcessor().sig_stock_data_load_error.connect(self.slot_bao_stock_data_load_error)

    def load_qss(self, theme="default"):
        qss_file_name = f":/theme/{theme}/market/market.qss"
        qssFile = QFile(qss_file_name)
        if qssFile.open(QFile.ReadOnly):
            self.setStyleSheet(str(qssFile.readAll(), encoding='utf-8'))
        else:
            self.logger.warning("无法打开行情模块样式表文件")
        qssFile.close()

        # 测试：
        # qss = '''
        #     #MarketHomeWidget #MarketWidget #StockCardWidget {border-bottom: 1px solid #000000;}
        #     #MarketHomeWidget #MarketWidget #StockCardWidget #label_stock_name {font-size: 20px;}
        #     #MarketHomeWidget #MarketWidget #StockCardWidget #label_stock_code {font-size: 18px; }
        #     #MarketHomeWidget #MarketWidget #StockCardWidget #label_price[change_status="up"] {font-size: 20px; font-weight: bold; color: rgb(255, 0, 0);}
        #     #MarketHomeWidget #MarketWidget #StockCardWidget #label_price[change_status="down"] {font-size: 20px; font-weight: bold; color: rgb(21, 130, 42);}
        #     #MarketHomeWidget #MarketWidget #StockCardWidget #label_price[change_status="flat"] {font-size: 20px; font-weight: bold; color: rgb(0, 0, 0);}
        #     #MarketHomeWidget #MarketWidget #StockCardWidget #label_change_percent[change_status="up"] {font-size: 18px; color: rgb(255, 0, 0);}
        #     #MarketHomeWidget #MarketWidget #StockCardWidget #label_change_percent[change_status="down"] {font-size: 18px; color: rgb(21, 130, 42);}
        #     #MarketHomeWidget #MarketWidget #StockCardWidget #label_change_percent[change_status="flat"] {font-size: 18px; color: rgb(0, 0, 0);}
        # '''
        # self.setStyleSheet(qss)

    def slot_bao_stock_data_load_finished(self, succsess):
        self.logger.info(f"Baostock股票数据加载完成，结果为：{succsess}")

        if succsess:
            self.market_widget.slot_bao_stock_data_load_finished(succsess)
            self.stackedWidget.setCurrentWidget(self.market_widget)
            
        with self.lock:
            self.b_bao_stock_data_load_finished = succsess



    def slot_bao_stock_data_load_progress(self, progress):
        self.logger.info(f"Baostock股票数据加载进度：{progress}")
        
    def slot_bao_stock_data_load_error(self, error):
        self.logger.error(f"Baostock股票数据加载出错：{error}")


    def showEvent(self, event):
        """
        重写showEvent方法，在窗口显示时执行初始化操作
        """
        super().showEvent(event)

        b_data_loaded = False
        with self.lock:
            b_data_loaded = self.b_bao_stock_data_load_finished
        if self.stackedWidget.currentWidget() != self.market_widget and b_data_loaded:
            self.market_widget.slot_bao_stock_data_load_finished(b_data_loaded)
            self.stackedWidget.setCurrentWidget(self.market_widget)