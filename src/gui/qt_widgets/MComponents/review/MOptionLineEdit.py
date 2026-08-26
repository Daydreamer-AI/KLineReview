# gui/qt_widgets/MComponents/MOptionLineEdit.py

from PyQt5.QtWidgets import QLineEdit, QListWidget, QWidget
from PyQt5.QtCore import pyqtSignal, QTimer, Qt
import logging

class MOptionLineEdit(QLineEdit):
    """
    带有选项列表的LineEdit控件
    """
    # 自定义信号
    optionSelected = pyqtSignal(str)  # 当选项被选中时发出信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # 初始化选项列表
        self.options_list_widget = QListWidget()
        # 使用更可靠的父窗口设置方式
        if parent:
            self.options_list_widget.setParent(parent)
            self.options_list_widget.setWindowFlags(Qt.Widget)
        else:
            # 如果没有父窗口，将其设为弹出窗口
            self.options_list_widget.setWindowFlags(Qt.Popup)
        self.options_list_widget.hide()
        self.options_list_widget.setMinimumSize(300, 150)
        
        # 数据属性
        self.all_options = []
        self.filtered_options = []
        
        # 连接信号
        self.textChanged.connect(self.on_text_changed)
        self.options_list_widget.itemClicked.connect(self.on_option_selected)
        self.editingFinished.connect(self.hide_options_list)
        
        # 安装事件过滤器
        self.installEventFilter(self)
        self.options_list_widget.installEventFilter(self)
        
    def set_options(self, options):
        """
        设置所有选项
        :param options: 选项列表
        """
        self.all_options = list(options) if options else []
        self.filtered_options = self.all_options[:]
        
    def on_text_changed(self, text):
        """
        处理文本变化
        """
        try:
            self.logger.debug(f"输入的搜索值为：{text}")
        except:
            pass  # 忽略日志初始化问题
            
        if not text:
            # 显示所有选项
            self.filtered_options = self.all_options[:]
        else:
            # 根据输入过滤选项
            self.filtered_options = [option for option in self.all_options 
                                   if text.lower() in option.lower()]
        
        # 更新选项列表显示
        self.update_options_list()
        
        # 动态定位和显示控制
        if self.filtered_options:
            self.position_options_list()
            self.options_list_widget.show()
        elif text:  # 如果有输入文本但没有匹配项，则隐藏
            self.options_list_widget.hide()
            
    def update_options_list(self):
        """
        更新选项列表显示
        """
        # 清空现有选项
        self.options_list_widget.clear()
        
        # 添加过滤后的选项
        for option in self.filtered_options:
            self.options_list_widget.addItem(option)
            
    def position_options_list(self):
        """
        动态计算并设置选项列表的位置，确保其在输入框下方且不被遮挡
        """
        # 更可靠地获取父窗口
        if not self.parent() and not self.window():
            return
            
        # 计算相对于主窗口的位置
        global_pos = self.mapToGlobal(self.rect().bottomLeft())
        
        if self.parent():
            # 如果有父窗口，转换为父窗口坐标系
            parent_global_pos = self.parent().mapToGlobal(self.parent().rect().topLeft())
            relative_pos = global_pos - parent_global_pos
            self.options_list_widget.move(relative_pos.x(), relative_pos.y())
        else:
            # 否则使用全局坐标
            self.options_list_widget.move(global_pos)
        
        # 设置宽度与输入框一致
        self.options_list_widget.setFixedWidth(self.width())
        
        # 确保选项列表在最上层
        self.options_list_widget.raise_()
        
        # 设置合适的z值，确保在最前面
        # self.options_list_widget.setZValue(1000)
        self.options_list_widget.activateWindow()
        
    def on_option_selected(self, item):
        """
        处理选项被点击
        """
        selected_text = item.text()
        try:
            self.logger.debug(f"选中的选项为：{selected_text}")
        except:
            pass  # 忽略日志初始化问题
        
        # 发出信号
        self.optionSelected.emit(selected_text)
        
        # 阻止在设置文本时触发on_text_changed
        self.blockSignals(True)
        
        # 设置文本并隐藏选项列表
        self.setText("")
        self.options_list_widget.hide()
        
        # 恢复信号
        self.blockSignals(False)
        
        # 最后清除焦点
        self.clearFocus()
        
    def hide_options_list(self):
        """
        隐藏选项列表
        """
        # 使用定时器延迟隐藏，以便处理点击事件
        QTimer.singleShot(100, lambda: self.options_list_widget.hide() if self.options_list_widget else None)
        
    def eventFilter(self, obj, event):
        """
        事件过滤器
        """
        if obj == self:
            if event.type() == event.FocusIn:
                # 当输入框获得焦点时
                self.on_focus_in()
            elif event.type() == event.FocusOut:
                # 当输入框失去焦点时
                QTimer.singleShot(150, self.check_focus_and_hide)
        elif obj == self.options_list_widget:
            if event.type() == event.FocusOut:
                # 当选项列表失去焦点时
                QTimer.singleShot(100, self.check_focus_and_hide)
                
        return super().eventFilter(obj, event)
        
    def on_focus_in(self):
        """
        当输入框获得焦点时的处理
        """
        current_text = self.text()
        if current_text:
            # 如果有文本，重新显示匹配的选项
            self.on_text_changed(current_text)
        else:
            # 如果没有文本，显示所有选项
            self.filtered_options = self.all_options[:]
            self.update_options_list()
            if self.filtered_options:
                self.position_options_list()
                self.options_list_widget.show()
                
    def check_focus_and_hide(self):
        """
        检查焦点状态并决定是否隐藏选项列表
        """
        # 如果输入框和选项列表都不拥有焦点，则隐藏选项列表
        try:
            if not (self.hasFocus() or (self.options_list_widget and self.options_list_widget.hasFocus())):
                if self.options_list_widget:
                    self.options_list_widget.hide()
        except RuntimeError:
            # 处理对象已被删除的情况
            pass
            
    def show_options(self):
        """
        显示选项列表
        """
        if self.filtered_options:
            self.position_options_list()
            self.options_list_widget.show()
            
    def hide_options(self):
        """
        隐藏选项列表
        """
        if self.options_list_widget:
            self.options_list_widget.hide()
        
    def get_selected_option(self):
        """
        获取当前选中的选项
        """
        return self.text()
        
    def clear_selection(self):
        """
        清除选择
        """
        self.clear()
        if self.options_list_widget:
            self.options_list_widget.hide()
        
    def resizeEvent(self, event):
        """
        处理大小变化事件
        """
        super().resizeEvent(event)
        # 当输入框大小变化时，重新定位选项列表
        if self.options_list_widget and self.options_list_widget.isVisible():
            self.position_options_list()