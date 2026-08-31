# coding:utf-8
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from gui.qt_widgets.MComponents.qfluentwidgets import ScrollArea, isDarkTheme, FluentIcon
from gui.qt_widgets.MComponents.review.danmaku_widget import DanmakuReviewWidget, _make_sample_items, _make_sample_items_by_list
from manager.bao_stock_data_manager import BaostockDataManager

from ..common.style_sheet import StyleSheet
from ..common.signal_bus import signalBus
from ..common.icon import Icon

import random

class HomeInterface(ScrollArea):
    """ Home interface """
    result_selected = pyqtSignal(object)
    manual_select_clicked = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent=parent)
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
        self.view.result_selected.connect(self.slot_danmaku_result_selected)
        self.view.manual_select_clicked.connect(self.manual_select_clicked)

    def load_sample_data(self):
        self.view.set_data(_make_sample_items())
    def slot_bao_stock_info_query_started(self, task_id):
        pass

    def slot_bao_stock_info_query_finished(self, task_id, result):
        if result["result"]:

            dict_code_name = BaostockDataManager().get_all_stock_code_name_dict()

            # print(f"dict_code_name长度：{dict_code_name}")

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

            self.view.set_data(_make_sample_items_by_list(list_danmaku_data))

        else:
            print(f"查询股票信息失败！")

    def slot_bao_stock_info_query_error(self, task_id, error):
        pass

    def slot_danmaku_result_selected(self, item):
        print(f"选中的弹幕：{item.text}")
        self.result_selected.emit(item)

    def slot_manual_select_clicked(self):
        print(f"手动选择弹幕, self: {self}")
        signalBus.switchToInterface.emit(self)