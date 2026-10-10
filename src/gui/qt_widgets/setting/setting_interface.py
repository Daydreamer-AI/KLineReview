# coding:utf-8
from gui.qt_widgets.MComponents.qfluentwidgets import (SettingCardGroup, SwitchSettingCard, FolderListSettingCard,
                            OptionsSettingCard, PushSettingCard,
                            HyperlinkCard, PrimaryPushSettingCard, ScrollArea,
                            ComboBoxSettingCard, ExpandLayout, Theme, CustomColorSettingCard, Pivot, qrouter, 
                            setTheme, setThemeColor, RangeSettingCard, isDarkTheme)
from gui.qt_widgets.MComponents.qfluentwidgets import FluentIcon as FIF
from gui.qt_widgets.MComponents.qfluentwidgets import InfoBar
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QStandardPaths
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget, QLabel, QStackedWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame

from common.config import cfg, HELP_URL, FEEDBACK_URL, AUTHOR, VERSION, YEAR, isWin11
from common.signal_bus import signalBus
from common.style_sheet import StyleSheet

from .general_setting_interface import GeneralSettingInterface
from .review_setting_interface import ReviewSettingInterface
from .baostock_setting_interface import BaostockSettingInterface
from .akshare_setting_interface import AKShareSettingInterface
from .tushare_setting_interface import TuShareSettingInterface


class SettingInterface(QWidget):
    """ Setting interface """

    Nav = Pivot
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('settingInterface')

        self.pivot = self.Nav(self)
        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout = QVBoxLayout(self)

        self.generalInterface = GeneralSettingInterface(self)
        self.reviewInterface = ReviewSettingInterface(self)
        # self.baostockInterface = BaostockSettingInterface(self)
        # self.akshareInterface = AKShareSettingInterface(self)
        # self.tushareInterface = TuShareSettingInterface(self)

        # add items to pivot
        self.addSubInterface(self.generalInterface, 'generalInterface', self.tr('General'))
        self.addSubInterface(self.reviewInterface, 'reviewInterface', self.tr('Review'))
        # self.addSubInterface(self.baostockInterface, 'baostockInterface', self.tr('Baostock'))
        # self.addSubInterface(self.akshareInterface, 'akshareInterface', self.tr('AKShare'))
        # self.addSubInterface(self.tushareInterface, 'tushareInterface', self.tr('TuShare'))

        self.vBoxLayout.addWidget(self.pivot, 0, Qt.AlignLeft)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        StyleSheet.SETTING_INTERFACE.apply(self)

        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)
        self.stackedWidget.setCurrentWidget(self.generalInterface)
        self.pivot.setCurrentItem(self.generalInterface.objectName())

        qrouter.setDefaultRouteKey(self.stackedWidget, self.generalInterface.objectName())

    def addSubInterface(self, widget: QLabel, objectName, text):
        widget.setObjectName(objectName)
        widget.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(
            routeKey=objectName,
            text=text,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget)
        )

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        self.pivot.setCurrentItem(widget.objectName())
        qrouter.push(self.stackedWidget, widget.objectName())