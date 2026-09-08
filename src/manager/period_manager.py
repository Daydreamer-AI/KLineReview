from enum import Enum
from PyQt5.QtCore import QCoreApplication

# 1. 数字标签映射 (这个不涉及翻译，可以预先构建)
_NUMBER_LABEL_MAPPING = {
    "time": "Time", "1": "1m", "3": "3m", "5": "5m", "10": "10m",
    "15": "15m", "30": "30m", "45": "45m", "60": "60m", "90": "90m",
    "120": "120m", "7": "7m", "25": "25m",
}
_REVERSE_NUMBER_LABEL_MAPPING = {v: k for k, v in _NUMBER_LABEL_MAPPING.items()}

# 2. 分钟级别集合 (不涉及翻译)
_MINUTE_PERIOD_VALUES = {"1m", "3m", "5m", "10m", "15m", "30m", "45m", "60m", "90m", "120m", "7m", "25m"}

# 3. 周期优先级顺序 (用于大小比较)
_PERIOD_ORDER = [
    '1m', '3m', '5m', '7m', '10m', '15m', '25m', '30m', '45m', '60m', '90m', '120m',
    '1d', '2d', '3d', '1w', '2w', '1M', '2M', '3M', '1Q', '6M', '12M', '1Y'
]


class TimePeriod(Enum):
    # 纯粹的枚举成员
    TIME = 'Time'
    MINUTE_1 = '1m'
    MINUTE_3 = '3m'
    MINUTE_5 = '5m'
    MINUTE_10 = '10m'
    MINUTE_15 = '15m'
    MINUTE_30 = '30m'
    MINUTE_45 = '45m'
    MINUTE_60 = '60m'
    MINUTE_90 = '90m'
    MINUTE_120 = '120m'
    DAY = '1d'
    WEEK = '1w'
    MONTH = '1M'     
    QUARTER = '1Q'  
    YEAR = '1Y'
    DAY_2 = '2d'
    DAY_3 = '3d'
    WEEK_2 = '2w'
    MONTH_2 = '2M'
    MONTH_3 = '3M'
    MONTH_6 = '6M'
    MONTH_12 = '12M'
    MINUTE_7 = '7m'
    MINUTE_25 = '25m'

    # ================= 动态翻译与反查 =================

    @property
    def label(self):
        """
        实时获取当前语言环境下的翻译字符串。
        每次访问都会重新调用 translate，绝不缓存。
        """
        return QCoreApplication.translate(__name__, self.value)

    @classmethod
    def from_label(cls, label):
        """
        根据当前语言环境下的标签，实时反查对应的枚举成员。
        因为标签是动态翻译的，所以反查也必须是动态比对的。
        """
        for member in cls:
            if member.label == label:
                return member
        # 如果遍历所有成员都没找到，返回默认值
        return cls.DAY
    
    @classmethod
    def get_chinese_label(cls, period):
        """根据枚举值获取对应的标签"""
        return period.label
    
    @classmethod
    def from_minute_number_label(cls, label):
        """根据数字标签获取对应的枚举值"""
        period_str = _NUMBER_LABEL_MAPPING.get(label, '1d')
        return cls(period_str)
    
    @classmethod
    def get_number_label(cls, period):
        """根据枚举值获取对应的数字标签"""
        return _REVERSE_NUMBER_LABEL_MAPPING.get(period.value, "30")
    
    @classmethod
    def get_period_list(cls):
        """获取当前支持的所有级别"""
        return list(cls)
    
    @classmethod
    def is_minute_level(cls, period) -> bool:
        """判断是否为分钟级别"""
        return period.value in _MINUTE_PERIOD_VALUES
    
    def get_table_name(self):
        """获取对应级别的数据库表名"""
        return f"stock_data_{self.value}"
    

    # ================= 比较运算符 =================

    def _get_order_index(self):
        """获取当前周期在优先级列表中的索引"""
        try:
            return _PERIOD_ORDER.index(self.value)
        except ValueError:
            raise ValueError(f"无法找到周期值 '{self.value}' 在排序列表中的位置")

    def __lt__(self, other):
        if not isinstance(other, TimePeriod):
            return NotImplemented
        return self._get_order_index() < other._get_order_index()
    
    def __le__(self, other):
        if not isinstance(other, TimePeriod):
            return NotImplemented
        return self._get_order_index() <= other._get_order_index()
    
    def __gt__(self, other):
        if not isinstance(other, TimePeriod):
            return NotImplemented
        return self._get_order_index() > other._get_order_index()
    
    def __ge__(self, other):
        if not isinstance(other, TimePeriod):
            return NotImplemented
        return self._get_order_index() >= other._get_order_index()

    def is_shorter_than(self, other):
        return self < other
    
    def is_longer_than(self, other):
        return self > other
    
    def is_same_as(self, other):
        return self == other
    
class ReviewPeriodProcessData(object):
    def __init__(self):
        self.current_period = None
        self.current_start_date_time = None
        self.current_date_time = None
        self.current_start_index = None
        self.current_index = None
        self.current_min_index = None
        self.current_max_index = None

