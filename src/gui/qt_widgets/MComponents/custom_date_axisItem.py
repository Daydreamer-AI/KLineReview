from pyqtgraph import DateAxisItem, AxisItem
from PyQt5.QtCore import QDateTime

class CustomDateAxisItem(DateAxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def tickStrings(self, values, scale, spacing):
        """重写此方法来自定义日期显示格式为'YYYY-MM-DD'"""
        strings = []
        for value in values:
            # 关键修复：将浮点数转换为整数
            timestamp_ms = int(value * 1000)  # 转换为整数毫秒
            qdt = QDateTime.fromMSecsSinceEpoch(timestamp_ms)
            date_str = qdt.toString('yyyy-MM-dd')
            strings.append(date_str)
        return strings
    

class NoLabelAxis(AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def tickStrings(self, values, scale, spacing):
        # 返回空字符串列表，隐藏所有刻度值
        return [""] * len(values)