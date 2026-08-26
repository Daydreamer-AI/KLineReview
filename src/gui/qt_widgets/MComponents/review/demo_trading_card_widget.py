from PyQt5 import uic
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal, Qt

from pathlib import Path

class DemoTradingCardWidget(QWidget):
    # 定义自定义信号
    clicked = pyqtSignal(object)  # 点击信号
    hovered = pyqtSignal()  # 悬浮进入信号
    hoverLeft = pyqtSignal()  # 悬浮离开信号
    doubleClicked = pyqtSignal()  # 双击信号

    def __init__(self, parent=None):
        super(DemoTradingCardWidget, self).__init__(parent)

        ui_file = Path(__file__).parent / "DemoTradingCardWidget.ui"
        
        # 检查文件是否存在
        if not ui_file.exists():
            raise FileNotFoundError(
                f"找不到UI文件: {ui_file.absolute()}\n"
                f"当前工作目录: {Path.cwd()}"
            )
        
        uic.loadUi(str(ui_file), self)

        self.init_para()
        self.init_ui()
        self.init_connect()

    def init_para(self):
        self._is_hovered = False  # 跟踪悬浮状态
        self.data = None

    def init_ui(self):
        pass

    def init_connect(self):
        pass

    def set_data(self, data):
        self.data = data

    def update_ui(self):
        status = self.data.status
        self.label_trading_yield.setText("--")
        if status == 1:
            self.label_name.setText(self.data.name)
            self.label_code.setText(self.data.code)
        elif status >= 2:
            self.label_trading_yield.setText(f"{self.data.trading_yield * 100:.2f}%")

            if self.data.trading_yield > 0:
                self.label_trading_yield.setStyleSheet("color: #E5403C;")
            elif self.data.trading_yield < 0:
                self.label_trading_yield.setStyleSheet("color: #1BCB34;")
            else:
                self.label_trading_yield.setStyleSheet("color: black;")

        self.label_status.setText(self.data.get_status_text())


    def mousePressEvent(self, event):
        """重写鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.data)  # 发射点击信号
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """重写鼠标释放事件（可选）"""
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """重写鼠标双击事件"""
        if event.button() == Qt.LeftButton:
            self.doubleClicked.emit()  # 发射双击信号
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event):
        """重写鼠标进入事件（悬浮开始）"""
        self._is_hovered = True
        self.hovered.emit()  # 发射悬浮信号
        self.update()  # 触发重绘
        super().enterEvent(event)

    def leaveEvent(self, event):
        """重写鼠标离开事件（悬浮结束）"""
        self._is_hovered = False
        self.hoverLeft.emit()  # 发射悬浮离开信号
        self.update()  # 触发重绘
        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        """重写鼠标移动事件（需要启用mouseTracking）"""
        # 可以在这里处理鼠标在控件内移动的逻辑
        super().mouseMoveEvent(event)


    def slot_trading_status_changed(self, status):
        if status == 0 or status == 6:
            return
        
        self.update_ui()
