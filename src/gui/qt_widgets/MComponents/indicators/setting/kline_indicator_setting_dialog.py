from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QButtonGroup, QColorDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
from functools import partial

from manager.logging_manager import get_logger
from manager.indicators_config_manager import *

class MASettingObject(object):
    def __init__(self, id=0, period_lineedit_obj=None, checkbox_obj=None, line_width_lineedit_obj=None, color_obj=None):
        self.id = id
        self.period_lineedit_obj = period_lineedit_obj
        self.checkbox_obj = checkbox_obj
        self.line_width_lineedit_obj = line_width_lineedit_obj
        self.color_obj = color_obj

class KLineIndicatorSettingDialog(QDialog):
    def __init__(self, parent=None):
        super(KLineIndicatorSettingDialog, self).__init__(parent)
        uic.loadUi('./src/gui/qt_widgets/MComponents/indicators/setting/KLineIndicatorSettingDialog.ui', self)

        self.init_para()
        self.init_ui()
        self.init_connect()

    def init_para(self):
        self.logger = get_logger(__name__)

        # 获取完整的用户配置
        all_user_configs = get_indicator_config_manager().get_user_configs()
        
        # 提取MA配置
        self.dict_ma_setting_user = all_user_configs.get(IndicatrosEnum.MA.value, {})

        self.dict_ma_setting_object = {
            0: MASettingObject(0, self.lineEdit_ma_period, self.checkBox_ma, self.lineEdit_line_width, self.btn_color),
            1: MASettingObject(1, self.lineEdit_ma_period_1, self.checkBox_ma_1, self.lineEdit_line_width_1, self.btn_color_1),
            2: MASettingObject(2, self.lineEdit_ma_period_2, self.checkBox_ma_2, self.lineEdit_line_width_2, self.btn_color_2),
            3: MASettingObject(3, self.lineEdit_ma_period_3, self.checkBox_ma_3, self.lineEdit_line_width_3, self.btn_color_3),
            4: MASettingObject(4, self.lineEdit_ma_period_4, self.checkBox_ma_4, self.lineEdit_line_width_4, self.btn_color_4),
            5: MASettingObject(5, self.lineEdit_ma_period_5, self.checkBox_ma_5, self.lineEdit_line_width_5, self.btn_color_5),
            6: MASettingObject(6, self.lineEdit_ma_period_6, self.checkBox_ma_6, self.lineEdit_line_width_6, self.btn_color_6)
        }

    def init_ui(self):
        self.frame_indicators.hide()
        self.btn_scheme_1.hide()
        self.btn_scheme_2.hide()

        self.scheme_button_group = QButtonGroup(self)
        self.scheme_button_group.addButton(self.btn_scheme, 0)
        self.scheme_button_group.addButton(self.btn_scheme_1, 1)
        self.scheme_button_group.addButton(self.btn_scheme_2, 2)

        # self.period_color_button_group = QButtonGroup(self)
        # self.period_color_button_group.addButton(self.btn_color, 0)
        # self.period_color_button_group.addButton(self.btn_color_1, 1)
        # self.period_color_button_group.addButton(self.btn_color_2, 2)
        # self.period_color_button_group.addButton(self.btn_color_3, 3)
        # self.period_color_button_group.addButton(self.btn_color_4, 4)
        # self.period_color_button_group.addButton(self.btn_color_5, 5)
        # self.period_color_button_group.addButton(self.btn_color_6, 6)

        # 遍历MA配置并设置UI
        for id, ma_setting in self.dict_ma_setting_user.items():
            # self.logger.info(f"ma_setting--id: {ma_setting.id}, period: {ma_setting.period}, name: {ma_setting.name}, visible: {ma_setting.visible}, line_width: {ma_setting.line_width}, color: {ma_setting.color}, color_hex: {ma_setting.color_hex}")
            if id in self.dict_ma_setting_object.keys():
                ma_setting_object = self.dict_ma_setting_object[id]
                ma_setting_object.period_lineedit_obj.setText(str(ma_setting.period))
                ma_setting_object.checkbox_obj.setChecked(ma_setting.visible)
                ma_setting_object.line_width_lineedit_obj.setText(str(ma_setting.line_width))
                ma_setting_object.color_obj.setStyleSheet(f"background-color: {ma_setting.color_hex}; border: 1px solid gray; border-radius: 4px;")

    def init_connect(self):
        self.scheme_button_group.buttonClicked.connect(self.slot_scheme_button_group_buttonClicked)
        # self.period_color_button_group.buttonClicked.connect(self.slot_period_color_button_group_buttonClicked)

        self.btn_color.clicked.connect(partial(self.slot_btn_color_clicked, 0))
        self.btn_color_1.clicked.connect(partial(self.slot_btn_color_clicked, 1))
        self.btn_color_2.clicked.connect(partial(self.slot_btn_color_clicked, 2))
        self.btn_color_3.clicked.connect(partial(self.slot_btn_color_clicked, 3))
        self.btn_color_4.clicked.connect(partial(self.slot_btn_color_clicked, 4))
        self.btn_color_5.clicked.connect(partial(self.slot_btn_color_clicked, 5))
        self.btn_color_6.clicked.connect(partial(self.slot_btn_color_clicked, 6))
        

        self.btn_reset.clicked.connect(self.slot_btn_reset_clicked)
        self.btn_apply.clicked.connect(self.slot_btn_apply_clicked)


    def update_button_color(self, button_id):
        """更新按钮的背景颜色"""
        if button_id in self.dict_ma_setting_object.keys() and button_id in self.dict_ma_setting_user.keys():
            ma_setting_object = self.dict_ma_setting_object[button_id]
            ma_setting_object.color_obj.setStyleSheet(f"background-color: {self.dict_ma_setting_user[button_id].color_hex}; border: 1px solid gray; border-radius: 4px;")

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

    def slot_scheme_button_group_buttonClicked(self, btn):
        checked_id = self.scheme_button_group.checkedId()
        # self.period_color_button_group.button(checked_id).setChecked(True)
        # self.period_color_button_group.button(checked_id).click()


    # def slot_period_color_button_group_buttonClicked(self, btn):
    #     checked_id = self.period_color_button_group.checkedId()
    #     self.logger.info(f"点击了按钮 {checked_id}")
    #     self.logger.info(f"self.dict_ma_setting_object.keys(): {self.dict_ma_setting_object.keys()}")
    #     if checked_id not in self.dict_ma_setting_object.keys(): 
    #         return

    #     # 弹出颜色选择对话框
    #     current_color = self.dict_ma_setting_user[checked_id].color_hex
    #     color = QColorDialog.getColor(current_color, self, f"选择颜色 {checked_id + 1}")

    #     if color.isValid():
    #         # 更新颜色存储
    #         self.dict_ma_setting_user[checked_id].set_color_hex(color.name())
    #         # 更新按钮显示颜色
    #         self.update_button_color(checked_id)

    def slot_btn_color_clicked(self, id):
        self.logger.info(f"点击了按钮 {id}")
        self.logger.info(f"self.dict_ma_setting_object.keys(): {self.dict_ma_setting_object.keys()}")
        if id not in self.dict_ma_setting_object.keys(): 
            return

        # 检查配置是否存在
        if id not in self.dict_ma_setting_user:
            self.logger.warning(f"ID {id} 在配置中不存在")
            return

        # 弹出颜色选择对话框
        current_color_hex = self.dict_ma_setting_user[id].color_hex
        # 将十六进制字符串转换为 QColor 对象
        current_color = QColor(current_color_hex)
        color = QColorDialog.getColor(current_color, self, f"选择颜色 {id + 1}")

        if color.isValid():
            # 更新颜色存储
            color_name = color.name()
            self.logger.info(f"color_name: {color_name}")
            self.dict_ma_setting_user[id].set_color_hex(color_name)
            # 更新按钮显示颜色
            self.update_button_color(id)

    def slot_btn_reset_clicked(self):
        get_indicator_config_manager().reset_to_defaults(IndicatrosEnum.MA.value)
        get_indicator_config_manager().save_user_config()

        self.dict_ma_setting_user = get_indicator_config_manager().get_user_config_by_indicator_type(IndicatrosEnum.MA.value)
        self.init_ui()

    def slot_btn_apply_clicked(self):
        for id, ma_setting_object in self.dict_ma_setting_object.items():
            if id in self.dict_ma_setting_user.keys():
                self.dict_ma_setting_user[id].period = int(ma_setting_object.period_lineedit_obj.text())
                self.dict_ma_setting_user[id].name  = f'{IndicatrosEnum.MA.value}{self.dict_ma_setting_user[id].period}'
                self.dict_ma_setting_user[id].visible = ma_setting_object.checkbox_obj.isChecked()
                self.dict_ma_setting_user[id].line_width = int(ma_setting_object.line_width_lineedit_obj.text())
                self.dict_ma_setting_user[id].set_color_hex(self.get_button_background_color(ma_setting_object.color_obj).name())

        get_indicator_config_manager().save_user_config()
        self.accept()
