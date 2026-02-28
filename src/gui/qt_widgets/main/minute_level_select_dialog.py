from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QButtonGroup
from PyQt5.QtCore import pyqtSlot

from manager.logging_manager import get_logger

class MinuteLevelSelectDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(MinuteLevelSelectDialog, self).__init__(parent)
        uic.loadUi('./src/gui/qt_widgets/main/MinuteLevelSelectDialog.ui', self)
        
        self.init_para()
        self.init_ui()
        self.init_connect()

        

    def init_para(self):
        self.logger = get_logger(__name__)

    def init_ui(self):
        self.board_type_group = QButtonGroup(self)  # 创建按钮组
        self.board_type_group.addButton(self.radioButton_sh_and_sz_main, 0)
        self.board_type_group.addButton(self.radioButton_sh_main, 1)   # 将按钮加入组，并可分配一个ID
        self.board_type_group.addButton(self.radioButton_sz_main, 2)
        self.board_type_group.addButton(self.radioButton_gem, 3)
        self.board_type_group.addButton(self.radioButton_star, 4)
        self.board_type_group.addButton(self.radioButton_bse, 5)

        self.minute_level_group = QButtonGroup(self)
        self.minute_level_group.addButton(self.radioButton_1m, 1)
        self.minute_level_group.addButton(self.radioButton_3m, 3)
        self.minute_level_group.addButton(self.radioButton_5m, 5)
        self.minute_level_group.addButton(self.radioButton_10m, 10)
        self.minute_level_group.addButton(self.radioButton_15m, 15)
        self.minute_level_group.addButton(self.radioButton_30m, 30)
        self.minute_level_group.addButton(self.radioButton_45m, 45)
        self.minute_level_group.addButton(self.radioButton_60m, 60)
        self.minute_level_group.addButton(self.radioButton_90m, 90)
        self.minute_level_group.addButton(self.radioButton_120m, 120)

        self.radioButton_sh_main.setChecked(True)
        self.radioButton_gem.setEnabled(False)
        self.radioButton_star.setEnabled(False)
        self.radioButton_bse.setEnabled(False)

        self.radioButton_1m.setEnabled(False)
        self.radioButton_3m.setEnabled(False)
        self.radioButton_10m.setEnabled(False)
        self.radioButton_45m.setEnabled(False)
        self.radioButton_90m.setEnabled(False)
        self.radioButton_120m.setEnabled(False)


    def init_connect(self):
        self.board_type_group.buttonClicked.connect(self.slot_board_type_clicked)
        self.board_type_group.buttonToggled.connect(self.slot_board_type_toggled)

        self.minute_level_group.buttonClicked.connect(self.slot_minute_level_clicked)
        self.minute_level_group.buttonToggled.connect(self.slot_minute_level_toggled)

    def get_checked_board_type(self):
        return self.board_type_group.checkedId()
    
    def get_checked_minute_level(self):
        return self.minute_level_group.checkedId()
    
    def get_target_code(self):
        return self.lineEdit_target_code.text()


    def slot_board_type_clicked(self, btn):
        # self.logger.info(f"slot_board_type_clicked. isChecked: {btn.isChecked()}")
        # self.logger.info(f"slot_board_type_clicked. text: {btn.text()}")
        # self.logger.info(f"ID: {self.board_type_group.checkedId()}")
        pass

    def slot_board_type_toggled(self, btn):
        # self.logger.info(f"slot_board_type_toggled. isChecked: {btn.isChecked()}")
        # self.logger.info(f"slot_board_type_toggled. text: {btn.text()}")
        # self.logger.info(f"ID: {self.board_type_group.checkedId()}")
        pass

    def slot_minute_level_clicked(self, btn):
        # self.logger.info(f"slot_minute_level_clicked. isChecked: {btn.isChecked()}")
        # self.logger.info(f"slot_minute_level_clicked. text: {btn.text()}")
        # self.logger.info(f"ID: {self.minute_level_group.checkedId()}")
        pass

    def slot_minute_level_toggled(self, btn):
        # self.logger.info(f"slot_minute_level_toggled. isChecked: {btn.isChecked()}")
        # self.logger.info(f"slot_minute_level_toggled. text: {btn.text()}")
        # self.logger.info(f"ID: {self.minute_level_group.checkedId()}")
        pass
