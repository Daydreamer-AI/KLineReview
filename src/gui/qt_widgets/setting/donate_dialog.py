from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QStackedWidget, QVBoxLayout
from PyQt5.QtCore import Qt

from gui.qt_widgets.MComponents.qfluentwidgets import (isDarkTheme, ColorDialog)

class DonateDialog(QDialog):
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

        

    def init_connect(self):
        pass