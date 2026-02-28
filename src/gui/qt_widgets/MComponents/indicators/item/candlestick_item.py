import pyqtgraph as pg
from PyQt5 import QtGui, QtCore
import numpy as np

from manager.indicators_config_manager import get_kline_half_width, IndicatrosEnum, get_indicator_config_manager, get_dict_kline_color


class CandlestickItem(pg.GraphicsObject):
    # "."蜡烛图绘制类…·
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)

        # 数据验证
        required_columns = ['open', 'close', 'high', 'low'] # , 'ma5', 'ma10', 'ma20', 'ma24', 'ma30', 'ma52', 'ma60'
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"缺少必要的数据列，需要: {required_columns}")

        self.data = data            # data should be a list or Pandas.DataFrame (date, code, open, high, low, close...)
        self.ma_visible = True
        self.generatePicture()

    def get_data(self):
        return self.data
    
    def update_data(self, data):
        # 数据验证
        required_columns = ['open', 'close', 'high', 'low'] # , 'ma5', 'ma10', 'ma20', 'ma24', 'ma30', 'ma52', 'ma60'
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"缺少必要的数据列，需要: {required_columns}")

        self.data = data
        self.generatePicture()
        self.prepareGeometryChange()  # 通知框架几何形状可能发生了变化
        self.update()  # 触发重绘

    def is_ma_show(self):
        return self.ma_visible
    
    def show_ma(self, b_show=True):
        if self.ma_visible == b_show:
            return
        
        self.ma_visible = b_show
        self.generatePicture()
        self.prepareGeometryChange()
        self.update()

    def generatePicture(self):
        # 生成蜡烛图
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        pg.setConfigOptions(leftButtonPan=False, antialias=False)
        w = get_kline_half_width()

        # 长度检查
        if len(self.data) == 0:
            p.end()
            return

        #绘制移动平均线
        if self.ma_visible:
            all_user_configs = get_indicator_config_manager().get_user_configs()
            dict_ma_setting_user = all_user_configs.get(IndicatrosEnum.MA.value, {})

            for id, ma_setting in dict_ma_setting_user.items():
                if ma_setting.visible and ma_setting.name in self.data.columns and len(self.data) > ma_setting.period:
                    ma = self.data[ma_setting.name]
                    ma_lines = self._get_quota_lines(ma)
                    if ma_lines:  # 确保有线段可绘制
                        p.setPen(pg.mkPen(ma_setting.color_hex, width=ma_setting.line_width))
                        p.drawLines(*tuple(ma_lines))


            # if 'ma5' in self.data.columns and len(self.data) > 5:
            #     ma5 = self.data['ma5']
            #     ma5_lines = self._get_quota_lines(ma5)
            #     if ma5_lines:  # 确保有线段可绘制
            #         p.setPen(pg.mkPen(dict_ma_color[f'{IndicatrosEnum.MA.value}5'], width=2))
            #         p.drawLines(*tuple(ma5_lines))

            # if 'ma10' in self.data.columns and len(self.data) > 10:
            #     ma10 = self.data['ma10']
            #     ma10_lines = self._get_quota_lines(ma10)
            #     if ma10_lines:
            #         p.setPen(pg.mkPen(dict_ma_color[f'{IndicatrosEnum.MA.value}10'], width=2))
            #         p.drawLines(*tuple(ma10_lines))

            # if 'ma24' in self.data.columns and len(self.data) > 24:
            #     ma24 = self.data['ma24']
            #     ma24_lines = self._get_quota_lines(ma24)
            #     if ma24_lines:
            #         p.setPen(pg.mkPen(dict_ma_color[f'{IndicatrosEnum.MA.value}24'], width=2))
            #         p.drawLines(*tuple(ma24_lines))

            # if 'ma52' in self.data.columns and len(self.data) > 52:
            #     ma52 = self.data['ma52']
            #     ma52_lines = self._get_quota_lines(ma52)
            #     if ma52_lines:
            #         p.setPen(pg.mkPen(dict_ma_color[f'{IndicatrosEnum.MA.value}52'], width=2))
            #         p.drawLines(*tuple(ma52_lines))

        #绘制蜡烛图
        dict_kline_color = get_dict_kline_color()
        for i in range(len(self.data)):
            # 使用 iloc 按位置访问数据，而不是按索引访问
            open_price = self.data['open'].iloc[i]
            close_price = self.data['close'].iloc[i]
            high_price = self.data['high'].iloc[i]
            low_price = self.data['low'].iloc[i]

            if close_price < open_price:
                #下跌－绿色
                p.setPen(pg.mkPen(dict_kline_color[IndicatrosEnum.KLINE_DESC.value]))
                p.setBrush(pg.mkBrush(dict_kline_color[IndicatrosEnum.KLINE_DESC.value]))
                p.drawLine(QtCore.QPointF(i, low_price), QtCore.QPointF(i, high_price))
                p.drawRect(QtCore.QRectF(i - w, open_price, w * 2, close_price - open_price))
                
            else:
                #上涨－红色 空心蜡烛
                p.setPen(pg.mkPen(dict_kline_color[IndicatrosEnum.KLINE_ASC.value]))
                p.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))  # 设置为空画刷，绘制空心矩形
                
                # 绘制上下影线
                if high_price != close_price:
                    p.drawLine(QtCore.QPointF(i, high_price), QtCore.QPointF(i, close_price))
                    
                if low_price != open_price:
                    p.drawLine(QtCore.QPointF(i, open_price), QtCore.QPointF(i, low_price))
                
                #绘制实体（空心）
                if close_price == open_price:
                    p.drawLine(QtCore.QPointF(i - w, open_price), QtCore.QPointF(i + w, open_price))
                else:
                    p.drawRect(QtCore.QRectF(i - w, open_price, w * 2, close_price - open_price))
                    
        p.end()
    def _get_quota_lines(self, data):
        #…获取指标线段的坐标点·
        lines = []
        for i in range(1, len(data)):
            if not np.isnan(data.iloc[i-1]) and not np.isnan(data.iloc[i]):
                lines.append(QtCore.QLineF(QtCore.QPointF(i-1, data.iloc[i-1]),
                QtCore.QPointF(i, data.iloc[i])))
        return lines
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    def boundingRect(self) :
        return QtCore.QRectF(self.picture.boundingRect())

