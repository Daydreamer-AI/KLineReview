from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QColorDialog
from PyQt5.QtGui import QColor
from functools import partial
from manager.logging_manager import get_logger
from manager.indicators_config_manager import *

class AmountSettingObject(object):
    def __init__(self, id=0, period_lineedit_obj=None, checkbox_obj=None, line_width_lineedit_obj=None, color_obj=None):
        self.id = id
        self.period_lineedit_obj = period_lineedit_obj
        self.checkbox_obj = checkbox_obj
        self.line_width_lineedit_obj = line_width_lineedit_obj
        self.color_obj = color_obj

class AmountSettingDialog(QDialog):
    def __init__(self, parent=None):
        super(AmountSettingDialog, self).__init__(parent)
        uic.loadUi('./src/gui/qt_widgets/MComponents/indicators/setting/AmountSettingDialog.ui', self)

        self.init_para()
        self.init_ui()
        self.init_connect()


    def init_para(self):
        self.logger = get_logger(__name__)

        self.indicator_type = IndicatrosEnum.AMOUNT.value
        
        # 提取Volume配置
        self.dict_setting_user = get_indicator_config_manager().get_user_config_by_indicator_type(self.indicator_type)

        self.dict_setting_object = {
            0: AmountSettingObject(0, self.lineEdit_ma_period, self.checkBox_ma, self.lineEdit_line_width, self.btn_color),
            1: AmountSettingObject(1, self.lineEdit_ma_period_1, self.checkBox_ma_1, self.lineEdit_line_width_1, self.btn_color_1),
            2: AmountSettingObject(2, self.lineEdit_ma_period_2, self.checkBox_ma_2, self.lineEdit_line_width_2, self.btn_color_2)
        }


    def init_ui(self):
        # 遍历配置并设置UI
        for id, setting in self.dict_setting_user.items():
            # self.logger.info(f"setting--id: {setting.id}, period: {setting.period}, name: {setting.name}, visible: {setting.visible}, line_width: {setting.line_width}, color: {setting.color}, color_hex: {setting.color_hex}")
            if id in self.dict_setting_object.keys():
                setting_object = self.dict_setting_object[id]
                setting_object.period_lineedit_obj.setText(str(setting.period))
                setting_object.checkbox_obj.setChecked(setting.visible)
                setting_object.line_width_lineedit_obj.setText(str(setting.line_width))
                setting_object.color_obj.setStyleSheet(f"background-color: {setting.color_hex}; border: 1px solid gray; border-radius: 4px;")

    def init_connect(self):
        self.btn_color.clicked.connect(partial(self.slot_btn_color_clicked, 0))
        self.btn_color_1.clicked.connect(partial(self.slot_btn_color_clicked, 1))
        self.btn_color_2.clicked.connect(partial(self.slot_btn_color_clicked, 2))
        

        self.btn_reset.clicked.connect(self.slot_btn_reset_clicked)
        self.btn_apply.clicked.connect(self.slot_btn_apply_clicked)

    def update_button_color(self, button_id):
        """更新按钮的背景颜色"""
        if button_id in self.dict_setting_object.keys() and button_id in self.dict_setting_user.keys():
            setting_object = self.dict_setting_object[button_id]
            setting_object.color_obj.setStyleSheet(f"background-color: {self.dict_setting_user[button_id].color_hex}; border: 1px solid gray; border-radius: 4px;")

    def get_button_background_color(self, button):
        """获取按钮的背景颜色，返回QColor对象"""
        # 首先尝试从属性中获取
        color = button.property("bg_color")
        if color:
            return QColor(color)
        
        # 如果属性中没有，则从样式表解析
        import re
        style_sheet = button.styleSheet()
        match = re.search(r'background-color:\s*([^;]+)', style_sheet)
        if match:
            color_str = match.group(1).strip()
            return QColor(color_str)
        
        # 如果无法解析颜色，返回无效的QColor对象
        return QColor()

    def slot_btn_color_clicked(self, id):
        self.logger.info(f"点击了按钮 {id}")
        self.logger.info(f"self.dict_setting_object.keys(): {self.dict_setting_object.keys()}")
        if id not in self.dict_setting_object.keys(): 
            return

        # 检查配置是否存在
        if id not in self.dict_setting_user:
            self.logger.warning(f"ID {id} 在配置中不存在")
            return

        # 弹出颜色选择对话框
        current_color_hex = self.dict_setting_user[id].color_hex
        # 将十六进制字符串转换为 QColor 对象
        current_color = QColor(current_color_hex)
        color = QColorDialog.getColor(current_color, self, f"选择颜色 {id + 1}")

        if color.isValid():
            # 更新颜色存储
            color_name = color.name()
            self.logger.info(f"color_name: {color_name}")
            self.dict_setting_user[id].set_color_hex(color_name)
            # 更新按钮显示颜色
            self.update_button_color(id)

    def slot_btn_reset_clicked(self):
        get_indicator_config_manager().reset_to_defaults(self.indicator_type)
        get_indicator_config_manager().save_user_config()

        self.dict_setting_user = get_indicator_config_manager().get_user_config_by_indicator_type(self.indicator_type)
        self.init_ui()

    def slot_btn_apply_clicked(self):
        for id, setting_object in self.dict_setting_object.items():
            if id in self.dict_setting_user.keys():
                self.dict_setting_user[id].period = int(setting_object.period_lineedit_obj.text())
                self.dict_setting_user[id].name  = f'{self.indicator_type}{self.dict_setting_user[id].period}'
                self.dict_setting_user[id].visible = setting_object.checkbox_obj.isChecked()
                self.dict_setting_user[id].line_width = int(setting_object.line_width_lineedit_obj.text())
                self.dict_setting_user[id].set_color_hex(self.get_button_background_color(setting_object.color_obj).name())

        get_indicator_config_manager().save_user_config()
        self.accept()