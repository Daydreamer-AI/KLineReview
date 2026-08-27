# coding:utf-8
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush, QPainterPath, QLinearGradient
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

from gui.qt_widgets.MComponents.qfluentwidgets import ScrollArea, isDarkTheme, FluentIcon
from ..common.config import cfg, HELP_URL, REPO_URL, EXAMPLE_URL, FEEDBACK_URL
from ..common.icon import Icon, FluentIconBase
# from ..components.link_card import LinkCardView
# from ..components.sample_card import SampleCardView
from ..common.style_sheet import StyleSheet

from ..MComponents.review.review_widget import ReviewWidget


class ReviewInterface(ScrollArea):
    """ Review interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.view = ReviewWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self.__initWidget()

    def __initWidget(self):
        self.view.setObjectName('view')
        self.setObjectName('reviewInterface')
        StyleSheet.REVIEW_INTERFACE.apply(self)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 36)
        self.vBoxLayout.setSpacing(40)
        # self.vBoxLayout.addWidget(self.banner)
        self.vBoxLayout.setAlignment(Qt.AlignTop)

    def slot_bao_stock_info_query_started(self, task_id):
        self.view.slot_bao_stock_info_query_started(task_id)

    def slot_bao_stock_info_query_finished(self, task_id, result):
        self.view.slot_bao_stock_info_query_finished(task_id, result)

    def slot_bao_stock_info_query_error(self, task_id, error):
        self.view.slot_bao_stock_info_query_error(task_id, error)