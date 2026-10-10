# coding:utf-8
from gui.qt_widgets.MComponents.qfluentwidgets import (SettingCardGroup, SwitchSettingCard, StepSettingCard,
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


class ReviewSettingInterface(ScrollArea):
    """ Review Setting interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # setting label
        # self.settingLabel = QLabel(self.tr("ReviewSettings"), self)

        self.__initWidget()


    def __initWidget(self):
        self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 0, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setObjectName('reviewSettingInterface')

        # initialize style sheet
        self.scrollWidget.setObjectName('scrollWidget')
        # self.settingLabel.setObjectName('settingLabel')
        # StyleSheet.SETTING_INTERFACE.apply(self)

        
        # operation
        self.operationGroup = SettingCardGroup(
            self.tr('Operation'), self.scrollWidget)
        self.ctfCard = SwitchSettingCard(
            '',
            self.tr('Complete the forward'),
            self.tr('Complete the current unfinished candlestick; turn on to also move on to the next one'),
            cfg.ctfEnabled,
            self.operationGroup
        )

        self.openCard = SwitchSettingCard(
            '',
            self.tr('Open first'),
            self.tr('Single-step forward shows the open price first (unfinished), click again to complete it; '
                    'when on, "Complete the forward" is ignored'),
            cfg.openFirst,
            self.operationGroup
        )

        self.regretModeCard = SwitchSettingCard(
            '',
            self.tr('Regret mode'),
            self.tr('Allow k-line backward operation'),
            cfg.regretMode,
            self.operationGroup
        )

        self.stepCard = StepSettingCard(
            cfg.fastForwardStep,
            '',
            self.tr('Fast forward step'),
            self.tr("From {0} to {1}").format(cfg.fastForwardStep.range[0], cfg.fastForwardStep.range[1]),
            self.operationGroup
        )

        # openFirst 优先：开启时“补全并前进”不生效，置灰对应卡片
        cfg.openFirst.valueChanged.connect(self.__openFirstChanged)
        self.__openFirstChanged(cfg.openFirst.value)

        # initialize layout
        self.__initLayout()

    def __openFirstChanged(self, b_open_first):
        """openFirst 开启时抑制 ctfEnabled 的自动前进，置灰“补全并前进”卡片。"""
        self.ctfCard.setEnabled(not b_open_first)
    
    def __initLayout(self):
        # self.settingLabel.move(36, 30)

        # add cards to group
        self.operationGroup.addSettingCard(self.ctfCard)
        self.operationGroup.addSettingCard(self.openCard)
        self.operationGroup.addSettingCard(self.regretModeCard)
        self.operationGroup.addSettingCard(self.stepCard)

        # add setting card group to layout
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
        self.expandLayout.addWidget(self.operationGroup)
