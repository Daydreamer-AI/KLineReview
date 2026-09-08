from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal, Qt

import os
from pathlib import Path
import pandas as pd

class StockCardWidget(QWidget):

    # 定义自定义信号
    clicked = pyqtSignal(object)  # 点击信号
    hovered = pyqtSignal()  # 悬浮进入信号
    hoverLeft = pyqtSignal()  # 悬浮离开信号
    doubleClicked = pyqtSignal()  # 双击信号

    def __init__(self, type=0):
        super().__init__()
        # uic.loadUi('.gui/qt_widgets/MComponents/StockCardWidget.ui', self)
        # 使用 pathlib 确保跨平台兼容性
        ui_file = Path(__file__).parent / "StockCardWidget.ui"
        
        # 检查文件是否存在
        if not ui_file.exists():
            raise FileNotFoundError(
                f"找不到UI文件: {ui_file.absolute()}\n"
                f"当前工作目录: {Path.cwd()}"
            )
        
        uic.loadUi(str(ui_file), self)

        self.board_type = type  # 0: 行业板块，1: 概念板块，2：个股
        
        self.init_para()
        self.init_ui()
        self.init_connect()

    def init_para(self):
        self._is_hovered = False  # 跟踪悬浮状态

    def init_ui(self):
        # 启用鼠标跟踪以检测悬浮事件
        self.setMouseTracking(True)
        # 设置焦点策略以便接收键盘事件（可选）
        self.setFocusPolicy(Qt.StrongFocus)

    def init_connect(self):
        pass

    def _get_data_attr(self, attr_name, default=None):
        """安全获取数据属性的辅助函数"""
        if self.data is None:
            return default
        
        if hasattr(self.data, 'get'):  # pandas Series
            return self.data.get(attr_name, default)
        else:  # NamedTuple 或其他对象
            return getattr(self.data, attr_name, default)

    def update_ui(self):
        if self.data is not None:
            if self.board_type == 2:
                # 个股，data: pandas Series
                # self.label_stock_name.hide()
                code = self._get_data_attr('code')
                name = self._get_data_attr('name')
                close = self._get_data_attr('close')
                
                if code is not None:
                    self.label_stock_code.setText(str(code))

                if name is not None:
                    self.label_stock_name.setText(str(name))

                if close is not None:
                    self.label_price.setText(str(close))

            else:
                # data: namedtuple
                self.label_stock_code.hide()
                if self.board_type == 0:
                    industry_name = self._get_data_attr('industry_name')
                    if industry_name is not None:
                        self.label_stock_name.setText(str(industry_name))
                    
                    # 设置均价，保留2位小数
                    avg_price = self._get_data_attr('avg_price')
                    if avg_price is not None and not (isinstance(avg_price, float) and pd.isna(avg_price)):
                        self.label_price.setText(f"{float(avg_price):.2f}")
                    else:
                        self.label_price.setText("N/A")
                else:
                    concept_name = self._get_data_attr('concept_name')
                    if concept_name is not None:
                        self.label_stock_name.setText(str(concept_name))
                    # self.label_price.setText("N/A")
                    # self.label_price.hide()
                    open_price = self._get_data_attr('open_price')
                    if open_price is not None and not (isinstance(open_price, float) and pd.isna(open_price)):
                        self.label_price.setText(f"{float(open_price):.2f}")
                    else:
                        self.label_price.setText("N/A")

            # 设置涨跌幅，保留2位小数并添加百分号
            change_percent = self._get_data_attr('change_percent')
            if change_percent is not None and not (isinstance(change_percent, float) and pd.isna(change_percent)):
                # print(f"""change_percent type: {type(change_percent)}""") # <class 'numpy.float64'>
                float_change_percent = float(change_percent)
                # print(f"""change_percent: {float_change_percent}""")
                self.label_change_percent.setText(f"{float_change_percent:.2f}%")

                # 根据价格变化设置属性
                if float_change_percent > 0:
                    self.label_price.setProperty("change_status", "up")
                    self.label_change_percent.setProperty("change_status", "up")
                elif float_change_percent < 0:
                    # print(f"change_percent: {float_change_percent}")
                    self.label_price.setProperty("change_status", "down")
                    self.label_change_percent.setProperty("change_status", "down")
                elif float_change_percent == 0:
                    self.label_price.setProperty("change_status", "flat")
                    self.label_change_percent.setProperty("change_status", "flat")

                # 重新应用样式
                self.label_price.style().unpolish(self.label_price)
                self.label_price.style().polish(self.label_price)
                self.label_change_percent.style().unpolish(self.label_change_percent)
                self.label_change_percent.style().polish(self.label_change_percent)
                
            else:
                self.label_change_percent.setText("N/A")


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


    def set_data(self, data):
        self.data = data