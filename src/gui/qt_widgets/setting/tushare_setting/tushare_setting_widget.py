from PyQt5 import QtCore, uic, QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QDate
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget, QMessageBox, QCompleter

from manager.logging_manager import get_logger
from manager.environment_config_manager import EnvironmentConfigManager
from manager.period_manager import TimePeriod, _DEFAULT_LOAD_PERIODS, _BASE_LOAD_PERIODS
from manager.tushare_stock_data_manager import TuShareStockDataManager

from processor.tushare_processor import TUSHARE_PRO_API_KEY, TushareProcessor

class TuShareSettingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi('./src/gui/qt_widgets/setting/tushare_setting/TuShareSettingWidget.ui', self)

        self.init_para()
        self.init_ui()
        self.init_connect()

    def init_para(self):
        self.logger = get_logger(__name__)
        self.list_allowed_period = [TimePeriod.DAY, TimePeriod.WEEK, TimePeriod.MONTH]

    def init_ui(self):
        key_value = EnvironmentConfigManager.get(TUSHARE_PRO_API_KEY)

        if key_value == '' or key_value is None: 
            self.logger.info("Tushare login failed. API key is empty.")
        else:
            self.lineEdit_api_key.setText(key_value)

        list_interfaces = ['update_trade_calendar', 'update_stock_basic_info', 'query_stock_unadjusted_data', 'query_stock_adjusted_data']
        self.btn_interface_select.addItems(list_interfaces)
        self.btn_interface_select.setCurrentIndex(0)

        stands = TuShareStockDataManager().get_code_name_complete_list()
        completer = QCompleter(stands, self.lineEdit_code)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setMaxVisibleItems(10)
        self.lineEdit_code.setCompleter(completer)

        self.btn_select_start_date.setDate(QDate.currentDate().addDays(-365))
        self.btn_select_end_date.setDate(QDate.currentDate())

        list_adjustment = ['bfq', 'qfq', 'hfq']
        self.btn_adjustment.addItems(list_adjustment)
        self.btn_adjustment.setCurrentIndex(0)

        list_period = ['D', 'W', 'M']
        self.btn_period.addItems(list_period)
        self.btn_period.setCurrentIndex(0)

    def init_connect(self):
        self.btn_save_api_key.clicked.connect(self.slot_btn_save_api_key_clicked)
        self.btn_test.clicked.connect(self.slot_btn_test_clicked)

    def slot_btn_save_api_key_clicked(self):
        b_ret = TushareProcessor().initialize()
        if b_ret:
            EnvironmentConfigManager.set(TUSHARE_PRO_API_KEY, self.lineEdit_api_key.text(), True)
            self.logger.info("Tushare login successful.")
        else:
            self.logger.info("Tushare login failed.")
            self.lineEdit_api_key.setText('')

    def slot_btn_test_clicked(self):
        
        str_interface = self.btn_interface_select.currentText()

        str_stands = self.lineEdit_code.text()
        list_code_name = TuShareStockDataManager().parse_code_name_by_complete_text(str_stands)
        if not list_code_name:
            return
        
        code = list_code_name[0]
        name = list_code_name[-1]

        str_start_date = self.btn_select_start_date.getDate().toString("yyyyMMdd")
        str_end_date = self.btn_select_end_date.getDate().toString("yyyyMMdd")
        str_adjustment = self.btn_adjustment.currentText()
        str_period = self.btn_period.currentText()

        self.logger.info(f"Tushare test: interface={str_interface}, code: {code}, name: {name}, start_date={str_start_date}, end_date={str_end_date}, adjustment={str_adjustment}, period={str_period}")

        i_interface_index = self.btn_interface_select.currentIndex()
        i_adjustment_index = self.btn_adjustment.currentIndex()
        i_period_index = self.btn_period.currentIndex()
        self.logger.info(f"Tushare test: interface_index={i_interface_index}, adjustment_index={i_adjustment_index}, period_index={i_period_index}")

        if i_interface_index == 0:
            b_ret = TushareProcessor().update_trade_calendar(str_start_date, str_end_date)
        elif i_interface_index == 1:
            b_ret = TushareProcessor().update_stock_basic_info()
        elif i_interface_index == 2:
            b_ret = TushareProcessor().query_stock_unadjusted_data(code, str_start_date, str_end_date, self.list_allowed_period[i_period_index])
        elif i_interface_index == 3:
            b_ret = TushareProcessor().query_stock_adjusted_data(code, str_start_date, str_end_date, str_adjustment, str_period)