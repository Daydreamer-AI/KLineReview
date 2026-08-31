# coding:utf-8
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from gui.qt_widgets.MComponents.qfluentwidgets import ScrollArea, isDarkTheme, FluentIcon
from gui.qt_widgets.MComponents.review.danmaku_widget import DanmakuReviewWidget, _make_sample_items, _make_sample_items_by_list
from manager.bao_stock_data_manager import BaostockDataManager

from manager.logging_manager import get_logger

from ..common.style_sheet import StyleSheet
from ..common.signal_bus import signalBus
from ..common.icon import Icon

import random

class HomeInterface(ScrollArea):
    """ Home interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.logger = get_logger(__name__)
        self.dict_code_index = {}

        self.view = DanmakuReviewWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self.__initWidget()
        self.__init_connect()
        # self.load_sample_data()

    def __initWidget(self):
        self.view.setObjectName('view')
        # self.view.set_main_icon("dice_icon.svg")
        # self.view.danmaku.set_sub_text("手动选择")
        self.view.set_stop_mode(DanmakuReviewWidget.STOP_AUTO)
        self.view.set_result_hide_mode(DanmakuReviewWidget.RESULT_HIDE_AUTO, duration_ms=3000)
        self.view.global_opacity = 1
        self.view.set_track_count(8)
        self.view.set_main_icon(Icon.DICE)

        self.setObjectName('homeInterface')
        StyleSheet.HOME_INTERFACE.apply(self)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 36)
        self.vBoxLayout.setSpacing(40)
        self.vBoxLayout.setAlignment(Qt.AlignTop)

    def __init_connect(self):
        pass

    def load_sample_data(self):
        self.view.set_data(_make_sample_items())

    def set_fixed_result(self, dict_data):
        code = dict_data['code']
        name = dict_data['name']
        date = dict_data['date']
        period = dict_data['period']
        self.logger.info(f"设置内定数据：{code}, {name}, {date}, {period}")
        if code in self.dict_code_index:
            self.view.set_fixed_result(self.dict_code_index[code])
        
    def slot_bao_stock_info_query_started(self, task_id):
        pass

    def slot_bao_stock_info_query_finished(self, task_id, result):
        if result["result"]:

            dict_code_name = BaostockDataManager().get_all_stock_code_name_dict()

            # self.logger.info(f"dict_code_name长度：{dict_code_name}")
            self.dict_code_index.clear()
            index = 0
            list_danmaku_data = []
            for code, name in dict_code_name.items():
                text = random.choice([code, name])
                dict_item = {
                    "text": text
                    , "color": QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),
                    # "font_size": random.randint(16, 20),
                    # "bold": random.choice([True, False]),
                    # "opacity": random.uniform(0.3, 1.0),
                }

                list_danmaku_data.append(dict_item)

                self.dict_code_index[code] = index
                index += 1

            self.view.set_data(_make_sample_items_by_list(list_danmaku_data))

        else:
            self.logger.info(f"查询股票信息失败！")

    def slot_bao_stock_info_query_error(self, task_id, error):
        pass