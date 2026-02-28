# file: gui/qt_widgets/MComponents/boll_item.py
import pyqtgraph as pg
from PyQt5 import QtGui, QtCore
import numpy as np

from manager.indicators_config_manager import *

class BOLLItem(pg.GraphicsObject):
    """BOLL指标绘制类"""
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)

        # 数据验证
        required_columns = get_indicator_config_manager().get_user_config_columns_by_indicator_type(IndicatrosEnum.BOLL.value)
        required_columns.append('close')
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"缺少必要的数据列，需要: {required_columns}")
        
        self.data = data
        self.generatePicture()

    def get_data(self):
        return self.data
    
    def update_data(self, data):
        # 数据验证
        required_columns = get_indicator_config_manager().get_user_config_columns_by_indicator_type(IndicatrosEnum.BOLL.value)
        required_columns.append('close')
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"缺少必要的数据列，需要: {required_columns}")

        self.data = data
        self.generatePicture()
        self.prepareGeometryChange()  # 通知框架几何形状可能发生了变化
        self.update()  # 触发重绘

    def generatePicture(self):
        """生成BOLL图"""
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        pg.setConfigOptions(leftButtonPan=False, antialias=False)

        # 绘制收盘价线
        close_points = []
        for i in range(len(self.data)):
            close_value = self.data['close'].iloc[i]
            if not np.isnan(close_value):
                close_points.append(QtCore.QPointF(i, close_value))
        
        if len(close_points) > 1:
            p.setPen(pg.mkPen(dict_boll_color[IndicatrosEnum.BOLL_CLOSE.value], width=2))
            for i in range(len(close_points) - 1):
                p.drawLine(close_points[i], close_points[i + 1])


        dict_settings = get_indicator_config_manager().get_user_config_by_indicator_type(IndicatrosEnum.BOLL.value)
        if dict_settings is None or len(dict_settings) != 3:
            dict_settings = get_indicator_config_manager().get_default_config_by_indicator_type(IndicatrosEnum.BOLL.value)

        # 绘制中轨线
        if dict_settings[0].visible:
            mb_points = []
            for i in range(len(self.data)):
                mb_value = self.data[dict_settings[0].name].iloc[i]
                if not np.isnan(mb_value):
                    mb_points.append(QtCore.QPointF(i, mb_value))
            
            if len(mb_points) > 1:
                p.setPen(pg.mkPen(dict_settings[0].color_hex, width=dict_settings[0].line_width))
                for i in range(len(mb_points) - 1):
                    p.drawLine(mb_points[i], mb_points[i + 1])

        # 绘制上轨线
        if dict_settings[1].visible:
            up_points = []
            for i in range(len(self.data)):
                up_value = self.data[dict_settings[1].name].iloc[i]
                if not np.isnan(up_value):
                    up_points.append(QtCore.QPointF(i, up_value))
            
            if len(up_points) > 1:
                p.setPen(pg.mkPen(dict_settings[1].color_hex, width=dict_settings[1].line_width))
                for i in range(len(up_points) - 1):
                    p.drawLine(up_points[i], up_points[i + 1])

        # 绘制下轨线
        if dict_settings[2].visible:
            dn_points = []
            for i in range(len(self.data)):
                dn_value = self.data[dict_settings[2].name].iloc[i]
                if not np.isnan(dn_value):
                    dn_points.append(QtCore.QPointF(i, dn_value))
            
            if len(dn_points) > 1:
                p.setPen(pg.mkPen(dict_settings[2].color_hex, width=dict_settings[2].line_width))
                for i in range(len(dn_points) - 1):
                    p.drawLine(dn_points[i], dn_points[i + 1])

        # 绘制布林带填充区域（上轨和下轨之间）
        if dict_settings[1].visible and dict_settings[2].visible:
            if len(up_points) > 1 and len(dn_points) > 1:
                p.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                p.setBrush(QtGui.QBrush(QtGui.QColor(255, 61, 61, 30)))  # 半透明红色
                
                # 创建填充区域的点
                fill_points = up_points + dn_points[::-1]  # 上轨点 + 反转的下轨点
                if len(fill_points) > 2:
                    polygon = QtGui.QPolygonF(fill_points)
                    p.drawPolygon(polygon)

        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())