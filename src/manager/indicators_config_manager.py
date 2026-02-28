import json
from pathlib import Path
from typing import Dict, Any, Optional
from manager.logging_manager import get_logger
from manager.config_manager import ConfigManager

from enum import Enum

class IndicatrosEnum(Enum):
    '''
        统一规范指标键名称，作用范围：Pandas.DataFrame对象的列名，字典键名称，显示的指标名称
    '''
    MA = 'ma'
    VOLUME = 'volume'
    AMOUNT = 'amount'
    MACD = 'macd'
    MACD_DIFF = 'diff'
    MACD_DEA = 'dea'
    KDJ = 'kdj'
    KDJ_K = 'k'
    KDJ_D = 'd'
    KDJ_J = 'j'
    RSI = 'rsi'
    BOLL = 'boll'
    BOLL_MID = 'mid'  
    BOLL_UPPER = 'upper'     
    BOLL_LOWER = 'lower'
    BOLL_CLOSE = 'close'

    KLINE = 'kline'
    KLINE_ASC = 'asc'
    KLINE_DESC = 'desc'
    
    KLINE_OPEN = 'open'
    KLINE_CLOSE = 'close'
    KLINE_HIGH = 'high'
    KLINE_LOW = 'low'

    TURNOVER_RATE = 'turnover_rate'
    VOLUME_RATIO = 'volume_ratio'



    @classmethod
    def get_chinese_label(cls, indicator_name):
        """根据枚举值获取对应的中文标签"""
        # 延迟初始化映射字典
        if not hasattr(cls, '_chinese_label_mapping'):
            cls._chinese_label_mapping = {
                cls.KLINE: "K线图",
                cls.VOLUME: "成交量",
                cls.AMOUNT: "成交额",
                cls.MACD: "MACD",
                cls.KDJ: "KDJ",
                cls.RSI: "RSI",
                cls.BOLL: "BOLL"
            }
        return cls._chinese_label_mapping.get(indicator_name, "K线图")
    
    @classmethod
    def get_check_columns(cls):
        return ()

def color_to_hex(color):
    """
    将RGB/RGBA颜色元组转换为十六进制颜色字符串
    
    Args:
        color: RGB颜色元组，格式为 (r, g, b) 或 RGBA颜色元组，格式为 (r, g, b, a)
               其中每个值范围为0-255
    
    Returns:
        str: 十六进制颜色字符串，格式为 '#rrggbb' 或 '#rrggbbaa'
    """
    if isinstance(color, (tuple, list)):
        if len(color) == 3:
            # RGB 格式
            r, g, b = color
            return f"#{r:02x}{g:02x}{b:02x}"
        elif len(color) == 4:
            # RGBA 格式
            r, g, b, a = color
            return f"#{r:02x}{g:02x}{b:02x}{a:02x}"
        else:
            raise ValueError("颜色必须是包含3个或4个整数的元组或列表，格式为(r, g, b)或(r, g, b, a)")
    else:
        raise ValueError("颜色必须是元组或列表")


def hex_to_color(hex_color):
    """
    将十六进制颜色字符串转换为RGB/RGBA颜色元组
    
    Args:
        hex_color: 十六进制颜色字符串，格式为 '#rrggbb' 或 '#rrggbbaa' 或 'rrggbb' 或 'rrggbbaa'
    
    Returns:
        tuple: RGB颜色元组，格式为 (r, g, b) 或 RGBA颜色元组，格式为 (r, g, b, a)
    """
    # 移除可能存在的 # 符号
    hex_color = hex_color.lstrip('#')
    
    # 验证十六进制颜色格式
    if len(hex_color) not in (6, 8):
        raise ValueError("十六进制颜色必须是6位或8位字符，格式为 #rrggbb 或 #rrggbbaa")
    
    try:
        if len(hex_color) == 6:
            # RGB 格式
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (r, g, b)
        elif len(hex_color) == 8:
            # RGBA 格式
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            a = int(hex_color[6:8], 16)
            return (r, g, b, a)
    except ValueError:
        raise ValueError("无效的十六进制颜色字符串")

# 示例用法：
# RGB 颜色转换
# rgb_color = (255, 61, 61)
# hex_color = color_to_hex(rgb_color)  # 返回 '#ff3d3d'
# back_to_rgb = hex_to_color(hex_color)  # 返回 (255, 61, 61)

# RGBA 颜色转换（带透明度）
# rgba_color = (255, 61, 61, 128)  # 最后一个值是透明度，128表示半透明
# hex_color_with_alpha = color_to_hex(rgba_color)  # 返回 '#ff3d3d80'
# back_to_rgba = hex_to_color(hex_color_with_alpha)  # 返回 (255, 61, 61, 128)


# k线涨跌幅颜色
kline_half_width = 0.25  # 默认K线半边宽度
def get_kline_half_width():
    return kline_half_width

def set_kline_half_width(width):
    global kline_half_width
    kline_half_width = width


dict_kline_color = {
IndicatrosEnum.KLINE_DESC.value: (0, 168, 67), #绿色－下跌 (0, 169, 178), (0, 168, 67), (43, 186, 146)
IndicatrosEnum.KLINE_ASC.value: (255, 61, 61) #红色 -上涨
}

dict_kline_color_hex = {
IndicatrosEnum.KLINE_DESC.value: '#00a84b', #绿色－下跌
IndicatrosEnum.KLINE_ASC.value: '#ff3d3d' #红色 -上涨
}

def get_dict_kline_color():
    return dict_kline_color

def get_dict_kline_color_hex():
    return dict_kline_color_hex


# 均线
# 默认颜色
dict_ma_color = {
f'{IndicatrosEnum.MA.value}5': (0, 0, 0), 
f'{IndicatrosEnum.MA.value}10': (217, 186, 38), 
f'{IndicatrosEnum.MA.value}20': (25, 160, 255), 
f'{IndicatrosEnum.MA.value}24': (239, 57, 178),
f'{IndicatrosEnum.MA.value}30': (255, 154, 117),
f'{IndicatrosEnum.MA.value}52': (10, 204, 90),
f'{IndicatrosEnum.MA.value}60': (119, 60, 178),
f'{IndicatrosEnum.MA.value}120': (176, 187, 242),
f'{IndicatrosEnum.MA.value}250': (175, 117, 234)
}

dict_ma_color_hex = {
    f'{IndicatrosEnum.MA.value}5': '#000000', 
    f'{IndicatrosEnum.MA.value}10': '#d9ba26', 
    f'{IndicatrosEnum.MA.value}20': '#1fa0ff', 
    f'{IndicatrosEnum.MA.value}24': '#ef39ae',
    f'{IndicatrosEnum.MA.value}30': '#ff9a75',
    f'{IndicatrosEnum.MA.value}52': '#0acc5a',
    f'{IndicatrosEnum.MA.value}60': '#7777ff',
    f'{IndicatrosEnum.MA.value}120': '#afafef',
    f'{IndicatrosEnum.MA.value}250': '#af77ef'
}

# 成交量
dict_volume_color = {
f'{IndicatrosEnum.MA.value}5': dict_ma_color[f'{IndicatrosEnum.MA.value}5'],
f'{IndicatrosEnum.MA.value}10': dict_ma_color[f'{IndicatrosEnum.MA.value}10'],
f'{IndicatrosEnum.MA.value}20': dict_ma_color[f'{IndicatrosEnum.MA.value}20']
}

dict_volume_color_hex = {
    f'{IndicatrosEnum.MA.value}5': dict_ma_color_hex[f'{IndicatrosEnum.MA.value}5'],
    f'{IndicatrosEnum.MA.value}10': dict_ma_color_hex[f'{IndicatrosEnum.MA.value}10'],
    f'{IndicatrosEnum.MA.value}20': dict_ma_color_hex[f'{IndicatrosEnum.MA.value}20']
}

dict_volume_color_user = dict_volume_color.copy()
dict_volume_color_user_hex = dict_volume_color_hex.copy()



# 成交额
dict_amount_color = {
f'{IndicatrosEnum.MA.value}5': dict_ma_color[f'{IndicatrosEnum.MA.value}5'],
f'{IndicatrosEnum.MA.value}10': dict_ma_color[f'{IndicatrosEnum.MA.value}10'],
f'{IndicatrosEnum.MA.value}20': dict_ma_color[f'{IndicatrosEnum.MA.value}20']
}

dict_amount_color_hex = {
    f'{IndicatrosEnum.MA.value}5': dict_ma_color_hex[f'{IndicatrosEnum.MA.value}5'],
    f'{IndicatrosEnum.MA.value}10': dict_ma_color_hex[f'{IndicatrosEnum.MA.value}10'],
    f'{IndicatrosEnum.MA.value}20': dict_ma_color_hex[f'{IndicatrosEnum.MA.value}20']
}

dict_amount_color_user = dict_amount_color.copy()
dict_amount_color_user_hex = dict_amount_color_hex.copy()


# MACD
dict_macd_color = {
IndicatrosEnum.MACD_DIFF.value: (0, 0, 0),
IndicatrosEnum.MACD_DEA.value: (217, 186, 38),
}

dict_macd_color_hex = {
    IndicatrosEnum.MACD_DIFF.value: '#000000',
    IndicatrosEnum.MACD_DEA.value: '#d9ba26'
}

dict_macd_color_user = dict_macd_color.copy()
dict_macd_color_user_hex = dict_macd_color_hex.copy()

# KDJ
dict_kdj_color = { 
IndicatrosEnum.KDJ_K.value: (217, 186, 38),
IndicatrosEnum.KDJ_D.value: (25, 160, 255),
IndicatrosEnum.KDJ_J.value: (244, 134, 208)
}

dict_kdj_color_hex = { 
    IndicatrosEnum.KDJ_K.value: '#d9ba26',
    IndicatrosEnum.KDJ_D.value: '#1fa0ff',
    IndicatrosEnum.KDJ_J.value: '#ef39ae'
}

dict_kdj_color_user = dict_kdj_color.copy()
dict_kdj_color_user_hex = dict_kdj_color_hex.copy()

# RSI
dict_rsi_color = { 
f'{IndicatrosEnum.RSI.value}6': (217, 186, 38),
f'{IndicatrosEnum.RSI.value}12': (10, 204, 90),
f'{IndicatrosEnum.RSI.value}24': (25, 160, 255)
}

dict_rsi_color_hex = { 
    f'{IndicatrosEnum.RSI.value}6': '#d9ba26',
    f'{IndicatrosEnum.RSI.value}12': '#0acc5a',
    f'{IndicatrosEnum.RSI.value}24': '#1fa0ff'
}

dict_rsi_color_user = dict_rsi_color.copy()
dict_rsi_color_user_hex = dict_rsi_color_hex.copy()

# BOLL
dict_boll_color = { 
IndicatrosEnum.BOLL_UPPER.value: (255, 61, 61),
IndicatrosEnum.BOLL_MID.value: (25, 160, 255),
IndicatrosEnum.BOLL_LOWER.value: (10, 204, 90),
IndicatrosEnum.BOLL_CLOSE.value: (0, 0, 0)
}

dict_boll_color_hex = { 
    IndicatrosEnum.BOLL_UPPER.value: '#ff3d3d',
    IndicatrosEnum.BOLL_MID.value: '#1fa0ff',
    IndicatrosEnum.BOLL_LOWER.value: '#0acc5a',
    IndicatrosEnum.BOLL_CLOSE.value: '#000000'
}

dict_boll_color_user = dict_boll_color.copy()
dict_boll_color_user_hex = dict_boll_color_hex.copy()


# -------------------------------------------------------------


class IndicatorSetting:
    """通用指标设置基类"""
    def __init__(self, id: int = 0, period: int = 5, name: str = '', visible: bool = True, 
                 line_width: int = 2, color: tuple = (0, 0, 0), color_hex: str = '#000000'):
        self.id = id
        self.period = period
        self.name = name
        self.visible = visible
        self.line_width = line_width
        self.color = color
        self.color_hex = color_hex

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式用于序列化"""
        return {
            'id': self.id,
            'period': self.period,
            'name': self.name,
            'visible': self.visible,
            'line_width': self.line_width,
            'color': list(self.color),
            'color_hex': self.color_hex
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        instance = cls(
            id=data['id'],
            period=data['period'],
            name= data['name'],
            visible=data.get('visible', True),
            line_width=data.get('line_width', 2),
            color=tuple(data['color']),
            color_hex=data['color_hex']
        )
        return instance
    
    def set_color(self, color):
        self.color = color
        self.color_hex = color_to_hex(color)

    def set_color_hex(self, color_hex):
        self.color = hex_to_color(color_hex)
        self.color_hex = color_hex


class KLineSetting(IndicatorSetting):
    """K线设置"""
    def __init__(self, id: int = 0, period: int = 5, name: str = 'kline', visible: bool = True, 
                 line_width: int = 2, color: tuple = (0, 0, 0), color_hex: str = '#000000'):
        
        if not name:
            name = f'kline'

        super().__init__(id, period, name, visible, line_width, color, color_hex)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        return super().from_dict(data)


class MASetting(IndicatorSetting):
    """均线设置"""
    def __init__(self, id: int = 0, period: int = 5, name: str = '', visible: bool = True, 
                 line_width: int = 2, color: tuple = (0, 0, 0), color_hex: str = '#000000'):
        
        if not name:
            name = f'{IndicatrosEnum.MA.value}{period}'

        super().__init__(id, period, name, visible, line_width, color, color_hex)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        return super().from_dict(data)



# class ColorSetting(IndicatorSetting):
#     """颜色设置基类"""
#     def __init__(self, name: str, colors: Dict[str, tuple], color_hexes: Dict[str, str], visible: bool = True):
#         super().__init__(name, visible)
#         self.colors = colors  # RGB格式
#         self.color_hexes = color_hexes  # 十六进制格式

#     def to_dict(self) -> Dict[str, Any]:
#         return {
#             'name': self.name,
#             'visible': self.visible,
#             'colors': {k: list(v) for k, v in self.colors.items()},
#             'color_hexes': self.color_hexes
#         }

#     @classmethod
#     def from_dict(cls, data: Dict[str, Any]):
#         instance = cls(
#             name=data['name'],
#             colors={k: tuple(v) for k, v in data['colors'].items()},
#             color_hexes=data['color_hexes'],
#             visible=data.get('visible', True)
#         )
#         return instance


class VolumeSetting(IndicatorSetting):
    """成交量设置"""
    def __init__(self, id: int = 0, period: int = 5, name: str = '', visible: bool = True, 
                 line_width: int = 2, color: tuple = (0, 0, 0), color_hex: str = '#000000'):
        
        if not name:
            name = f'{IndicatrosEnum.MA.value}{period}'

        super().__init__(id, period, name, visible, line_width, color, color_hex)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        return super().from_dict(data)


class AmountSetting(IndicatorSetting):
    """成交额设置"""
    def __init__(self, id: int = 0, period: int = 5, name: str = '', visible: bool = True, 
                 line_width: int = 2, color: tuple = (0, 0, 0), color_hex: str = '#000000'):
        
        if not name:
            name = f'{IndicatrosEnum.MA.value}{period}'

        super().__init__(id, period, name, visible, line_width, color, color_hex)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        return super().from_dict(data)


class MACDSetting(IndicatorSetting):
    """MACD设置"""
    def __init__(self, id: int = 0, period: int = 5, name: str = '', visible: bool = True, 
                 line_width: int = 2, color: tuple = (0, 0, 0), color_hex: str = '#000000'):
        
        # id: 0-短周期-DIFF，1-长周期-DEA，2-移动平均周期
        if id < 0 or id > 2:
            raise ValueError("Invalid id value. It must be 0, 1, or 2.")
        
        if not name:
            if id == 0:
                name = IndicatrosEnum.MACD_DIFF.value
            elif id == 1:
                name = IndicatrosEnum.MACD_DEA.value
            else:
                name = ''
        
        super().__init__(id, period, name, visible, line_width, color, color_hex)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        return super().from_dict(data)


class KDJSetting(IndicatorSetting):
    """KDJ设置"""
    def __init__(self, id: int = 0, period: int = 5, name: str = '', visible: bool = True, 
                line_width: int = 2, color: tuple = (0, 0, 0), color_hex: str = '#000000'):
    
        # id: 0-计算周期-K，1-移动平均周期-D，2-移动平均周期-J
        if id < 0 or id > 2:
            raise ValueError("Invalid id value. It must be 0, 1, or 2.")
        
        if not name:
            if id == 0:
                name = IndicatrosEnum.KDJ_K.value
            elif id == 1:
                name = IndicatrosEnum.KDJ_D.value
            else:
                name = IndicatrosEnum.KDJ_J.value
        
        super().__init__(id, period, name, visible, line_width, color, color_hex)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        return super().from_dict(data)


class RSISetting(IndicatorSetting):
    """RSI设置"""
    def __init__(self, id: int = 0, period: int = 5, name: str = '', visible: bool = True, 
                line_width: int = 2, color: tuple = (0, 0, 0), color_hex: str = '#000000'):
    
        # id: 0-移动平均周期，1-移动平均周期，2-移动平均周期
        if id < 0 or id > 2:
            raise ValueError("Invalid id value. It must be 0, 1, or 2.")
        
        if not name:
            name = f'{IndicatrosEnum.RSI.value}{period}'
        
        super().__init__(id, period, name, visible, line_width, color, color_hex)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        return super().from_dict(data)


class BOLLSetting(IndicatorSetting):
    """BOLL设置"""
    def __init__(self, id: int = 0, period: int = 5, name: str = '', visible: bool = True, 
                line_width: int = 2, color: tuple = (0, 0, 0), color_hex: str = '#000000'):
    
        # id: 0-计算周期-MID，1-股票参数特性-UPPER，2-LOWER
        if id < 0 or id > 2:
            raise ValueError("Invalid id value. It must be 0, 1, or 2.")
        
        if not name:
            if id == 0:
                name = IndicatrosEnum.BOLL_MID.value
            elif id == 1:
                name = IndicatrosEnum.BOLL_UPPER.value
            else:
                name = IndicatrosEnum.BOLL_LOWER.value
        
        super().__init__(id, period, name, visible, line_width, color, color_hex)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        return super().from_dict(data)


class IndicatorConfigManager:
    """指标配置管理器，复用ConfigManager的实现"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager()
        
        # 使用统一的配置目录
        config_dir = self.config_manager.get_config_path().parent
        self.default_config_file = config_dir / 'indicator_config_default.json'
        self.user_config_file = config_dir / 'indicator_config_user.json'
        
        # 存储所有配置
        self.default_configs = {}  # 默认配置，格式：{'指标名称' : {id : IndicatorSetting}}
        self.user_configs = {}     # 用户配置，格式：{'指标名称' : {id : IndicatorSetting}}
        
        # 初始化默认配置
        self._init_default_configs()
    
    def _init_default_configs(self):
        """初始化默认配置"""
        
        # 加载默认配置
        if self.load_default_config():
            self.logger.info("成功加载默认配置")
        else:
            # 从 indicators_config_manager.py 中导入的默认值
            from .indicators_config_manager import (
                dict_ma_color, dict_ma_color_hex, 
                dict_volume_color, dict_volume_color_hex,
                dict_amount_color, dict_amount_color_hex,
                dict_macd_color, dict_macd_color_hex,
                dict_kdj_color, dict_kdj_color_hex,
                dict_rsi_color, dict_rsi_color_hex,
                dict_boll_color, dict_boll_color_hex
            )
            
            # 默认均线配置
            self.default_configs[IndicatrosEnum.MA.value] = {
                0: MASetting(0, 5, '', True, 2, dict_ma_color[f'{IndicatrosEnum.MA.value}5'], dict_ma_color_hex[f'{IndicatrosEnum.MA.value}5']),
                1: MASetting(1, 10, '', True, 2, dict_ma_color[f'{IndicatrosEnum.MA.value}10'], dict_ma_color_hex[f'{IndicatrosEnum.MA.value}10']),
                2: MASetting(2, 20, '', False, 2, dict_ma_color[f'{IndicatrosEnum.MA.value}20'], dict_ma_color_hex[f'{IndicatrosEnum.MA.value}20']),
                3: MASetting(3, 24, '', True, 2, dict_ma_color[f'{IndicatrosEnum.MA.value}24'], dict_ma_color_hex[f'{IndicatrosEnum.MA.value}24']),
                4: MASetting(4, 30, '', False, 2, dict_ma_color[f'{IndicatrosEnum.MA.value}30'], dict_ma_color_hex[f'{IndicatrosEnum.MA.value}30']),
                5: MASetting(5, 52, '', True, 2, dict_ma_color[f'{IndicatrosEnum.MA.value}52'], dict_ma_color_hex[f'{IndicatrosEnum.MA.value}52']),
                6: MASetting(6, 60, '', False, 2, dict_ma_color[f'{IndicatrosEnum.MA.value}60'], dict_ma_color_hex[f'{IndicatrosEnum.MA.value}60']),
                7: MASetting(7, 120, '', False, 2, dict_ma_color[f'{IndicatrosEnum.MA.value}120'], dict_ma_color_hex[f'{IndicatrosEnum.MA.value}120']),
                8: MASetting(8, 250, '', False, 2, dict_ma_color[f'{IndicatrosEnum.MA.value}250'], dict_ma_color_hex[f'{IndicatrosEnum.MA.value}250'])
            }
            
            # 其他指标默认配置
            self.default_configs[IndicatrosEnum.VOLUME.value] = {
                0: VolumeSetting(0, 5, '', False, 2, dict_volume_color[f'{IndicatrosEnum.MA.value}5'], dict_volume_color_hex[f'{IndicatrosEnum.MA.value}5']),
                1: VolumeSetting(1, 10, '', False, 2, dict_volume_color[f'{IndicatrosEnum.MA.value}10'], dict_volume_color_hex[f'{IndicatrosEnum.MA.value}5']),
                2: VolumeSetting(2, 20, '', False, 2, dict_volume_color[f'{IndicatrosEnum.MA.value}20'], dict_volume_color_hex[f'{IndicatrosEnum.MA.value}20'])
            }
            
            self.default_configs[IndicatrosEnum.AMOUNT.value] = {
                0: AmountSetting(0, 5, '', False, 2, dict_amount_color[f'{IndicatrosEnum.MA.value}5'], dict_amount_color_hex[f'{IndicatrosEnum.MA.value}5']),
                1: AmountSetting(1, 10, '', False, 2, dict_amount_color[f'{IndicatrosEnum.MA.value}10'], dict_amount_color_hex[f'{IndicatrosEnum.MA.value}10']),
                2: AmountSetting(2, 20, '', False, 2, dict_amount_color[f'{IndicatrosEnum.MA.value}20'], dict_amount_color_hex[f'{IndicatrosEnum.MA.value}20'])
            }
            
            self.default_configs[IndicatrosEnum.MACD.value] = {
                0: MACDSetting(0, 12, '', True, 2, dict_macd_color[f'{IndicatrosEnum.MACD_DIFF.value}'], dict_macd_color_hex[f'{IndicatrosEnum.MACD_DIFF.value}']),
                1: MACDSetting(1, 26, '', True, 2, dict_macd_color[f'{IndicatrosEnum.MACD_DEA.value}'], dict_macd_color_hex[f'{IndicatrosEnum.MACD_DEA.value}']),
                2: MACDSetting(2, 9, '', True, 2, (0, 0, 0), '#000000')
            }
            
            self.default_configs[IndicatrosEnum.KDJ.value] = {
                0: KDJSetting(0, 9, '', True, 2, dict_kdj_color[f'{IndicatrosEnum.KDJ_K.value}'], dict_kdj_color_hex[f'{IndicatrosEnum.KDJ_K.value}']),
                1: KDJSetting(1, 3, '', True, 2, dict_kdj_color[f'{IndicatrosEnum.KDJ_D.value}'], dict_kdj_color_hex[f'{IndicatrosEnum.KDJ_D.value}']),
                2: KDJSetting(2, 3, '', True, 2, dict_kdj_color[f'{IndicatrosEnum.KDJ_J.value}'], dict_kdj_color_hex[f'{IndicatrosEnum.KDJ_J.value}'])
            }
            
            self.default_configs[IndicatrosEnum.RSI.value] = {
                0: RSISetting(0, 5, '', True, 2, dict_rsi_color[f'{IndicatrosEnum.RSI.value}6'], dict_rsi_color_hex[f'{IndicatrosEnum.RSI.value}6']),
                1: RSISetting(1, 12, '', True, 2, dict_rsi_color[f'{IndicatrosEnum.RSI.value}12'], dict_rsi_color_hex[f'{IndicatrosEnum.RSI.value}12']),
                2: RSISetting(2, 24, '', True, 2, dict_rsi_color[f'{IndicatrosEnum.RSI.value}24'], dict_rsi_color_hex[f'{IndicatrosEnum.RSI.value}24'])
            }
            
            self.default_configs[IndicatrosEnum.BOLL.value] = {
                0: BOLLSetting(0, 20, '', True, 2, dict_boll_color[f'{IndicatrosEnum.BOLL_MID.value}'], dict_boll_color_hex[f'{IndicatrosEnum.BOLL_MID.value}']),
                1: BOLLSetting(1, 2, '', True, 2, dict_boll_color[f'{IndicatrosEnum.BOLL_UPPER.value}'], dict_boll_color_hex[f'{IndicatrosEnum.BOLL_UPPER.value}']),
                2: BOLLSetting(2, 0, '', True, 2, dict_boll_color[f'{IndicatrosEnum.BOLL_LOWER.value}'], dict_boll_color_hex[f'{IndicatrosEnum.BOLL_LOWER.value}'])
            }
            
            # 初始化用户配置为空
            # for indicator_type in self.default_configs:
            #     self.user_configs[indicator_type] = {}


        # 加载用户配置
        if self.load_user_config():
            self.logger.info('加载用户配置成功')
        else:
            self.user_configs = self.default_configs.copy()

        # 确保初次加载时文件存在
        self.save_default_config()
        self.save_user_config()

        self.load_default_config()
        self.load_user_config()
    
    def get_default_configs(self):
        return self.default_configs
    
    def get_user_configs(self):
        return self.user_configs
    
    def get_default_config_by_indicator_type(self, indicator_type=IndicatrosEnum.MA.value):
        return self.default_configs.get(indicator_type, {})
    
    def get_user_config_by_indicator_type(self, indicator_type=IndicatrosEnum.MA.value):
        return self.user_configs.get(indicator_type, {})
    
    def get_default_config_columns_by_indicator_type(self, indicator_type=IndicatrosEnum.MA.value):
        dict_config_setting = self.default_configs.get(indicator_type, {})

        list_columns = []
        for id, setting in dict_config_setting.items():
            if setting.name:
                list_columns.append(setting.name)

        return list_columns
    
    def get_user_config_columns_by_indicator_type(self, indicator_type=IndicatrosEnum.MA.value):
        dict_config_setting = self.user_configs.get(indicator_type, {})

        list_columns = []
        for id, setting in dict_config_setting.items():
            if setting.name:
                list_columns.append(setting.name)

        if list_columns is None or len(list_columns) == 0:
            list_columns = self.get_default_config_columns_by_indicator_type(indicator_type)

        return list_columns

    def save_default_config(self):
        """保存默认配置到文件"""
        try:
            config_data = {}
            for indicator_type, settings in self.default_configs.items():
                config_data[indicator_type] = {}
                for key, setting in settings.items():
                    config_data[indicator_type][str(key)] = setting.to_dict()
            
            # 使用ConfigManager的save方法
            self.config_manager.set_config_path(self.default_config_file)
            self.config_manager._config_data = config_data
            self.config_manager.save()
                
        except Exception as e:
            self.logger.error(f"保存默认配置失败: {e}")
    
    def save_user_config(self):
        """保存用户配置到文件"""
        try:
            config_data = {}
            for indicator_type, settings in self.user_configs.items():
                config_data[indicator_type] = {}
                for key, setting in settings.items():
                    config_data[indicator_type][str(key)] = setting.to_dict()
            
            # 使用ConfigManager的save方法
            self.config_manager.set_config_path(self.user_config_file)
            self.config_manager._config_data = config_data
            self.config_manager.save()
                
        except Exception as e:
            self.logger.error(f"保存用户配置失败: {e}")
    
    def load_default_config(self):
        """从文件加载默认配置"""
        try:
            # 使用ConfigManager的load方法
            if self.default_config_file.exists():
                self.config_manager.set_config_path(self.default_config_file)
                if not self.config_manager._load_config():
                    return False
                
                config_data = self.config_manager._config_data
                
                self.default_configs = self._deserialize_config(config_data)
                return True
            else:
                return False
        except Exception as e:
            self.logger.error(f"加载默认配置失败: {e}")
            return False
    
    def load_user_config(self):
        """从文件加载用户配置"""
        try:
            # 使用ConfigManager的load方法
            if self.user_config_file.exists():
                self.config_manager.set_config_path(self.user_config_file)
                if not self.config_manager._load_config():
                    return False

                config_data = self.config_manager._config_data
                
                self.user_configs = self._deserialize_config(config_data)
                return True
            else:
                # 用户配置不存在，使用默认配置初始化
                self._init_user_configs_from_defaults()
                return False
        except Exception as e:
            self.logger.error(f"加载用户配置失败: {e}")
            # 加载失败时使用默认配置初始化
            self._init_user_configs_from_defaults()
            return False
    
    def _deserialize_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """反序列化配置数据"""
        result = {}
        
        for indicator_type, settings in config_data.items():
            result[indicator_type] = {}
            for key_str, setting_data in settings.items():
                # 根据配置类型创建相应的对象
                if indicator_type == IndicatrosEnum.MA.value:
                    setting = MASetting.from_dict(setting_data)
                elif indicator_type in [IndicatrosEnum.VOLUME.value, IndicatrosEnum.AMOUNT.value, IndicatrosEnum.MACD.value, IndicatrosEnum.KDJ.value, IndicatrosEnum.RSI.value, IndicatrosEnum.BOLL.value]:
                    # 使用通用的颜色设置类
                    if indicator_type == IndicatrosEnum.VOLUME.value:
                        setting = VolumeSetting.from_dict(setting_data)
                    elif indicator_type == IndicatrosEnum.AMOUNT.value:
                        setting = AmountSetting.from_dict(setting_data)
                    elif indicator_type == IndicatrosEnum.MACD.value:
                        setting = MACDSetting.from_dict(setting_data)
                    elif indicator_type == IndicatrosEnum.KDJ.value:
                        setting = KDJSetting.from_dict(setting_data)
                    elif indicator_type == IndicatrosEnum.RSI.value:
                        setting = RSISetting.from_dict(setting_data)
                    elif indicator_type == IndicatrosEnum.BOLL.value:
                        setting = BOLLSetting.from_dict(setting_data)
                else:
                    # 未知类型，使用基础设置类
                    setting = IndicatorSetting.from_dict(setting_data)
                
                result[indicator_type][int(key_str) if key_str.isdigit() else key_str] = setting
        
        return result
    
    def _init_user_configs_from_defaults(self):
        """从默认配置初始化用户配置"""
        for indicator_type, default_settings in self.default_configs.items():
            self.user_configs[indicator_type] = {}
            for key, setting in default_settings.items():
                # 使用 from_dict 和 to_dict 方法进行深拷贝
                setting_data = setting.to_dict()
                new_setting = setting.__class__.from_dict(setting_data)
                self.user_configs[indicator_type][key] = new_setting
    
    def get_indicator_settings(self, indicator_type: str, id: int = 0) -> Dict:
        """获取指定类型的指标设置"""
        if indicator_type in self.user_configs and id in self.user_configs[indicator_type]:
            return self.user_configs[indicator_type][id]
        elif indicator_type in self.default_configs and id in self.default_configs[indicator_type]:
            return self.default_configs[indicator_type][id]
        else:
            return {}
    
    def set_indicator_settings(self, indicator_type: str, setting: IndicatorSetting, id: int = 0):
        """设置指定类型的指标配置"""
        if indicator_type not in self.user_configs:
            self.user_configs[indicator_type] = {}
        self.user_configs[indicator_type][id] = setting

    # def set_indicator_settings(self, indicator_type: str, settings: Dict, id: int = 0):
    #     """设置指定类型的指标配置"""
    #     if indicator_type not in self.user_configs:
    #         self.user_configs[indicator_type] = {}
        
    #     # 根据indicator_type决定使用哪个类来创建对象
    #     if indicator_type == IndicatrosEnum.MA.value:
    #         setting_obj = MASetting.from_dict(settings)
    #     elif indicator_type == IndicatrosEnum.VOLUME.value:
    #         setting_obj = VolumeSetting.from_dict(settings)
    #     elif indicator_type == IndicatrosEnum.AMOUNT.value:
    #         setting_obj = AmountSetting.from_dict(settings)
    #     elif indicator_type == IndicatrosEnum.MACD.value:
    #         setting_obj = MACDSetting.from_dict(settings)
    #     elif indicator_type == IndicatrosEnum.KDJ.value:
    #         setting_obj = KDJSetting.from_dict(settings)
    #     elif indicator_type == IndicatrosEnum.RSI.value:
    #         setting_obj = RSISetting.from_dict(settings)
    #     elif indicator_type == IndicatrosEnum.BOLL.value:
    #         setting_obj = BOLLSetting.from_dict(settings)
    #     else:
    #         setting_obj = IndicatorSetting.from_dict(settings)
        
    #     self.user_configs[indicator_type][id] = setting_obj
    
    def reset_to_defaults(self, indicator_type: str = None, id: int = None):
        """重置为默认设置"""
        if indicator_type:
            # 重置特定指标类型
            if indicator_type in self.default_configs:
                if id is not None and id in self.default_configs[indicator_type]:
                    # 重置特定ID的设置
                    setting = self.default_configs[indicator_type][id]
                    # 使用 to_dict/from_dict 进行深拷贝
                    setting_data = setting.to_dict()
                    new_setting = setting.__class__.from_dict(setting_data)
                    if indicator_type not in self.user_configs:
                        self.user_configs[indicator_type] = {}
                    self.user_configs[indicator_type][id] = new_setting
                else:
                    # 重置整个指标类型的所有设置
                    self.user_configs[indicator_type] = {}
                    for key, setting in self.default_configs[indicator_type].items():
                        # 使用 to_dict/from_dict 进行深拷贝
                        setting_data = setting.to_dict()
                        new_setting = setting.__class__.from_dict(setting_data)
                        self.user_configs[indicator_type][key] = new_setting
        else:
            # 重置所有指标类型
            self._init_user_configs_from_defaults()
    
    def add_indicator_type(self, indicator_type: str, default_settings: Dict):
        """添加新的指标类型"""
        self.default_configs[indicator_type] = default_settings
        self.user_configs[indicator_type] = {}
        self._init_user_configs_from_defaults()
    
    def get_all_indicator_types(self) -> list:
        """获取所有指标类型"""
        return list(self.default_configs.keys())


# 全局实例
_indicator_config_manager = None

def get_indicator_config_manager() -> IndicatorConfigManager:
    """获取指标配置管理器实例"""
    global _indicator_config_manager
    if _indicator_config_manager is None:
        _indicator_config_manager = IndicatorConfigManager()
    return _indicator_config_manager


# 便捷函数
def load_indicator_configs():
    """加载所有指标配置"""
    manager = get_indicator_config_manager()
    manager.load_default_config()
    manager.load_user_config()


def save_indicator_configs():
    """保存所有指标配置"""
    manager = get_indicator_config_manager()
    manager.save_default_config()
    manager.save_user_config()


def get_ma_settings(id: int = 0) -> Dict:
    """获取均线设置"""
    manager = get_indicator_config_manager()
    return manager.get_indicator_settings(IndicatrosEnum.MA.value, id)


def get_volume_settings(id: int = 0) -> Dict:
    """获取成交量设置"""
    manager = get_indicator_config_manager()
    return manager.get_indicator_settings(IndicatrosEnum.VOLUME.value, id)


def get_macd_settings(id: int = 0) -> Dict:
    """获取MACD设置"""
    manager = get_indicator_config_manager()
    return manager.get_indicator_settings(IndicatrosEnum.MACD.value, id)


def reset_indicator_configs(indicator_type: str = None):
    """重置指标配置"""
    manager = get_indicator_config_manager()
    manager.reset_to_defaults(indicator_type)