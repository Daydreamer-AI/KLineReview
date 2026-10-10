from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QStackedWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

from gui.qt_widgets.MComponents.qfluentwidgets import (isDarkTheme, Pivot)
from .general_donate_interface import GeneralDonateInterface
from .on_chain_donate_interface import OnChainDonateInterface

class DonateDialog(QDialog):
    Nav = Pivot
    def __init__(self, parent=None):
        super(DonateDialog, self).__init__(parent)
        uic.loadUi('./src/gui/qt_widgets/setting/DonateDialog.ui', self)

        self.init_para()
        self.init_ui()
        self.init_connect()

    def init_para(self):
        pass

    def init_ui(self):
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)   

        if isDarkTheme():
            self.setStyleSheet("QDialog{background: #1E1E1E;}")
        else:
            self.setStyleSheet("QDialog{background: #F0F0F0;}")

        self.setObjectName('donateDialog')
        
        self.pivot = self.Nav(self)
        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout = QVBoxLayout(self)

        self.generalDonateInterface = GeneralDonateInterface(self)
        self.onChainDonateInterface = OnChainDonateInterface(self)

        # add items to pivot
        self.addSubInterface(self.generalDonateInterface, 'generalDonateInterface', self.tr('General'))
        self.addSubInterface(self.onChainDonateInterface, 'onChainDonateInterface', self.tr('OnChain'))

        self.vBoxLayout.addWidget(self.pivot, 0, Qt.AlignLeft)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.vBoxLayout.setContentsMargins(12, 12, 12, 12)

        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)
        self.stackedWidget.setCurrentWidget(self.generalDonateInterface)
        self.pivot.setCurrentItem(self.generalDonateInterface.objectName())

    def init_connect(self):
        pass

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