# coding:utf-8
from gui.qt_widgets.MComponents.qfluentwidgets import (SettingCardGroup, SwitchSettingCard, FolderListSettingCard,
                            OptionsSettingCard, PushSettingCard,
                            HyperlinkCard, PrimaryPushSettingCard, ScrollArea,
                            ComboBoxSettingCard, ExpandLayout, FlowLayout, ImageLabel, CustomColorSettingCard,
                            setTheme, setThemeColor, RangeSettingCard, isDarkTheme)
from gui.qt_widgets.MComponents.qfluentwidgets import FluentIcon as FIF
from gui.qt_widgets.MComponents.qfluentwidgets import InfoBar
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QStandardPaths
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget, QLabel, QFileDialog

from common.config import cfg, HELP_URL, FEEDBACK_URL, AUTHOR, VERSION, YEAR, isWin11
from common.signal_bus import signalBus
from common.style_sheet import StyleSheet


class GeneralDonateInterface(ScrollArea):
    """ Baostock Setting interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.center_widget = QWidget()
        self.flow_layout = FlowLayout(self.center_widget, True)

        self.flow_layout.setContentsMargins(0, 0, 0, 0)
        self.flow_layout.setVerticalSpacing(30)
        self.flow_layout.setHorizontalSpacing(30)

        self.__initWidget()


    def __initWidget(self):
        self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(30, 30, 30, 30)
        self.setWidget(self.center_widget)
        self.setWidgetResizable(True)
        self.setObjectName('GeneralDonateInterface')

        # initialize style sheet
        self.center_widget.setObjectName('centerWidget')

        self.wechat_image_label = ImageLabel(":/images/donate/WeChat.jpg", self.center_widget)
        self.airplay_image_label = ImageLabel(":/images/donate/Airplay.jpg", self.center_widget)
        self.binance_image_label = ImageLabel(":/images/donate/binance.jpg", self.center_widget)
        self.okx_image_label = ImageLabel(":/images/donate/OKX.jpg", self.center_widget)

        self.wechat_image_label.setFixedSize(600, 800)
        self.airplay_image_label.setFixedSize(600, 800)
        self.binance_image_label.setFixedSize(600, 800)
        self.okx_image_label.setFixedSize(600, 800)


        # initialize layout
        self.__initLayout()
    
    def __initLayout(self):
        self.flow_layout.addWidget(self.wechat_image_label)
        self.flow_layout.addWidget(self.airplay_image_label)
        self.flow_layout.addWidget(self.binance_image_label)
        self.flow_layout.addWidget(self.okx_image_label)