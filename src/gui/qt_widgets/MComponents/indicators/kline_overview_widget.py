from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QVBoxLayout
from PyQt5.QtCore import pyqtSlot, Qt

from manager.indicators_config_manager import *

class KLineOverviewWidget(QWidget):
    def __init__(self, parent=None):
        super(KLineOverviewWidget, self).__init__(parent)
        self.ui = uic.loadUi(self.get_ui_path(), self)
        self.init_para()
        self.init_ui()
        self.init_connect()
        self.load_qss()

    def get_ui_path(self):
        return "./src/gui/qt_widgets/MComponents/indicators/KLineOverviewWidget.ui"
    
    def init_para(self):
        pass

    def init_ui(self):
        self.label_hours.hide()

    def init_connect(self):
        pass

    def load_qss(self):
        self.setStyleSheet("QFrame{border: 2px solid #2982ff; background-color: #a0ffffff;} QLabel{border: None; background-color: transparent; font-size: 16px}")
        self.label_amplitude.setStyleSheet("color: #00a9b2; font-size: 18px")
        self.label_volume.setStyleSheet("color: #00a9b2; font-size: 18px")
        self.label_amount.setStyleSheet("color: #00a9b2; font-size: 18px")
        self.label_turnover_rate.setStyleSheet("color: #00a9b2; font-size: 18px")
        self.label_volume_ratio.setStyleSheet("color: #00a9b2; font-size: 18px")
        self.label_kline_status.setStyleSheet("color: #00a9b2; font-size: 18px")

    def update_labels(self, df_last_row, df_current_row, y_val, level='1d'):
        if df_last_row is None:
            self.setStyleSheet("")
            last_close = 0
        else:
            last_close = df_last_row['close']

        if df_current_row is not None:
            date = df_current_row['date']
            open = df_current_row['open']
            close = df_current_row['close']
            high = df_current_row['high']
            low = df_current_row['low']
            change_percent = df_current_row['change_percent']
            amplitude = (high - low) / low * 100
            volume = df_current_row['volume'] / 10000      # 单位：万
            amount = df_current_row['amount'] / 100000000  # 单位：亿
            turnover_rate = df_current_row['turnover_rate']
            volume_ratio = df_current_row['volume_ratio']

            if 'm' in level:
                time = df_current_row['time']
                self.label_hours.setText(str(time))

            self.label_date.setText(str(date))

            self.label_value.setText(f"{y_val:.2f}")
            self.label_open.setText(f"{open:.2f}")
            self.label_close.setText(f"{close:.2f}")
            self.label_high.setText(f"{high:.2f}")
            self.label_low.setText(f"{low:.2f}")
            self.label_change_percent.setText(f"{change_percent:.2f}%")
            self.label_amplitude.setText(f"+{amplitude:.2f}%")
            self.label_volume.setText(f"{volume:.2f}万")
            self.label_amount.setText(f"{amount:.2f}亿")
            self.label_turnover_rate.setText(f"{turnover_rate:.2f}%")
            self.label_volume_ratio.setText(f"{volume_ratio:.2f}")
            self.label_kline_status.setText("--")

            # TODO: 根据股票所属板块进行涨跌停、炸板、翘板判断。
            # if close >= high:
            #     self.label_kline_status.setText("涨停")
            # elif close <= low:
            #     self.label_kline_status.setText("跌停")
            # elif 
            #     self.label_kline_status.setText
        
            if y_val > last_close:
                self.label_value.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_ASC.value]}; font-size: 18px")
            elif y_val < last_close:
                self.label_value.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_DESC.value]}; font-size: 18px")
            else:
                self.label_value.setStyleSheet("font-size: 18px")

            if open > last_close:
                self.label_open.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_ASC.value]}; font-size: 18px")
            elif open < last_close:
                self.label_open.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_DESC.value]}; font-size: 18px")
            else:
                self.label_open.setStyleSheet("font-size: 18px")

            if close > last_close:
                self.label_close.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_ASC.value]}; font-size: 18px")
            elif close < last_close:
                self.label_close.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_DESC.value]}; font-size: 18px")
            else:
                self.label_close.setStyleSheet("font-size: 18px")

            if high > last_close:
                self.label_high.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_ASC.value]}; font-size: 18px")
            elif high < last_close:
                self.label_high.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_DESC.value]}; font-size: 18px")
            else:
                self.label_high.setStyleSheet("font-size: 18px")

            if low > last_close:
                self.label_low.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_ASC.value]}; font-size: 18px")
            elif low < last_close:
                self.label_low.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_DESC.value]}; font-size: 18px")
            else:
                self.label_low.setStyleSheet("font-size: 18px")

            if change_percent > 0:
                self.label_change_percent.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_ASC.value]}; font-size: 18px")
            elif change_percent < 0:
                self.label_change_percent.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_DESC.value]}; font-size: 18px")
            else:
                self.label_change_percent.setStyleSheet("font-size: 18px")

