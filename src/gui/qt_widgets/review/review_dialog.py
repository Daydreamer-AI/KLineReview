from PyQt5 import QtCore, uic, QtGui
from PyQt5.QtWidgets import QDialog, QMessageBox, QListWidget, QListWidgetItem
from PyQt5.QtCore import QDate


from manager.logging_manager import get_logger

class ReviewDialog(QDialog):
    def __init__(self, parent=None):
        super(ReviewDialog, self).__init__(parent) 
        uic.loadUi('./src/gui/qt_widgets/review/ReviewDialog.ui', self)

        self.init_para()
        self.init_ui()
        self.init_connect()

    def init_para(self):
        self.logger = get_logger(__name__)

    def init_ui(self):
        pass

    def init_connect(self):
        pass

    def preload_data(self, df_row):
        self.review_widget.preload_data(df_row)
