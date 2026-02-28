import PyQt5.QtGui as QtGui
from PyQt5.QtGui import QValidator

class MRangeValidator(QtGui.QValidator):
    def __init__(self, min_value, max_value, parent=None):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, input_str, pos):
        # 空字符串允许（用户可能正在输入）
        if not input_str:
            return QValidator.Intermediate, input_str, pos
            
        # 检查是否为数字
        if not input_str.isdigit():
            return QValidator.Invalid, input_str, pos
            
        # 检查范围
        value = int(input_str)
        if self.min_value <= value <= self.max_value:
            return QValidator.Acceptable, input_str, pos
        elif value < self.min_value:
            return QValidator.Intermediate, input_str, pos
        else:  # value > max_value
            # 如果超过最大值，判断是否可以接受部分输入
            if str(self.max_value).startswith(input_str):
                return QValidator.Intermediate, input_str, pos
            else:
                return QValidator.Invalid, input_str, pos

    def fixup(self, input_str):
        """自动修正输入"""
        try:
            value = int(input_str)
            if value < self.min_value:
                return str(self.min_value)
            elif value > self.max_value:
                return str(self.max_value)
            return input_str
        except ValueError:
            return str(self.min_value)

# 使用方式
# def init_ui(self):
#     uic.loadUi('gui/qt_widgets/board/BoardOverViewWidget.ui', self)
    
#     # 使用自定义验证器
#     validator = RangeValidator(10, 30, self.lineEdit_top)
#     self.lineEdit_top.setValidator(validator)
#     self.lineEdit_top.setText('20')
    
    # ... 其他代码 ...