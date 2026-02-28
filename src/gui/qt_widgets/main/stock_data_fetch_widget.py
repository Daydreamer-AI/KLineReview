from PyQt5 import uic
from PyQt5.QtWidgets import QWidget

from thread.baostock_data_fetch_task import BaostockDataFetchTask

class StockDataFetchWidget(QWidget):
    def __init__(self, parent=None):
        super(StockDataFetchWidget, self).__init__(parent)
        self.ui = uic.loadUi("./src/gui/qt_widgets/main/StockDataFetchWidget.ui", self)
        self.init_para()
        self.init_ui()
        self.init_connect()

    def init_para(self):
        self.dict_task = {}     # 0: 沪市主板日线周线，1：深市主板日线周线，2：沪深主板15、30、60分钟k线数据
        baostock_sh_main_data_fetch_task = BaostockDataFetchTask()
        baostock_sz_main_data_fetch_task = BaostockDataFetchTask()
        baostock_sh_and_sz_main_minute_data_fetch_task = BaostockDataFetchTask()
        self.dict_task[0] = baostock_sh_main_data_fetch_task
        self.dict_task[1] = baostock_sz_main_data_fetch_task
        self.dict_task[2] = baostock_sh_and_sz_main_minute_data_fetch_task

    def init_ui(self):
        self.widget_sh_main_fetch.set_task(self.dict_task[0])
        self.widget_sz_main_fetch.set_task(self.dict_task[1])
        self.widget_sh_and_sz_main_minute_fetch.set_task(self.dict_task[2])

        self.widget_sh_main_fetch.setEnabled(False)
        self.widget_sz_main_fetch.setEnabled(False)

    def init_connect(self):
        self.btn_min.clicked.connect(self.slot_btn_min_clicked)
        self.btn_close.clicked.connect(self.slot_btn_close_clicked)


    def slot_btn_min_clicked(self):
        self.hide()

    def slot_btn_close_clicked(self):
        self.hide()
