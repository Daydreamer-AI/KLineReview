from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import pyqtSlot

import pyqtgraph as pg
import numpy as np

from manager.logging_manager import get_logger
from gui.qt_widgets.MComponents.indicators.base_indicator_widget import BaseIndicatorWidget, signal_manager
from gui.qt_widgets.MComponents.indicators.item.volume_item import VolumeItem

from manager.indicators_config_manager import *
from gui.qt_widgets.MComponents.indicators.setting.volume_setting_dialog import VolumeSettingDialog

class VolumeWidget(BaseIndicatorWidget):
    def __init__(self, data, type, parent=None):
        super(VolumeWidget, self).__init__(data, type, parent)
        self.custom_init()
        self.load_qss()

    def custom_init(self):
        self.label_ma5.hide()
        self.label_ma10.hide()
        self.label_ma20.hide()

        self.btn_close.hide()

        self.btn_setting.clicked.connect(self.slot_btn_setting_clicked)

    def init_para(self, data):
        self.logger = get_logger(__name__)

        self.indicator_type = IndicatrosEnum.VOLUME.value

        if data is None or data.empty:
            # raise ValueError("数据为空，无法绘制成交量指标图")
            self.logger.warning("数据为空，无法绘制成交量指标图")
            return
        
        required_columns = ['open', 'close', 'volume']
        if not all(col in data.columns for col in required_columns):
            raise ValueError("缺少必要的数据列来绘制成交量指标图")
        
        self.df_data = data

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

    def addtional_connect(self):
        pass

    def get_ui_path(self):
        return './src/gui/qt_widgets/MComponents/indicators/VolumeWidget.ui'
    
    def validate_data(self):
        required_columns = ['open', 'close', 'volume']
        return all(col in self.df_data.columns for col in required_columns)
    
    def create_and_add_item(self):
        if self.item is None:
            self.item = VolumeItem(self.df_data)
        else:
            self.item.update_data(self.df_data)
            
        self.plot_widget.addItem(self.item)
    
    def set_axis_ranges(self):
        self.plot_widget.setXRange(-1, len(self.df_data) + 1, padding=0)
        max_vol = np.max(self.df_data['volume'])
        # self.logger.info(f"最大成交量-max_vol: {max_vol}")
        self.plot_widget.setYRange(0, max_vol / 10000 * 1.1, padding=0)
    
    def get_chart_name(self):
        return "成交量"
    
    def update_widget_labels(self):
        self.slot_global_update_labels(self, -1)

    def slot_btn_setting_clicked(self):
        dlg = VolumeSettingDialog()
        result = dlg.exec()
        if result == QDialog.Accepted:
            self.logger.info("更新成交量设置")

            # auto_ma_calulate(self.df_data)
            # 刷新K线图
            self.update_data(self.df_data)
            self.auto_scale_to_latest(120)
    
    def slot_range_changed(self):
        '''当视图范围改变时调用'''
        # y轴坐标值同步
        # 获取可视范围内的数据
        visible_data, x_min, x_max = self.get_visible_data_range()
        if visible_data is None or visible_data.empty:
            return
        
        # 根据当前可视范围内的数据的最大、最小值调整Y轴坐标值范围
        # 成交量图只需要考虑volume列的最大值，最小值始终为0
        max_volume = visible_data['volume'].max()
        max_volume = max_volume / 10000     # 单位：万
        
        # 添加一些padding以确保柱状图不会触及顶部边界
        padding = max_volume * 0.05  # 5%的padding
        y_min = 0  # 成交量最小值始终为0
        y_max = max_volume + padding
        
        # 重新设置Y轴刻度
        self.plot_widget.setYRange(y_min, y_max, padding=0)

    # def slot_mouse_moved(self, pos, widget_source=None):
    #     if widget_source is not None:
    #         self.logger.info(f"正在处理{self.get_chart_name()}鼠标移动响应，来源：{widget_source.get_chart_name()}")
    #     else:
    #         self.logger.info(f"widget_source is not None")

    #     if self.plot_widget.sceneBoundingRect().contains(pos):
    #         mouse_point = self.plot_widget.getViewBox().mapSceneToView(pos)
    #         x_val = mouse_point.x()
    #         y_val = mouse_point.y()

    #         # self.logger.info(f"鼠标位置：x={x_val}, y={y_val}")

    #         bar_centers = list(range(len(self.df_data)))
            
    #         closest_index = None
    #         min_distance = float('inf')
            
    #         for i, center in enumerate(bar_centers):
    #             distance = abs(center - x_val)
    #             if distance <= 0.25 / 2:
    #                 if distance < min_distance:
    #                     min_distance = distance
    #                     closest_index = i
            
    #         if closest_index is not None:
    #             view_range = self.plot_widget.getViewBox().viewRange()
    #             closest_x = bar_centers[closest_index]

    #             widget_source_plot_widget = widget_source.get_plot_widget()
    #             if widget_source_plot_widget is not None and widget_source_plot_widget == self.plot_widget:
    #                 self.h_line.setPos(y_val)
    #                 self.h_line.show()

    #             self.v_line.setPos(closest_x)
    #             self.v_line.show()
                

    #         # else:
    #         #     self.hide_all_labels()
    #     else:
    #         self.logger.info(f"鼠标位置超出图表范围")
    #         self.hide_all_labels()

    def slot_global_update_labels(self, sender, closest_index):
        if self.df_data is None or self.df_data.empty:
            return

        if self.type != sender.type:
            # self.logger.info(f"不响应其他窗口的鼠标移动事件")
            return
        

        volume = self.df_data.iloc[closest_index]['volume'] / 10000
        self.label_total_volume.setText(f"总量：{volume:.2f}万")

        change_percent = self.df_data.iloc[closest_index]['change_percent']
        if change_percent > 0:
            self.label_total_volume.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_ASC.value]};")
        else:
            self.label_total_volume.setStyleSheet(f"color: {dict_kline_color_hex[IndicatrosEnum.KLINE_DESC.value]};")

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
        
        