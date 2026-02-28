from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene
from PyQt5.QtCore import pyqtSlot, QRectF, Qt
from PyQt5.QtGui import QColor, QPen, QBrush, QPainter, QFont

import pyqtgraph as pg
import numpy as np

from manager.logging_manager import get_logger

class MPieChartItem(pg.GraphicsObject):
    """自定义饼图项"""
    def __init__(self, data, labels, parent=None):
        pg.GraphicsObject.__init__(self, parent)
        self.logger = get_logger(__name__)
        self.data = data
        self.labels = labels
        self.generate_picture()
    
    def generate_picture(self):
        """生成饼图"""
        self.picture = pg.QtGui.QPicture()
        painter = pg.QtGui.QPainter(self.picture)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 计算总量
        total = sum(self.data)
        if total == 0:
            return
            
        # 定义颜色
        colors = [
            QColor(255, 170, 170),  # 浅红
            QColor(170, 255, 170),  # 浅绿
            QColor(170, 170, 255),  # 浅蓝
            QColor(255, 255, 170),  # 浅黄
            QColor(255, 170, 255),  # 浅紫
            QColor(170, 255, 255),  # 浅青
            QColor(255, 210, 170),  # 浅橙
            QColor(210, 170, 255),  # 浅紫红
            QColor(170, 255, 210),  # 浅绿蓝
            QColor(255, 170, 210),  # 浅粉
            QColor(200, 200, 200)   # 灰色（其他）
        ]
        
        rect = QRectF(-100, -100, 200, 200)
        start_angle = 0
        
        for i, value in enumerate(self.data):
            span_angle = (value / total) * 360 * 16  # Qt角度单位是1/16度
            
            # 设置颜色和画笔
            color = colors[i % len(colors)] if i < 10 else QColor(200, 200, 200)
            painter.setBrush(QBrush(color))
            
            # 对前10名设置更粗的边框以突出显示
            pen_width = 2 if i < 10 else 1
            painter.setPen(QPen(Qt.black, pen_width))
            
            # 绘制扇形
            painter.drawPie(rect, int(start_angle), int(span_angle))
            
            start_angle += span_angle
        
        painter.end()
    
    def paint(self, painter, option, widget=None):
        painter.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        return QRectF(-110, -110, 220, 220)
    


class InteractiveMPieChartItem(MPieChartItem):
    """支持交互的饼图项"""
    
    def __init__(self, data, labels, parent=None):
        super().__init__(data, labels, parent)
        self.labels = labels
        self.data = data
        self.tooltip = None
        self.setup_interactive_features()
    
    def setup_interactive_features(self):
        """设置交互功能"""
        # 创建提示框
        self.tooltip = pg.TextItem("", anchor=(0.5, 0.5))
        self.tooltip.setZValue(10)
        self.tooltip.setVisible(False)
        
        # 连接事件
        self.mouseMoveEvent = self.on_mouse_move
        self.mouseLeaveEvent = self.on_mouse_leave
        
        # 设置鼠标样式
        self.setCursor(Qt.PointingHandCursor)
    
    def on_mouse_move(self, event):
        """处理鼠标移动"""
        # 获取鼠标位置
        pos = event.pos()
        self.logger.info(f"Mouse moved to ({pos.x()}, {pos.y()})")
        
        # 计算扇形索引
        sector_index = self.get_sector_at_position(pos)
        
        if sector_index >= 0 and sector_index < len(self.labels):
            label = self.labels[sector_index]
            value = self.data[sector_index]
            total = sum(self.data)
            percentage = (value / total) * 100
            
            # 显示提示
            text = f"{label}\n{value:,}亿\n{percentage:.1f}%"
            self.tooltip.setText(text)
            self.tooltip.setVisible(True)
            self.tooltip.setPos(pos.x(), pos.y() - 30)
        else:
            self.tooltip.setVisible(False)
    
    def on_mouse_leave(self, event):
        """处理鼠标离开"""
        if self.tooltip:
            self.tooltip.setVisible(False)
    
    def get_sector_at_position(self, pos):
        """根据位置获取扇形索引"""
        # 这里需要根据具体的饼图实现来计算
        # 示例实现：
        total = sum(self.data)
        if total == 0:
            return -1
            
        # 计算角度
        angle = np.arctan2(pos.y(), pos.x()) * 180 / np.pi
        
        # 找到对应的扇形
        current_angle = 0
        for i in range(len(self.data)):
            sector_angle = (self.data[i] / total) * 360
            if current_angle <= angle <= current_angle + sector_angle:
                return i
            current_angle += sector_angle
        
        return -1

# class InteractiveMPieChartItem(MPieChartItem):
#     """支持交互的饼图项"""
    
#     def __init__(self, data, labels, parent=None):
#         super().__init__(data, labels, parent)
#         self.labels = labels
#         self.data = data
#         self.tooltip = None
#         self.setup_interactive_features()
    
#     def setup_interactive_features(self):
#         """设置交互功能"""
#         # 创建提示框
#         self.tooltip = pg.TextItem("", anchor=(0.5, 0.5))
#         self.tooltip.setZValue(10)
#         self.tooltip.setVisible(False)
        
#         # 连接事件
#         self.mouseMoveEvent = self.on_mouse_move
#         self.mouseLeaveEvent = self.on_mouse_leave
        
#         # 设置鼠标样式
#         self.setCursor(Qt.PointingHandCursor)
    
#     def on_mouse_move(self, event):
#         """处理鼠标移动"""
#         # 获取鼠标位置
#         pos = event.pos()
        
#         # 计算扇形索引
#         sector_index = self.get_sector_at_position(pos)
        
#         if sector_index >= 0 and sector_index < len(self.labels):
#             label = self.labels[sector_index]
#             value = self.data[sector_index]
#             total = sum(self.data)
#             percentage = (value / total) * 100
            
#             # 显示提示
#             text = f"{label}\n{value:,}亿\n{percentage:.1f}%"
#             self.tooltip.setText(text)
#             self.tooltip.setVisible(True)
#             self.tooltip.setPos(pos.x(), pos.y() - 30)
#         else:
#             self.tooltip.setVisible(False)
    
#     def on_mouse_leave(self, event):
#         """处理鼠标离开"""
#         if self.tooltip:
#             self.tooltip.setVisible(False)
    
#     def get_sector_at_position(self, pos):
#         """根据位置获取扇形索引"""
#         # 这里需要根据具体的饼图实现来计算
#         # 示例实现：
#         total = sum(self.data)
#         if total == 0:
#             return -1
            
#         # 计算角度
#         angle = np.arctan2(pos.y(), pos.x()) * 180 / np.pi
        
#         # 找到对应的扇形
#         current_angle = 0
#         for i in range(len(self.data)):
#             sector_angle = (self.data[i] / total) * 360
#             if current_angle <= angle <= current_angle + sector_angle:
#                 return i
#             current_angle += sector_angle
        
#         return -1