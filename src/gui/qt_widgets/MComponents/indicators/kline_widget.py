from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtWidgets import QApplication, QWidget, QDialog
from PyQt5.QtCore import pyqtSlot, Qt

import pyqtgraph as pg
import numpy as np
import pandas as pd

from manager.logging_manager import get_logger

from gui.qt_widgets.MComponents.indicators.base_indicator_widget import BaseIndicatorWidget, signal_manager
from gui.qt_widgets.MComponents.indicators.item.candlestick_item import CandlestickItem
from gui.qt_widgets.MComponents.indicators.setting.kline_indicator_setting_dialog import KLineIndicatorSettingDialog

from manager.indicators_config_manager import *
from gui.qt_widgets.MComponents.indicators.kline_overview_widget import KLineOverviewWidget
from indicators.stock_data_indicators import *

class KLineWidget(BaseIndicatorWidget):
    def __init__(self, data, type, parent=None):
        # 调用父类初始化，这会自动调用init_para, init_ui, init_connect
        super(KLineWidget, self).__init__(data, type, parent)

        self.custom_init()

        # # 使用pg.TextItem作为k线图中的概览标签。问题：标签不会缩视图缩放固定。
        # main_viewbox = self.plot_widget.getViewBox()
        # self.label_overview = pg.TextItem("", anchor=(0, 0.5))
        # self.label_overview.setZValue(1000)
        
        # font = pg.QtGui.QFont("Arial", 10, pg.QtGui.QFont.Bold)
        # self.label_overview.setFont(font)
        
        # main_viewbox.addItem(self.label_overview, ignoreBounds=True)
        # self.label_overview.hide()

        # 使用QWidget作为概览标签弹窗显示。问题：会影响鼠标移动交互。解决：设置十字线位置后手动刷新
        self.overview_widget = KLineOverviewWidget(self)
        self.overview_widget.setFixedSize(200, 360)

        self.overview_widget.move(80, 40)    # 60是同步y轴宽度的位置 self.frame_title.height()
        self.overview_widget.hide()

        self.load_qss()

    def custom_init(self):
        self.label_ma20.hide()
        self.label_ma30.hide()
        self.label_ma60.hide()

        self.btn_restore.clicked.connect(self.slot_btn_restore_clicked)
        self.btn_zoom_in.clicked.connect(self.slot_btn_zoom_in_clicked)
        self.btn_zoom_out.clicked.connect(self.slot_btn_zoom_out_clicked)
        self.btn_setting.clicked.connect(self.slot_btn_setting_clicked)

    def init_para(self, data):
        self.logger = get_logger(__name__)
        # 检查是否有数据
        if data is None or data.empty:
            # raise ValueError("数据为空，无法绘制k线图")
            self.logger.warning("数据为空，无法绘制k线图")
            return
        
        # 确保数据列存在
        required_columns = ['open', 'high', 'low', 'close']
        if not all(col in data.columns for col in required_columns):
            self.logger.warning("缺少必要的数据列来绘制k线图")
            raise ValueError("缺少必要的数据列来绘制k线图")
        
        
        self.df_data = data

    def load_qss(self):
        # self.label_ma_period.setStyleSheet("color: #f0be83") # rgb(240, 190, 131)
        # self.label_stock_name.setStyleSheet("color: #f0be83")
        # self.label_ma5.setStyleSheet(f"color: {dict_ma_color_hex[f'{IndicatrosEnum.MA.value}5']}")
        # self.label_ma10.setStyleSheet(f"color: {dict_ma_color_hex[f'{IndicatrosEnum.MA.value}10']}")
        # self.label_ma20.setStyleSheet(f"color: {dict_ma_color_hex[f'{IndicatrosEnum.MA.value}20']}")
        # self.label_ma24.setStyleSheet(f"color: {dict_ma_color_hex[f'{IndicatrosEnum.MA.value}24']}")
        # self.label_ma30.setStyleSheet(f"color: {dict_ma_color_hex[f'{IndicatrosEnum.MA.value}30']}")
        # self.label_ma52.setStyleSheet(f"color: {dict_ma_color_hex[f'{IndicatrosEnum.MA.value}52']}")
        # self.label_ma60.setStyleSheet(f"color: {dict_ma_color_hex[f'{IndicatrosEnum.MA.value}60']}")

        self.dict_ma_label = {
            0: self.label_ma5,
            1: self.label_ma10,
            2: self.label_ma20,
            3: self.label_ma24,
            4: self.label_ma30,
            5: self.label_ma52,
            6: self.label_ma60,
        }
        dict_ma_settings = get_indicator_config_manager().get_user_config_by_indicator_type(IndicatrosEnum.MA.value)
        for id, ma_setting in dict_ma_settings.items():
            if id in self.dict_ma_label.keys():
                self.dict_ma_label[id].setStyleSheet(f"color: {ma_setting.color_hex}")


    def addtional_connect(self):
        # self.sig_v_line_moved.connect(self.slot_v_line_moved)     # 这里只能通过self实例连接类信号，这样的问题就是，只能响应当前类的图表鼠标移动事件。
        pass

    def get_ui_path(self):
        return './src/gui/qt_widgets/MComponents/indicators/KLineWidget.ui'
    
    def reset_labels(self):
        # self.label_ma_period.setText("")      # 选中周期时设置
        self.label_stock_name.setText("")   # 点击卡片Item时，根据当前选中的股票设置
        self.label_ma5.setText(f"MA5: ")
        self.label_ma10.setText(f"MA10: ")
        self.label_ma20.setText(f"MA20: ")
        self.label_ma24.setText(f"MA24: ")
        self.label_ma30.setText(f"MA30: ")
        self.label_ma52.setText(f"MA52: ")
        self.label_ma60.setText(f"MA60: ")

    # def update_labels(self, closest_index):
    #     self.label_ma5.setText(f"MA5:{self.df_data.iloc[closest_index]['ma5']:.2f}")
    #     self.label_ma10.setText(f"MA10:{self.df_data.iloc[closest_index]['ma10']:.2f}")
    #     self.label_ma20.setText(f"MA20:{self.df_data.iloc[closest_index]['ma20']:.2f}")
    #     self.label_ma24.setText(f"MA24:{self.df_data.iloc[closest_index]['ma24']:.2f}")
    #     self.label_ma30.setText(f"MA30:{self.df_data.iloc[closest_index]['ma30']:.2f}")
    #     self.label_ma52.setText(f"MA52:{self.df_data.iloc[closest_index]['ma52']:.2f}")
    #     self.label_ma60.setText(f"MA60:{self.df_data.iloc[closest_index]['ma60']:.2f}")
    
    def validate_data(self):
        required_columns = ['open', 'high', 'low', 'close']
        return all(col in self.df_data.columns for col in required_columns)
    
    def create_and_add_item(self):
        if self.item is None:
            self.item = CandlestickItem(self.df_data)
        else:
            self.item.update_data(self.df_data)
            
        self.plot_widget.addItem(self.item)

    def set_axis_ranges(self):
        data_high = np.max(self.df_data['high'])
        data_low = np.min(self.df_data['low'])
        self.plot_widget.setXRange(-1, len(self.df_data) + 1, padding=0)
        self.plot_widget.setYRange(data_low * 0.95, data_high * 1.05, padding=0)

    def get_chart_name(self):
        return "K线图"
    
    def is_ma_show(self):
        return self.item.is_ma_show() if self.item else False
    
    def show_ma(self, b_show=True):
        if self.item:
            self.item.show_ma(b_show)

    def set_period_text(self, period):
        self.label_ma_period.setText(period)

    def set_stock_name(self, stock_name):
        self.label_stock_name.setText(stock_name)

    def get_overview_text_with_style(self, index, y_val):
        '''获取概览标签的文本，并设置样式'''
        if self.df_data is None or self.df_data.empty:
            return ""

        row = self.df_data.iloc[index]
        date = row['date']
        open = row['open']
        close = row['close']
        high = row['high']
        low = row['low']
        change_percent = row['change_percent']
        amplitude = (high - low) / low * 100
        volume = row['volume'] / 10000      # 单位：万
        amount = row['amount'] / 100000000  # 单位：亿
        turnover_rate = row['turnover_rate']
        volume_ratio = row['volume_ratio']


        label_text = f"日期: {date}<br>数值：{y_val:.2f}<br>开盘：{open:.2f} <br>收盘: {close:.2f} \
            <br>最高: {high:.2f} <br>最低: {low:.2f}<br>涨跌幅: {change_percent:.2f}%<br>振幅: {amplitude:.2f}%\
                <br>成交量：{volume:.2f}万<br>成交额：{amount:.2f}亿<br>换手率：{turnover_rate:.2f}%<br>量比：{volume_ratio:.2f}"
        
        text_with_style = '<div style="color: black; background-color: white; border: 3px solid black; padding: 2px;">{}</div>'.format(label_text)
        return text_with_style
    
    def update_overview_widget_qss(self, index, y_val):
        if index < 0 or index >= len(self.df_data): return
    
    # def show_overview_label(self, index, y_val, bool_show=True):
    #     if bool_show:
            
    #         text_with_style = self.get_overview_text_with_style(index, y_val)
    #         # self.logger.info(f"显示概览标签：\n{text_with_style}")
    #         self.label_overview.setHtml(text_with_style)
    #         self.label_overview.show()
    #     else:
    #         self.label_overview.hide()
    #         self.logger.info("隐藏概览标签")

    # def hide_overview_label(self):
    #     self.label_overview.hide()

    def update_widget_labels(self):
        self.slot_global_update_labels(self, -1)

    def set_indicator_name(self, indicator_name):
        self.label_indicator.setText(indicator_name)

    def slot_btn_restore_clicked(self):
        self.reset_zoom()

    def slot_btn_zoom_in_clicked(self):
        self.zoom_in()

    def slot_btn_zoom_out_clicked(self):
        self.zoom_out()

    def slot_btn_setting_clicked(self):
        dlg = KLineIndicatorSettingDialog()
        result = dlg.exec()
        if result == QDialog.Accepted:
            self.logger.info("更新k线设置")
            auto_ma_calulate(self.df_data)
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
        required_columns = []
        if 'high' in visible_data.columns and 'low' in visible_data.columns:
            required_columns.extend(['high', 'low'])
        
        # TODO: 如果MA线显示，也需要考虑MA线的值
        ma_columns = ['ma5', 'ma10', 'ma20', 'ma30', 'ma60']
        for col in ma_columns:
            if col in visible_data.columns and self.is_ma_show():
                required_columns.append(col)
                
        if not required_columns:
            return
        
        # 计算可见范围内的最大值和最小值
        max_val = visible_data[required_columns].max().max()
        min_val = visible_data[required_columns].min().min()
        
        # 添加一些padding以确保K线不会触及边界
        padding = (max_val - min_val) * 0.05  # 5%的padding
        y_min = min_val - padding
        y_max = max_val + padding
        
        # 重新设置Y轴刻度
        self.plot_widget.setYRange(y_min, y_max, padding=0)

    def slot_global_update_labels(self, sender, closest_index):
        if self.df_data is None or self.df_data.empty:
            return
        
        if self.type != sender.type:
            # self.logger.info(f"不响应其他窗口的鼠标移动事件")
            return

        # 设置MA值
        dict_ma_settings = get_indicator_config_manager().get_user_config_by_indicator_type(IndicatrosEnum.MA.value)

        self.dict_ma_label = {
            0: self.label_ma5,
            1: self.label_ma10,
            2: self.label_ma20,
            3: self.label_ma24,
            4: self.label_ma30,
            5: self.label_ma52,
            6: self.label_ma60,
        }
        for id, ma_setting in dict_ma_settings.items():
            if id in self.dict_ma_label.keys() and ma_setting.name in self.df_data.columns:
                self.dict_ma_label[id].setText(f"{ma_setting.name}:{self.df_data.iloc[closest_index][ma_setting.name]:.2f}")
                self.dict_ma_label[id].setVisible(ma_setting.visible)
                self.dict_ma_label[id].setStyleSheet(f"color: {ma_setting.color_hex}")

    def slot_global_reset_labels(self, sender):
        self.slot_global_update_labels(sender, -1)
            
    def slot_global_show_overview_label(self, sender, index, y_val, x_pos, y_pos, bool_show=True):
        if self.type != sender.type:
            # self.logger.info(f"不响应其他窗口的鼠标移动事件")
            return
        # self.logger.info(f"正在处理{self.get_chart_name()}全局显示数据标签，数据长度：{len(self.df_data)}，位置：{x_pos}，{y_pos}, 数据索引：{index}, 数据值：{y_val}，是否显示：{bool_show}")

        # 不能在子类中通过self.plot_widget.getViewBox().viewRange() 计算显示位置。
        # self.label_overview.setPos(x_pos, y_pos)


        # self.logger.info(f"全局显示数据标签位置：{x_pos}, {y_pos}")
        # self.logger.info(f"子类计算出的数据标签位置：{x_pos_2}, {y_pos_2}")

        # self.logger.info(f"view_range:\n{view_range}")
        # self.label_overview.setPos(x_pos, y_pos)
        # if x_pos is not None and index is not None:
        #     view_range = self.plot_widget.getViewBox().viewRange()
        #     # self.logger.info(f"view_range:\n{view_range}")
        #     x_view_center = abs(view_range[0][0] - view_range[0][1]) / 2
        #     y_view_center = abs(view_range[1][0] - view_range[1][1]) / 2 
        #     self.logger.info(f"x_view_center:{x_view_center}, y_view_center:{y_view_center}")
        #     self.label_overview.setPos(x_view_center, y_view_center)
        #     # if x_pos >= len(self.df_data) - 3:
        #     #     self.label_overview.setPos(x_view_center, y_view_center)    # view_range[0][0], view_range[1][1]
        #     # else:
        #     #     self.label_overview.setPos(x_view_center, y_view_center)    # view_range[0][1], view_range[1][1]

        # self.show_overview_label(index, y_val, bool_show)

        if not hasattr(self, 'overview_widget') or self.overview_widget is None:
            return
    
        if bool_show:
            if index < 0 or index >= len(self.df_data): 
                return
            
            if self.df_data is None or self.df_data.empty:
                return

            if index == 0:
                last_row = None  # 第一行没有上一行
            else:
                last_row = self.df_data.iloc[index - 1] if index > 0 else None

            current_row = self.df_data.iloc[index] if index >= 0 and index < len(self.df_data) else None

            self.overview_widget.update_labels(last_row, current_row, y_val)


            # html_text = self.get_overview_text_with_style(index, y_val)
            # self.label_overview.setText(html_text)
            self.overview_widget.update_labels(last_row, current_row, y_val)

            # 自动更新概览标签位置，避免遮挡K线。
            view_range = self.plot_widget.getViewBox().viewRange()
            left_x = view_range[0][0]
            right_x = view_range[0][1]
            limit_range = (right_x - left_x) / 3
            left_x_limit = left_x + limit_range
            right_x_limit = right_x - limit_range
            # self.logger.info(f"view_range:\n{view_range}")
            if x_pos >= left_x and x_pos <= left_x_limit:
                self.overview_widget.move(self.width() - self.overview_widget.width(), 40)
            elif x_pos >= right_x_limit and x_pos <= right_x:
                self.overview_widget.move(80, 40)     # 注意不能使用plot_widget视图坐标设置上层的overview_widget的位置。

            self.overview_widget.show()
            self.plot_widget.prepareGeometryChange()    # 手动刷新避免十字线重影
            self.plot_widget.update()
        else:
            self.overview_widget.hide()

    # 处理有些重复，为什么不能直接放父类中？因为父类中不能处理其他所有子类的鼠标移动事件。若是只需要处理当前视图鼠标移动事件，可放在父类中处理（如：只在触发鼠标事件的视图中显示y轴水平、y轴标签，而所有视图都需显示x轴垂直线，则放在子类中处理）
    # def slot_h_line_mouse_moved(self, y_pos, widget_source=None):
    #     if widget_source is not None:
    #         # self.logger.info(f"正在处理{self.get_chart_name()}鼠标移动响应，来源：{widget_source.get_chart_name()}")
    #         widget_source_chart_name = widget_source.get_chart_name()
    #     else:
    #         # self.logger.info(f"widget_source is not None")
    #         return
        
    #     chart_name = self.get_chart_name()

    #     if chart_name == widget_source_chart_name:
    #         self.h_line.setPos(y_pos)
    #         self.h_line.show()
    #     else:
    #         self.h_line.hide()

    def slot_v_line_mouse_moved(self, sender, x_pos):
        # self.logger.info(f"正在处理{self.get_chart_name()}鼠标移动响应, self: {self}, sender: {sender}")
        # self.logger.info(f"self.type: {self.type}, sender.type: {sender.type}")
        if self.type != sender.type:
            # self.logger.info(f"不响应其他窗口的鼠标移动事件")
            return
        self.v_line.setPos(x_pos)
        self.v_line.show()
