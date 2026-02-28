from PyQt5 import QtCore
from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import pyqtSlot

import pyqtgraph as pg
import numpy as np

from manager.logging_manager import get_logger
from gui.qt_widgets.MComponents.indicators.base_indicator_widget import BaseIndicatorWidget
from gui.qt_widgets.MComponents.indicators.item.macd_item import MACDItem
from gui.qt_widgets.MComponents.indicators.setting.macd_setting_dialog import MacdSettingDialog
from indicators.stock_data_indicators import *
from manager.indicators_config_manager import *

class MacdWidget(BaseIndicatorWidget):
    def __init__(self, data, type, parent=None):
        super(MacdWidget, self).__init__(data, type, parent)
        self.custom_init()
        self.load_qss()

    def custom_init(self):
        self.btn_close.hide()
        self.btn_setting.clicked.connect(self.slot_btn_setting_clicked)

    def init_para(self, data):
        self.logger = get_logger(__name__)
        self.indicator_type = IndicatrosEnum.MACD.value
        # 检查是否有数据
        if data is None or data.empty:
            # raise ValueError("数据为空，无法绘制MACD指标图")
            self.logger.warning("数据为空，无法绘制MACD指标图")
            return
        
        # 确保数据列存在
        required_columns = [IndicatrosEnum.MACD_DIFF.value, IndicatrosEnum.MACD_DEA.value, IndicatrosEnum.MACD.value]
        if not all(col in data.columns for col in required_columns):
            self.logger.warning("缺少必要的数据列来绘制MACD指标图")
            raise ValueError("缺少必要的数据列来绘制MACD指标图")
        
        self.df_data = data

    def load_qss(self):
        self.dict_macd_label = {
            0: self.label_diff,
            1: self.label_dea
        }
        dict_settings = get_indicator_config_manager().get_user_config_by_indicator_type(self.indicator_type)
        if len(dict_settings) == 3:
            self.label_param.setText(f"{dict_settings[0].period, dict_settings[1].period, dict_settings[2].period}")
            
        for id, ma_setting in dict_settings.items():
            if id in self.dict_macd_label.keys():
                self.dict_macd_label[id].setStyleSheet(f"color: {ma_setting.color_hex}")

    def get_ui_path(self):
        return './src/gui/qt_widgets/MComponents/indicators/MacdWidget.ui'

    def validate_data(self):
        required_columns = [IndicatrosEnum.MACD_DIFF.value, IndicatrosEnum.MACD_DEA.value, IndicatrosEnum.MACD.value]
        return all(col in self.df_data.columns for col in required_columns)

    def create_and_add_item(self):
        if self.item is None:
            self.item = MACDItem(self.df_data)
        else:
            self.item.update_data(self.df_data)
        
        self.plot_widget.addItem(self.item)

    def set_axis_ranges(self):
        # 设置坐标范围
        self.plot_widget.setXRange(-1, len(self.df_data) + 1, padding=0)
        
        # 计算Y轴范围
        diff_values = self.df_data[IndicatrosEnum.MACD_DIFF.value].dropna()
        dea_values = self.df_data[IndicatrosEnum.MACD_DEA.value].dropna()
        macd_values = self.df_data[IndicatrosEnum.MACD.value].dropna()
        
        if len(diff_values) > 0 and len(dea_values) > 0 and len(macd_values) > 0:
            y_max = max(np.max(np.abs(diff_values)), np.max(np.abs(dea_values)), np.max(np.abs(macd_values)))
            y_max = y_max * 1.2 if y_max > 0 else 1
            self.plot_widget.setYRange(-y_max, y_max, padding=0)

    def get_chart_name(self):
        return "MACD"
    
    def update_widget_labels(self):
        self.slot_global_update_labels(self, -1)

    def additional_draw(self):
        """添加零轴线"""
        # 添加零轴线
        zero_line = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen('g', width=1, style=QtCore.Qt.DashLine))
        self.plot_widget.addItem(zero_line)

    def slot_btn_setting_clicked(self):
        dlg = MacdSettingDialog()
        result = dlg.exec()
        if result == QDialog.Accepted:
            self.logger.info("更新MACD设置")
            auto_macd_calulate(self.df_data)
            self.update_data(self.df_data)
            self.auto_scale_to_latest(120)

    def slot_range_changed(self):
        '''当视图范围改变时调用'''
        # y轴坐标值同步
        # 获取当前x轴视图范围内的数据
        visible_data, x_min, x_max = self.get_visible_data_range()
        if visible_data is None:
            return

        # 根据当前可视范围内的数据的最大、最小值调整Y轴坐标值范围
        # MACD指标需要考虑diff、dea、macd三列数据
        required_columns = [IndicatrosEnum.MACD_DIFF.value, IndicatrosEnum.MACD_DEA.value, IndicatrosEnum.MACD.value]
        # 检查所需列是否存在
        if not all(col in visible_data.columns for col in required_columns):
            return
        
        # 计算可视范围内的绝对值最大值（MACD通常围绕0轴对称）
        y_max = visible_data[required_columns].abs().max().max()
        
        # 防止y_max为0的情况
        y_max = y_max * 1.2 if y_max > 0 else 1
        
        # 重新设置Y轴刻度（保持对称）
        self.plot_widget.setYRange(-y_max, y_max, padding=0)

    def slot_global_update_labels(self, sender, closest_index):
        if self.df_data is None or self.df_data.empty:
            return
        
        if self.type != sender.type:
            # self.logger.info(f"不响应其他窗口的鼠标移动事件")
            return
        macd = self.df_data.iloc[closest_index][IndicatrosEnum.MACD.value]          # 这里直接使用枚举值，是因为计算时就以枚举值固定命名

        if macd > 0:
            self.label_macd.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_ASC.value]};")
        else:
            self.label_macd.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_DESC.value]};")

        dict_settings = get_indicator_config_manager().get_user_config_by_indicator_type(self.indicator_type)

        if len(dict_settings) == 3:
            self.label_param.setText(f"{dict_settings[0].period, dict_settings[1].period, dict_settings[2].period}")

        self.dict_macd_label = {
            0: self.label_diff,
            1: self.label_dea
        }
        for id, setting in dict_settings.items():
            if id in self.dict_macd_label.keys() and setting.name in self.df_data.columns:
                if id == 2:
                    continue

                self.dict_macd_label[id].setText(f"{setting.name}:{self.df_data.iloc[closest_index][setting.name]:.2f}")
                self.dict_macd_label[id].setVisible(setting.visible)
                self.dict_macd_label[id].setStyleSheet(f"color: {setting.color_hex}")

    def slot_global_reset_labels(self, sender):
        self.slot_global_update_labels(sender, -1)

    def slot_v_line_mouse_moved(self, sender, x_pos):
        # self.logger.info(f"正在处理{self.get_chart_name()}鼠标移动响应, self: {self}, sender: {sender}")
        if self.type != sender.type:
            # self.logger.info(f"不响应其他窗口的鼠标移动事件")
            return
        self.v_line.setPos(x_pos)
        self.v_line.show()