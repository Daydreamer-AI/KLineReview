# file: gui/qt_widgets/MComponents/macd_item.py
import pyqtgraph as pg
from PyQt5 import QtGui, QtCore
import numpy as np

from manager.indicators_config_manager import *

class MACDItem(pg.GraphicsObject):
    """MACD指标绘制类"""
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)

        # 数据验证
        required_columns = [IndicatrosEnum.MACD_DIFF.value, IndicatrosEnum.MACD_DEA.value, IndicatrosEnum.MACD.value]
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"缺少必要的数据列，需要: {required_columns}")
        
        self.data = data
        self.generatePicture()

    def get_data(self):
        return self.data
    
    def update_data(self, data):
        # 数据验证
        required_columns = [IndicatrosEnum.MACD_DIFF.value, IndicatrosEnum.MACD_DEA.value, IndicatrosEnum.MACD.value]
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"缺少必要的数据列，需要: {required_columns}")

        self.data = data
        self.generatePicture()
        self.prepareGeometryChange()  # 通知框架几何形状可能发生了变化
        self.update()  # 触发重绘

    def generatePicture(self):
        """生成MACD图"""
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        pg.setConfigOptions(leftButtonPan=False, antialias=False)
        w = 0.3

        # 绘制MACD柱状图
        for i in range(len(self.data)):
            macd_value = self.data[IndicatrosEnum.MACD.value].iloc[i]
            
            if not np.isnan(macd_value):
                if macd_value >= 0:
                    # 正数 - 红色
                    p.setPen(pg.mkPen(dict_kline_color[IndicatrosEnum.KLINE_ASC.value]))
                    p.setBrush(pg.mkBrush(dict_kline_color[IndicatrosEnum.KLINE_ASC.value]))
                else:
                    # 负数 - 绿色
                    p.setPen(pg.mkPen(dict_kline_color[IndicatrosEnum.KLINE_DESC.value]))
                    p.setBrush(pg.mkBrush(dict_kline_color[IndicatrosEnum.KLINE_DESC.value]))
                
                # 绘制柱状图
                p.drawRect(QtCore.QRectF(i - w, 0, w * 2, macd_value))

        dict_settings = get_indicator_config_manager().get_user_config_by_indicator_type(IndicatrosEnum.MACD.value)
        if dict_settings is None or len(dict_settings) < 2:
            dict_settings = get_indicator_config_manager().get_default_config_by_indicator_type(IndicatrosEnum.MACD.value)

        # 绘制DIFF线 (MACD线)
        if dict_settings[0].visible:
            diff_points = []
            for i in range(len(self.data)):
                diff_value = self.data[dict_settings[0].name].iloc[i]
                if not np.isnan(diff_value):
                    diff_points.append(QtCore.QPointF(i, diff_value))
            
            if len(diff_points) > 1:
                p.setPen(pg.mkPen(dict_settings[0].color_hex, width=dict_settings[0].line_width))
                for i in range(len(diff_points) - 1):
                    p.drawLine(diff_points[i], diff_points[i + 1])

        # 绘制DEA线 (信号线)
        if dict_settings[1].visible:
            dea_points = []
            for i in range(len(self.data)):
                dea_value = self.data[dict_settings[1].name].iloc[i]
                if not np.isnan(dea_value):
                    dea_points.append(QtCore.QPointF(i, dea_value))
            
            if len(dea_points) > 1:
                p.setPen(pg.mkPen(dict_settings[1].color_hex, width=dict_settings[1].line_width))
                for i in range(len(dea_points) - 1):
                    p.drawLine(dea_points[i], dea_points[i + 1])

        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())