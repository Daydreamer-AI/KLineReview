from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import pyqtSlot

import pyqtgraph as pg
import numpy as np
import pandas as pd

from manager.logging_manager import get_logger
from gui.qt_widgets.MComponents.indicators.base_indicator_widget import BaseIndicatorWidget
from gui.qt_widgets.MComponents.indicators.item.amount_item import AmountItem
from gui.qt_widgets.MComponents.indicators.setting.amount_setting_dialog import AmountSettingDialog

from manager.indicators_config_manager import *

class AmountWidget(BaseIndicatorWidget):
    def __init__(self, data, type, parent=None):
        super(AmountWidget, self).__init__(data, type, parent)

        self.custom_init()
        self.load_qss()

    def custom_init(self):
        self.label_ma5.hide()
        self.label_ma10.hide()
        self.label_ma20.hide()

        self.btn_close.hide()

        self.btn_setting.clicked.connect(self.slot_btn_setting_clicked)

    def load_qss(self):
        self.dict_ma_label = {
            0: self.label_ma5,
            1: self.label_ma10,
            2: self.label_ma20
        }
        dict_ma_settings = get_indicator_config_manager().get_user_config_by_indicator_type(self.indicator_type)
        for id, ma_setting in dict_ma_settings.items():
            if id in self.dict_ma_label.keys():
                self.dict_ma_label[id].setStyleSheet(f"color: {ma_setting.color_hex}")

    def init_para(self, data):
        self.logger = get_logger(__name__)
        self.indicator_type = IndicatrosEnum.AMOUNT.value

        # 检查是否有数据
        if data is None or data.empty:
            # raise ValueError("数据为空，无法绘制成交额指标图")
            self.logger.warning("数据为空，无法绘制成交额指标图")
            return
        
        # 确保数据列存在
        required_columns = ['open', 'close', 'amount']
        if not all(col in data.columns for col in required_columns):
            self.logger.warning("缺少必要的数据列来绘制成交额指标图")
            raise ValueError("缺少必要的数据列来绘制成交额指标图")
        
        # 添加数据类型检查
        if not pd.api.types.is_numeric_dtype(data['amount']):
            self.logger.error(f"amount列数据类型错误: {data['amount'].dtype}")
            raise ValueError("amount列必须是数值类型")
        
        self.df_data = data
        

    def get_ui_path(self):
        return './src/gui/qt_widgets/MComponents/indicators/AmountWidget.ui'
    
    def validate_data(self):
        required_columns = ['open', 'close', 'amount']
        return all(col in self.df_data.columns for col in required_columns)

    def create_and_add_item(self):
        # 检查amount列是否有有效数据
        amount_data = self.df_data['amount']
        if amount_data.isna().all():
            self.logger.error("amount列全部为NaN")
            return
        
        if (amount_data == 0).all():
            self.logger.error("amount列全部为0")
            return

        # 创建或更新成交额图
        if self.item is None:
            self.item = AmountItem(self.df_data)
        else:
            self.item.update_data(self.df_data)

        self.plot_widget.addItem(self.item)

    def set_axis_ranges(self):
        # 设置坐标范围
        self.plot_widget.setXRange(-1, len(self.df_data) + 1, padding=0)
        max_amount = np.max(self.df_data['amount'])
        # self.logger.info(f"最大成交额-max_amount: {max_amount}")
        self.plot_widget.setYRange(0, max_amount / 100000000 * 1.1, padding=0)       # 单位：亿

    def get_chart_name(self):
        return "成交额"
    
    def update_widget_labels(self):
        self.slot_global_update_labels(self, -1)

    def slot_btn_setting_clicked(self):
        dlg = AmountSettingDialog()
        result = dlg.exec()
        if result == QDialog.Accepted:
            self.logger.info("更新成交额设置")
            # 暂未计算成交额的均线
            # auto_ma_calulate(self.df_data)
            # 刷新K线图
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
        # 成交额图只需要考虑amount列的最大值，最小值始终为0
        max_amount = visible_data['amount'].max()
        max_amount = max_amount / 100000000     # 单位：亿
        
        # 添加一些padding以确保柱状图不会触及顶部边界
        padding = max_amount * 0.05  # 5%的padding
        y_min = 0  # 成交额最小值始终为0
        y_max = max_amount + padding
        
        # 重新设置Y轴刻度
        self.plot_widget.setYRange(y_min, y_max, padding=0)

    def slot_global_update_labels(self, sender, closest_index):
        if self.df_data is None or self.df_data.empty:
            return
        
        if self.type != sender.type:
            # self.logger.info(f"不响应其他窗口的鼠标移动事件")
            return
        amount = self.df_data.iloc[closest_index]['amount'] / 100000000
        self.label_total_amount.setText(f"总金额：{amount:.2f}亿")

        change_percent = self.df_data.iloc[closest_index]['change_percent']
        if change_percent > 0:
            self.label_total_amount.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_ASC.value]};")
        else:
            self.label_total_amount.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_DESC.value]};")


        dict_settings = get_indicator_config_manager().get_user_config_by_indicator_type(self.indicator_type)
        self.dict_ma_label = {
            0: self.label_ma5,
            1: self.label_ma10,
            2: self.label_ma20
        }
        for id, setting in dict_settings.items():
            if id in self.dict_ma_label.keys() and setting.name in self.df_data.columns:
                # 暂未计算成交量的均线
                # self.dict_ma_label[id].setText(f"{setting.name}:{self.df_data.iloc[closest_index][setting.name]:.2f}")
                # self.dict_ma_label[id].setVisible(setting.visible)
                self.dict_ma_label[id].setStyleSheet(f"color: {setting.color_hex}")

    def slot_global_reset_labels(self, sender):
        self.slot_global_update_labels(sender, -1)

    def slot_v_line_mouse_moved(self, sender, x_pos):
        # self.logger.info(f"正在处理{self.get_chart_name()}鼠标移动响应, self: {self}, sender: {sender}")
        if self.type != sender.type:
            # self.logger.info(f"不响应其他窗口的鼠标移动事件")
            return
        self.v_line.setPos(x_pos)
        self.v_line.show()