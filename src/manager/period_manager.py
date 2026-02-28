from enum import Enum
from functools import total_ordering

class TimePeriod(Enum):
    # 定义周期优先级顺序（使用字符串值避免初始化问题）
    _period_order = [
        '1m', '3m', '5m', '10m', '15m', '30m', '45m', '60m', '90m', '120m',
        '1d', '1w', '1M', '1Q', '1Y'
    ]

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
    
    @classmethod
    def from_label(cls, label):
        """根据按钮标签获取对应的枚举值"""
        mapping = {
            "日线": cls.DAY,
            "周线": cls.WEEK,
            "月线": cls.MONTH,
            "季线": cls.QUARTER,
            "年线": cls.YEAR,
            "1分": cls.MINUTE_1,
            "3分": cls.MINUTE_3,
            "5分": cls.MINUTE_5,
            "10分": cls.MINUTE_10,
            "15分": cls.MINUTE_15,
            "30分": cls.MINUTE_30,
            "45分": cls.MINUTE_45,
            "60分": cls.MINUTE_60,
            "90分": cls.MINUTE_90,
            "120分": cls.MINUTE_120,
        }
        return mapping.get(label, cls.DAY)
    
    
    @classmethod
    def get_chinese_label(cls, period):
        """根据枚举值获取对应的中文标签"""
        # 延迟初始化映射字典
        if not hasattr(cls, '_chinese_label_mapping'):
            cls._chinese_label_mapping = {
                cls.DAY: "日线",
                cls.WEEK: "周线",
                cls.MONTH: "月线",
                cls.QUARTER: "季线",
                cls.YEAR: "年线",
                cls.MINUTE_1: "1分",
                cls.MINUTE_3: "3分",
                cls.MINUTE_5: "5分",
                cls.MINUTE_10: "10分",
                cls.MINUTE_15: "15分",
                cls.MINUTE_30: "30分",
                cls.MINUTE_45: "45分",
                cls.MINUTE_60: "60分",
                cls.MINUTE_90: "90分",
                cls.MINUTE_120: "120分",
            }
        return cls._chinese_label_mapping.get(period, "日线")
    
    @classmethod
    def from_minute_number_label(cls, label):
        """根据按钮标签获取对应的枚举值"""
        mapping = {
            "1": cls.MINUTE_1,
            "3": cls.MINUTE_3,
            "5": cls.MINUTE_5,
            "10": cls.MINUTE_10,
            "15": cls.MINUTE_15,
            "30": cls.MINUTE_30,
            "45": cls.MINUTE_45,
            "60": cls.MINUTE_60,
            "90": cls.MINUTE_90,
            "120": cls.MINUTE_120,
        }
        return mapping.get(label, cls.DAY)
    
    @classmethod
    def get_number_label(cls, period):
        """根据枚举值获取对应的按钮标签"""
        # 延迟初始化映射字典
        if not hasattr(cls, '_number_label_mapping'):
            cls._number_label_mapping = {
                cls.MINUTE_1: "1",
                cls.MINUTE_3: "3",
                cls.MINUTE_5: "5",
                cls.MINUTE_10: "10",
                cls.MINUTE_15: "15",
                cls.MINUTE_30: "30",
                cls.MINUTE_45: "45",
                cls.MINUTE_60: "60",
                cls.MINUTE_90: "90",
                cls.MINUTE_120: "120",
            }

        return cls._number_label_mapping.get(period, "30")
    
    @classmethod
    def get_period_list(cls):
        '''获取当前支持的所有级别'''
        return [cls.MINUTE_1, cls.MINUTE_3, cls.MINUTE_5, cls.MINUTE_10, cls.MINUTE_15, 
                cls.MINUTE_30, cls.MINUTE_45, cls.MINUTE_60, cls.MINUTE_90, cls.MINUTE_120, 
                cls.DAY, cls.WEEK, cls.MONTH, cls.QUARTER, cls.YEAR]
    
    @classmethod
    def is_minute_level(cls, period) -> bool:
        return period in [cls.MINUTE_1, cls.MINUTE_3, cls.MINUTE_5, cls.MINUTE_10, 
                         cls.MINUTE_15, cls.MINUTE_30, cls.MINUTE_45, cls.MINUTE_60, 
                         cls.MINUTE_90, cls.MINUTE_120]
    
    def get_table_name(self):
        """
        获取对应级别的数据库表名
        例如: '1d' -> 'stock_data_1d', '30m' -> 'stock_data_30m'
        """
        return f"stock_data_{self.value}"
    

    def compare_to(self, other):
        """
        比较当前周期与另一个周期的大小
        返回值: 
        - 负数: self < other
        - 0: self == other
        - 正数: self > other
        """
        if not isinstance(other, TimePeriod):
            raise TypeError("参数必须是TimePeriod枚举类型")
        
        # 定义周期优先级顺序
        period_order = [
            '1m', '3m', '5m', '10m', '15m', '30m', '45m', '60m', '90m', '120m',
            '1d', '1w', '1M', '1Q', '1Y'
        ]
        
        try:
            self_index = period_order.index(self.value)
            other_index = period_order.index(other.value)
            return self_index - other_index
        except ValueError as e:
            raise ValueError(f"无法找到周期值在排序列表中的位置: {e}")
    
    def __hash__(self):
        """使枚举成员可哈希"""
        return hash(self.value)

    def __lt__(self, other):
        """小于比较"""
        if not isinstance(other, TimePeriod):
            return NotImplemented
        return self.compare_to(other) < 0
    
    def __le__(self, other):
        """小于等于比较"""
        if not isinstance(other, TimePeriod):
            return NotImplemented
        return self.compare_to(other) <= 0
    
    def __gt__(self, other):
        """大于比较"""
        if not isinstance(other, TimePeriod):
            return NotImplemented
        return self.compare_to(other) > 0
    
    def __ge__(self, other):
        """大于等于比较"""
        if not isinstance(other, TimePeriod):
            return NotImplemented
        return self.compare_to(other) >= 0
    
    def __eq__(self, other):
        """等于比较"""
        if not isinstance(other, TimePeriod):
            return NotImplemented
        return self.value == other.value
    
    def __ne__(self, other):
        """不等于比较"""
        if not isinstance(other, TimePeriod):
            return NotImplemented
        return self.value != other.value
    
    def is_shorter_than(self, other):
        """判断当前周期是否比另一个周期短"""
        return self < other
    
    def is_longer_than(self, other):
        """判断当前周期是否比另一个周期长"""
        return self > other
    
    def is_same_as(self, other):
        """判断当前周期是否与另一个周期相同"""
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

