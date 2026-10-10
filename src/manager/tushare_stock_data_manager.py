
import threading
from manager.logging_manager import get_logger

from db_base.tushare_stock_basic_info_db import TuShareStockBasicInfoDB

class TuShareStockDataManager:
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TuShareStockDataManager, cls).__new__(cls)
        return cls._instance
    def __init__(self):
        self.logger = get_logger(__name__)

        self.lock = threading.Lock()

        self.df_trade_calendar = None

        self.df_stock_basic_info = {}            
        self.dict_code_name = None      # {code : name}，按需构建的“个股代码-名称”映射缓存
        self.dict_name_code = None            # {name : code}，按需构建的“个股名称-代码”映射缓存

        self.stock_basic_info_db = TuShareStockBasicInfoDB()
        self._init_data()

    def _init_data(self):
        df_trade_calendar = self.query_lastest_trade_calendar()
        df_stock_basic_info = self.query_lastest_stock_basic_info()

        with self.lock:
            self.df_trade_calendar = df_trade_calendar
            self.df_stock_basic_info = df_stock_basic_info

    def get_trade_calendar(self):
        with self.lock:
            return self.df_trade_calendar

    def get_stock_basic_info(self):
        with self.lock:
            return self.df_stock_basic_info

    def update_trade_calendar(self, df_trade_calendar):
        with self.lock:
            self.df_trade_calendar = df_trade_calendar

    def update_stock_basic_info(self, df_stock_basic_info):
        with self.lock:
            self.df_stock_basic_info = df_stock_basic_info

    def get_code_name_dict(self, code_column_name='ts_code', name_column_name='name'):
        """从本地股票信息库同步构建 {code: name} 映射（不依赖后台日线缓存）。
    
        供复盘随机选股及后续需要“个股代码-名称”的功能使用；结果按需缓存。
        """
        if self.dict_code_name is not None:
            return self.dict_code_name

        with self.lock:
            dict_stocks_info = self.df_stock_basic_info

        dict_code_name = {}
        for index, row in dict_stocks_info.iterrows():
            dict_code_name[row[code_column_name]] = row[name_column_name]

        with self.lock:
            self.dict_code_name = dict_code_name

        return dict_code_name

    def get_name_code_dict(self, code_column_name='ts_code', name_column_name='name'):
            """从本地股票信息库同步构建 {code: name} 映射（不依赖后台日线缓存）。
    
            供复盘随机选股及后续需要“个股代码-名称”的功能使用；结果按需缓存。
            """
            if self.dict_name_code is not None:
                return self.dict_name_code
    
            with self.lock:
                df_stock_basic_info = self.df_stock_basic_info
    
            dict_name_code = {}
            for index, row in df_stock_basic_info.iterrows():
                dict_name_code[row[name_column_name]] = row[code_column_name]

            with self.lock:
                self.dict_name_code = dict_name_code
            return dict_name_code

    def get_code_name_complete_list(self):
        """获取所有股票代码-名称列表。

        Returns:
            list: 所有股票代码-名称列表，如：["600000.SH - 浦发银行", "000001.SZ - 平安银行"]。
        """
        list_result = []
        dict_code_name = self.get_code_name_dict()
        for code, name in dict_code_name.items():
            list_result.append(f"{code} - {name}")
        return list_result

    def get_complete_text(self, code, name):
        return f"{code} - {name}"

    def parse_code_name_by_complete_text(self, complete_text: str):
        """从完整的股票代码-名称字符串中解析出股票代码。

        Args:
            complete_text (str): 完整的股票代码-名称字符串，如："600000 - 浦发银行"。

        Returns:
            list: 股票代码名称list，如：["600000", "浦发银行"]。
        """
        if not complete_text:
            return None

        code_name_list = complete_text.split(' - ')
        return code_name_list

    # ====================================================数据库接口===============================================================
    def save_trade_calendar(self, trade_calendar_data):
        return self.stock_basic_info_db.save_trade_calendar(trade_calendar_data)

    def query_lastest_trade_calendar(self):
        return self.stock_basic_info_db.query_lastest_trade_calendar()

    def clear_trade_calendar_db_data(self):
        self.stock_basic_info_db.clear_trade_calendar_db_data()

    def save_stock_basic_info(self, stock_basic_info_data):
        return self.stock_basic_info_db.save_stock_basic_info(stock_basic_info_data)

    def query_lastest_stock_basic_info(self):
        return self.stock_basic_info_db.query_lastest_stock_basic_info()

    def clear_stock_basic_info_db_data(self):
        self.stock_basic_info_db.clear_stock_basic_info_db_data()

