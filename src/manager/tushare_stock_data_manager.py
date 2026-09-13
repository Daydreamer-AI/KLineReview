
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
        self.dict_stock_code_name = None      # {code : name}，按需构建的“个股代码-名称”映射缓存
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

