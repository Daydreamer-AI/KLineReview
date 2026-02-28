from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QVBoxLayout
from PyQt5.QtCore import pyqtSlot, QTimer

class MarketWaitWidget(QWidget):
    def __init__(self, parent = None):
        super(MarketWaitWidget, self).__init__(parent)

        uic.loadUi("./src/gui/qt_widgets/market/MarketWaitWidget.ui", self)

        self.init_para()
        self.init_ui()
        self.init_connect()
        

    def init_para(self):
        pass

    def init_ui(self):
        pass

    def init_connect(self):
        pass

