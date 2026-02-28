from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import pyqtSlot, QTimer

from processor.baostock_processor import BaoStockProcessor

from common.common_api import *
import datetime
from manager.logging_manager import get_logger

from indicators import stock_data_indicators as sdi

import numpy as np
import pyqtgraph as pg
import time

from gui.qt_widgets.MComponents.stock_card_widget import StockCardWidget

from gui.qt_widgets.MComponents.indicators.indicators_view_widget import IndicatorsViewWidget

from manager.period_manager import TimePeriod
from manager.bao_stock_data_manager import BaostockDataManager

class MarketWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.init_para()
        self.init_ui()
        self.init_connect()

    def init_para(self):
        self.logger = get_logger(__name__)

        self.dict_lastest_1d_stock_data = None # {'code': DataFrame}

        self.set_current_dict_1d_stock_keys = None   # 用于检测数据更新

        self.option_to_code_map = {}  # name - code 映射字典
    def init_ui(self):
        uic.loadUi('./src/gui/qt_widgets/market/MarketWidget.ui', self)

        
        main_h_layout = self.layout()
        if main_h_layout is None:
            self.setLayout(QHBoxLayout())
            main_h_layout = self.layout()

        self.indicators_view_widget = IndicatorsViewWidget()
        main_h_layout.addWidget(self.indicators_view_widget)

    def init_stock_card_list(self):
        if self.dict_lastest_1d_stock_data is None or self.dict_lastest_1d_stock_data == {}:
            return

        self.listWidget_card.clear()

        first_item_data = None  # 保存第一个item的数据
        search_option_list = []
        for code, df_data in self.dict_lastest_1d_stock_data.items():
            # 确保数据不为空
            if df_data.empty:
                continue

            row = df_data.iloc[-1]
            stock_card_widget = StockCardWidget(2)
            stock_card_widget.set_data(row)
            stock_card_widget.update_ui()

            stock_card_widget.clicked.connect(self.slot_stock_card_clicked)
            # stock_card_widget.hovered.connect(self.slot_stock_card_hovered)
            # stock_card_widget.hoverLeft.connect(self.slot_stock_card_hover_left)
            # stock_card_widget.doubleClicked.connect(self.slot_stock_card_double_clicked)

            item = QtWidgets.QListWidgetItem()
            # item.setSizeHint(stock_card_widget.sizeHint())
            item.setSizeHint(QtCore.QSize(200, 60))
            
            self.listWidget_card.addItem(item)

            self.listWidget_card.setItemWidget(item, stock_card_widget)

            # self.logger.info(f"row的类型为：{type(row)}")
            name = row['name']
            option = f"{name} - {code}"
            search_option_list.append(option)
            self.option_to_code_map[option] = code  # 保存映射关系方便后续访问

            # 保存第一个item的数据
            if first_item_data is None:
                first_item_data = row

        self.lineEdit_search.set_options(search_option_list)
        # 如果有数据，自动选择第一个item（使用定时器延迟执行）
        if first_item_data is not None:
            # 使用单次定时器确保UI完全初始化后再执行
            QTimer.singleShot(100, lambda: self.select_first_item(first_item_data))

    def init_connect(self):
        self.lineEdit_search.optionSelected.connect(self.slot_stock_card_selected)

    def select_first_item(self, first_item_data):

        """选择第一个item的独立方法"""
        # 设置列表选中第一个
        self.listWidget_card.setCurrentRow(0)

        self.indicators_view_widget.show_default_indicator()

        # 调用槽函数
        self.slot_stock_card_clicked(first_item_data)

    def update_stock_data_dict(self, new_dict_lastest_1d_stock_data):
        self.dict_lastest_1d_stock_data = new_dict_lastest_1d_stock_data
        self.logger.info(f"成功获取股票数据，日线数据数量为：{len(self.dict_lastest_1d_stock_data)}，即将初始化行情股票列表")
        board_start_time = time.time()  # 记录开始时间
        self.init_stock_card_list()
        elapsed_time = time.time() - board_start_time  # 计算耗时
        self.logger.info(f"初始化行情股票列表完成，耗时: {elapsed_time:.2f}秒，即{elapsed_time/60:.2f}分钟")

    # ----------------------槽函数-------------------------
    def slot_stock_card_clicked(self, data):
        '''
            点击股票列表中的股票时，更新图表
            data: pandas Series
        '''
        # self.logger.info(f"点击的股票数据为：{data}")

        # self.kline_widget.set_stock_name(data['code'])
        # self.update_chart(data)
        self.indicators_view_widget.update_chart(data)
        
    def slot_bao_stock_data_load_finished(self, succsess):
        # self.logger.info(f"Baostock股票数据加载完成，结果为：{succsess}")
        if succsess:
            bao_stock_data_manager = BaostockDataManager()
            new_dict_lastest_1d_stock_data = bao_stock_data_manager.get_all_lastest_row_data_dict_by_period_auto()
           
            self.logger.info(f"成功获取股票数据，日线数据数量为：{len(new_dict_lastest_1d_stock_data)}")

            new_set_lastest_1d_stock_keys = set(new_dict_lastest_1d_stock_data.keys())

            need_update = False

            if (self.dict_lastest_1d_stock_data is None or self.dict_lastest_1d_stock_data == {} ):
                need_update = True
                self.logger.info("当前数据为空，需要更新")
            elif (self.set_current_dict_1d_stock_keys != new_set_lastest_1d_stock_keys):
                need_update = True
                self.logger.info("数据发生变化，需要更新")

            if need_update:
                self.set_current_dict_1d_stock_keys = new_set_lastest_1d_stock_keys
                self.update_stock_data_dict(new_dict_lastest_1d_stock_data)
                self.logger.info("成功加载股票K线指标图")
            else:
                self.logger.info("数据未发生变化，不需要更新")
    def slot_bao_stock_data_load_progress(self, progress):
        self.logger.info(f"Baostock股票数据加载进度：{progress}")
        
    def slot_bao_stock_data_load_error(self, error):
        self.logger.error(f"Baostock股票数据加载出错：{error}")

    def slot_stock_card_selected(self, selected_option):
        
        self.logger.info(f"选中的选项为：{selected_option}")
        # 直接从映射字典中获取股票代码
        stock_code = self.option_to_code_map.get(selected_option)
        self.logger.info(f"对应的股票代码为：{stock_code}")
        
        # 找到对应行业并选中
        for i in range(self.listWidget_card.count()):
            card_widget = self.listWidget_card.itemWidget(self.listWidget_card.item(i))
            if card_widget and getattr(card_widget.data, 'code', '') == stock_code:
                self.listWidget_card.setCurrentRow(i)
                self.slot_stock_card_clicked(card_widget.data)
                break