# file: gui/qt_widgets/MComponents/rsi_item.py
import pyqtgraph as pg
from PyQt5 import QtGui, QtCore
import numpy as np

from manager.indicators_config_manager import *

class RSIItem(pg.GraphicsObject):
    """RSI指标绘制类"""
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)

        # 数据验证
        required_columns = []
        # 检查至少有一个RSI列存在
        rsi_columns = get_indicator_config_manager().get_user_config_columns_by_indicator_type(IndicatrosEnum.RSI.value)
        has_rsi = any(col in data.columns for col in rsi_columns)
        if not has_rsi:
            raise ValueError(f"缺少必要的RSI数据列，至少需要: {rsi_columns}")
        
        self.data = data
        self.generatePicture()

    def get_data(self):
        return self.data
    
    def update_data(self, data):
        # 数据验证
        required_columns = get_indicator_config_manager().get_user_config_columns_by_indicator_type(IndicatrosEnum.RSI.value)
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"缺少必要的数据列，需要: {required_columns}")

        self.data = data
        self.generatePicture()
        self.prepareGeometryChange()  # 通知框架几何形状可能发生了变化
        self.update()  # 触发重绘

    def generatePicture(self):
        """生成RSI图"""
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        pg.setConfigOptions(leftButtonPan=False, antialias=False)

        dict_settings = get_indicator_config_manager().get_user_config_by_indicator_type(IndicatrosEnum.RSI.value)
        if dict_settings is None or len(dict_settings) != 3:
            dict_settings = get_indicator_config_manager().get_default_config_by_indicator_type(IndicatrosEnum.RSI.value)

        # 绘制RSI6线
        if dict_settings[0].visible:
            if dict_settings[0].name in self.data.columns:
                rsi6_points = []
                for i in range(len(self.data)):
                    rsi6_value = self.data[dict_settings[0].name].iloc[i]
                    if not np.isnan(rsi6_value):
                        rsi6_points.append(QtCore.QPointF(i, rsi6_value))
                
                if len(rsi6_points) > 1:
                    p.setPen(pg.mkPen(dict_settings[0].color_hex, width=dict_settings[0].line_width))
                    for i in range(len(rsi6_points) - 1):
                        p.drawLine(rsi6_points[i], rsi6_points[i + 1])

        # 绘制RSI12线
        if dict_settings[1].visible:
            if dict_settings[1].name in self.data.columns:
                rsi12_points = []
                for i in range(len(self.data)):
                    rsi12_value = self.data[dict_settings[1].name].iloc[i]
                    if not np.isnan(rsi12_value):
                        rsi12_points.append(QtCore.QPointF(i, rsi12_value))
                
                if len(rsi12_points) > 1:
                    p.setPen(pg.mkPen(dict_settings[1].color_hex, width=dict_settings[1].line_width))
                    for i in range(len(rsi12_points) - 1):
                        p.drawLine(rsi12_points[i], rsi12_points[i + 1])

        # 绘制RSI24线
        if dict_settings[2].visible:
            if dict_settings[2].name in self.data.columns:
                rsi24_points = []
                for i in range(len(self.data)):
                    rsi24_value = self.data[dict_settings[2].name].iloc[i]
                    if not np.isnan(rsi24_value):
                        rsi24_points.append(QtCore.QPointF(i, rsi24_value))
                
                if len(rsi24_points) > 1:
                    p.setPen(pg.mkPen(dict_settings[2].color_hex, width=dict_settings[2].line_width))
                    for i in range(len(rsi24_points) - 1):
                        p.drawLine(rsi24_points[i], rsi24_points[i + 1])

        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())