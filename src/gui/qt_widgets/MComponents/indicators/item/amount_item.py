import pyqtgraph as pg
from PyQt5 import QtGui, QtCore
import numpy as np

from manager.indicators_config_manager import *

class AmountItem(pg.GraphicsObject):
    # …"交易量柱状图绘制类……
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)

        # 数据验证
        required_columns = ['open', 'close', 'amount'] # , 'low', 'ma5', 'ma10', 'ma20', 'ma24', 'ma30', 'ma52', 'ma60'
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"缺少必要的数据列，需要: {required_columns}")
        
        self.data = data
        self.generatePicture()

    def get_data(self):
        return self.data
    
    def update_data(self, data):
        # 数据验证
        required_columns = ['open', 'close', 'amount'] 
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"缺少必要的数据列，需要: {required_columns}")

        self.data = data
        self.generatePicture()
        self.prepareGeometryChange()  # 通知框架几何形状可能发生了变化
        self.update()  # 触发重绘

    def generatePicture(self):
        # …生成交易量柱状图?…
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        pg.setConfigOptions(leftButtonPan=False, antialias=False)
        w = 0.25

        for i in range(len(self.data['amount'])):
            open_price = self.data['open'][i]
            close_price = self.data['close'][i]
            amount = self.data['amount'][i]  / 100000000    # 单位：亿
            
            if close_price < open_price:
                #下跌－ 绿色填充
                p.setPen(pg.mkPen(dict_kline_color[IndicatrosEnum.KLINE_DESC.value]))
                p.drawRect(QtCore.QRectF(i - w, 0, w * 2, amount))
                p.setBrush(pg.mkBrush(dict_kline_color[IndicatrosEnum.KLINE_DESC.value]))
            else:
                #上涨－ 红色空心
                p.setPen(pg.mkPen(dict_kline_color[IndicatrosEnum.KLINE_ASC.value]))
                p.drawLines(
                    QtCore.QLineF(QtCore.QPointF(i - w, 0), QtCore.QPointF(i - w, amount)),
                    QtCore.QLineF(QtCore.QPointF(i - w, amount), QtCore.QPointF(i + w, amount)),
                    QtCore.QLineF(QtCore.QPointF(i + w, amount), QtCore.QPointF(i + w, 0)),
                    QtCore.QLineF(QtCore.QPointF(i + w, 0), QtCore.QPointF(i - w, 0))
                )
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())