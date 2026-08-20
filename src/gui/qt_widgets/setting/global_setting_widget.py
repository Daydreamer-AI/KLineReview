from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QVBoxLayout
from PyQt5.QtCore import pyqtSlot, QDir, QFile

from manager.config_manager import *
from manager.logging_manager import get_logger

class GlobalSettingWidget(QWidget):
    def __init__(self, parent = None):
        super(GlobalSettingWidget, self).__init__(parent)

        uic.loadUi("./src/gui/qt_widgets/setting/GlobalSettingWidget.ui", self)

        self.init_para()
        self.init_ui()
        self.init_connect()
        

    def init_para(self):
        self.logger = get_logger(__name__)

        self.global_config_file_name = 'global_config.json'
        self.config_manager = ConfigManager()
        self.config_manager.set_config_path(self.global_config_file_name)
        self.config_data = {'cache_dir' : 'D:/KLineReview/cache', 'delete_cache' : True}

    def init_ui(self):
        if self.config_manager.has_section('cache'):
            self.lineEdit_cache_dir.setText(self.config_manager.get('cache', 'cache_dir', 'D:/KLineReview/cache'))
            self.checkBox_delete_cache.setChecked(self.config_manager.getbool('cache', 'delete_cache', True))
        else:
            self.config_manager._config_data = self.config_data
            self.config_manager.save()

        self.load_qss()
        
    def init_connect(self):
        self.lineEdit_cache_dir.editingFinished.connect(self.slot_lineEdit_cache_dir_editingFinished)
        self.btn_select_cache_dir.clicked.connect(self.slot_btn_select_cache_dir_clicked)
        self.checkBox_delete_cache.stateChanged.connect(self.slot_checkBox_delete_cache_stateChanged)

    def load_qss(self, theme="default"):
        qss_file_name = f":/theme/{theme}/setting/setting.qss"
        self.logger.info(f"设置模块样式表文件路径：{qss_file_name}")
        qssFile = QFile(qss_file_name)
        if qssFile.open(QFile.ReadOnly):
            # self.logger.info(f"内容：{str(qssFile.readAll())}")
            self.setStyleSheet(str(qssFile.readAll(), encoding='utf-8'))
        else:
            self.logger.warning("无法打开设置模块样式表文件")

        qssFile.close()

    def slot_lineEdit_cache_dir_editingFinished(self):
        cache_dir = self.lineEdit_cache_dir.text()
        self.logger.info('新缓存目录：' + cache_dir)

        q_cache_dir = QDir(cache_dir)
        if not q_cache_dir.exists():
            q_cache_dir.mkpath(cache_dir)

        self.config_data['cache_dir'] = cache_dir
        self.config_manager._config_data = self.config_data
        self.config_manager.save()

    def slot_btn_select_cache_dir_clicked(self):
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择缓存目录", "")
        self.logger.info('用户选择缓存目录：' + folder_path)
        self.lineEdit_cache_dir.setText(folder_path)

        
        q_cache_dir = QDir(folder_path)
        if not q_cache_dir.exists():
            q_cache_dir.mkpath(folder_path)

        self.config_data['cache_dir'] = folder_path
        self.config_manager._config_data = self.config_data
        self.config_manager.save()

    def slot_checkBox_delete_cache_stateChanged(self, state):
       
        if state == QtCore.Qt.Checked:
            self.config_data['delete_cache'] = True
        else:
            self.config_data['delete_cache'] = False

        self.config_manager._config_data = self.config_data
        self.config_manager.save()
