# coding:utf-8
from gui.qt_widgets.MComponents.qfluentwidgets import (SettingCardGroup, SwitchSettingCard, FolderListSettingCard,
                            OptionsSettingCard, PushSettingCard,
                            HyperlinkCard, PrimaryPushSettingCard, ScrollArea,
                            ComboBoxSettingCard, ExpandLayout, Theme, CustomColorSettingCard,
                            setTheme, setThemeColor, RangeSettingCard, isDarkTheme)
from gui.qt_widgets.MComponents.qfluentwidgets import FluentIcon as FIF
from gui.qt_widgets.MComponents.qfluentwidgets import InfoBar
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QStandardPaths
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget, QLabel, QFileDialog

from common.config import cfg, HELP_URL, FEEDBACK_URL, AUTHOR, VERSION, YEAR, isWin11
from common.signal_bus import signalBus
from common.style_sheet import StyleSheet

from .tushare_setting.tushare_setting_widget import TuShareSettingWidget


class TuShareSettingInterface(ScrollArea):
    """ TuShare Setting interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)

        self.__initWidget()

    def __initWidget(self):
        self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setObjectName('tushareSettingInterface')

        # initialize style sheet
        self.scrollWidget.setObjectName('scrollWidget')

        # StyleSheet.SETTING_INTERFACE.apply(self)

        self.tushare_setting_widget = TuShareSettingWidget(self)

        # initialize layout
        self.__initLayout()
    
    def __initLayout(self):
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
        self.expandLayout.addWidget(self.tushare_setting_widget)