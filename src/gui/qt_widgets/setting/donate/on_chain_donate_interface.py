# coding:utf-8
from gui.qt_widgets.MComponents.qfluentwidgets import (SettingCardGroup, SwitchSettingCard, FolderListSettingCard,
                            OptionsSettingCard, PushSettingCard,
                            HyperlinkCard, PrimaryPushSettingCard, ScrollArea,
                            ImageLabel, ExpandLayout, FlowLayout, CustomColorSettingCard,
                            setTheme, setThemeColor, RangeSettingCard, isDarkTheme)
from gui.qt_widgets.MComponents.qfluentwidgets import FluentIcon as FIF
from gui.qt_widgets.MComponents.qfluentwidgets import InfoBar
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QStandardPaths
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget, QLabel, QFileDialog

from common.config import cfg, HELP_URL, FEEDBACK_URL, AUTHOR, VERSION, YEAR, isWin11
from common.signal_bus import signalBus
from common.style_sheet import StyleSheet


class OnChainDonateInterface(ScrollArea):
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
        self.setObjectName('OnChainDonateInterface')

        self.center_widget.setObjectName('centerWidget')
        
        self.image_label = ImageLabel(":/images/donate/on_chain/Arbitrum.png", self.center_widget)
        self.image_label_1 = ImageLabel(":/images/donate/on_chain/Arc.png", self.center_widget)
        self.image_label_2 = ImageLabel(":/images/donate/on_chain/Base.png", self.center_widget)

        self.image_label_3 = ImageLabel(":/images/donate/on_chain/Bitcoin.png", self.center_widget)
        self.image_label_4 = ImageLabel(":/images/donate/on_chain/BNBChain.png", self.center_widget)
        self.image_label_5 = ImageLabel(":/images/donate/on_chain/Ethereum.png", self.center_widget)

        self.image_label_6 = ImageLabel(":/images/donate/on_chain/Linea.png", self.center_widget)
        self.image_label_7 = ImageLabel(":/images/donate/on_chain/OP.png", self.center_widget)
        self.image_label_8 = ImageLabel(":/images/donate/on_chain/Polygon.png", self.center_widget)

        self.image_label_9 = ImageLabel(":/images/donate/on_chain/Sei.png", self.center_widget)
        self.image_label_10 = ImageLabel(":/images/donate/on_chain/Solana.png", self.center_widget)
        self.image_label_11 = ImageLabel(":/images/donate/on_chain/Tron.png", self.center_widget)

        self.image_label.setFixedSize(600, 800)
        self.image_label_1.setFixedSize(600, 800)
        self.image_label_2.setFixedSize(600, 800)

        self.image_label_3.setFixedSize(600, 800)
        self.image_label_4.setFixedSize(600, 800)
        self.image_label_5.setFixedSize(600, 800)

        self.image_label_6.setFixedSize(600, 800)
        self.image_label_7.setFixedSize(600, 800)
        self.image_label_8.setFixedSize(600, 800)

        self.image_label_9.setFixedSize(600, 800)
        self.image_label_10.setFixedSize(600, 800)
        self.image_label_11.setFixedSize(600, 800)

        # initialize layout
        self.__initLayout()
    
    def __initLayout(self):
        self.flow_layout.addWidget(self.image_label)
        self.flow_layout.addWidget(self.image_label_1)
        self.flow_layout.addWidget(self.image_label_2)

        self.flow_layout.addWidget(self.image_label_3)
        self.flow_layout.addWidget(self.image_label_4)
        self.flow_layout.addWidget(self.image_label_5)

        self.flow_layout.addWidget(self.image_label_6)
        self.flow_layout.addWidget(self.image_label_7)
        self.flow_layout.addWidget(self.image_label_8)

        self.flow_layout.addWidget(self.image_label_9)
        self.flow_layout.addWidget(self.image_label_10)
        self.flow_layout.addWidget(self.image_label_11)