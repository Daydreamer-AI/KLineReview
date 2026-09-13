import tushare as ts
import threading
import traceback
import gc
import datetime

from PyQt5.QtCore import QObject, pyqtSignal

from common.common_api import *
from common.config import VERSION

from manager.logging_manager import get_logger
from manager.environment_config_manager import EnvironmentConfigManager
from manager.tushare_stock_data_manager import TuShareStockDataManager



TUSHARE_PRO_API_KEY = "Tushare_Pro_API_KEY"

def singleton(cls):
    """
    一个线程安全的单例装饰器。
    使用双重检查锁模式确保在多线程环境下也只创建一个实例。
    """
    instances = {}  # 用于存储被装饰类的唯一实例
    lock = threading.Lock()  # 创建一个锁对象，用于同步

    def get_instance(*args, **kwargs):
        # 第一次检查（无锁）：如果实例已存在，直接返回，避免绝大多数不必要的锁开销
        if cls not in instances:
            with lock:  # 加锁，确保同一时间只有一个线程能进入下面的代码块
                # 第二次检查（有锁）：防止在等待锁的过程中，已有其他线程创建了实例
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)  # 创建唯一的实例
        return instances[cls]

    return get_instance

# 使用装饰器
@singleton
class TushareProcessor:
    def __init__(self):
        super().__init__() 
        self.logger = get_logger(__name__)

        self.tushare_pro = None
        self._is_initialized = False # 初始化状态标志

        self.df_trade_calendar = None
        self.df_stock_basic_info = None

    def initialize(self) -> bool:
        """显式登录TuShare系统。应在程序开始时调用。"""
        try:
            key_value = EnvironmentConfigManager.get(TUSHARE_PRO_API_KEY)
            # self.logger.info(f"Tushare login successful. API key: {key_value}")

            if key_value == '' or key_value is None: 
                self.logger.info("Tushare login failed. API key is empty.")
                return False

            self.tushare_pro = ts.pro_api(key_value)
            
            # self.logger.info(f"self.tushare_pro type: {type(self.tushare_pro)}, self.tushare_pro: {self.tushare_pro}")

            if self.tushare_pro is not None: 
                self.logger.info("Tushare login successful.")
                self._is_initialized = True

                start_date, end_date = get_year_start_end_dates(-2)
                self.logger.info(f"start_date: {start_date}, end_date: {end_date}")

                formatted_start_date = start_date.replace('-', '')
                formatted_end_date = end_date.replace('-', '')
                # self.update_trade_calendar(formatted_start_date, formatted_end_date)

                self.update_stock_basic_info()

                return True
            else:
                self.logger.info("Tushare login failed.")
                return False
            
        except Exception as e:
            self.logger.info("An error occurred during Tushare login.")
            self.logger.info(f"Traceback: {traceback.format_exc()}")
            return False

    def is_initialized(self) -> bool:
        if not self._is_initialized:
            return False

        if self.tushare_pro is None:
            return False

        return True

    def update_trade_calendar(self, start_date: str, end_date: str):
        """
        更新交易日历。每年1号之后更新
        :param start_date: 开始日期，格式：'20180101'
        :param end_date: 结束日期，格式：'20181231'
        :return: 交易日历列表
        """
        self.logger.info(f"update_trade_calendar--start_date: {start_date}, end_date: {end_date}")

        df_trade_calendar = TuShareStockDataManager().get_trade_calendar()
        if df_trade_calendar is not None and not df_trade_calendar.empty:
            lastest_trade_date = df_trade_calendar['cal_date'].iloc[-1]
            self.logger.info(f"lastest_trade_date: {lastest_trade_date}")
            lastest_trade_date_obj = datetime.datetime.strptime(lastest_trade_date, '%Y%m%d')
            end_date_obj = datetime.datetime.strptime(end_date, '%Y%m%d')
            if lastest_trade_date_obj >= end_date_obj:  # 忽略重复更新
                self.logger.info("Ignoring duplicate update.")
                return True

        if not self.is_initialized():
            self.logger.info("Tushare is not initialized.")
            return False

        # 接口(trade_cal)频率超限(1次/小时)，具体频次详情：https://tushare.pro/document/1?doc_id=108。
        df_trade_calendar = self.tushare_pro.trade_cal(exchange='', start_date=start_date, end_date=start_date)
        if df_trade_calendar is None or df_trade_calendar.empty: 
            self.logger.info("Failed to retrieve trade calendar data.")
            return False

        # df_trade_calendar type: <class 'pandas.DataFrame'>, columns: Index(['exchange', 'cal_date', 'is_open', 'pretrade_date'], dtype='str')
        self.logger.info(f"df_trade_calendar type: {type(df_trade_calendar)}, df_trade_calendar.columns: {df_trade_calendar.columns}, len: {len(df_trade_calendar)}")
        self.logger.info(f"df_trade_calendar head: {df_trade_calendar.head(3)}")
        self.logger.info(f"df_trade_calendar tail: {df_trade_calendar.tail(3)}")

        TuShareStockDataManager().update_trade_calendar(df_trade_calendar)
        self.df_trade_calendar = TuShareStockDataManager().get_trade_calendar()

        TuShareStockDataManager().clear_trade_calendar_db_data()
        TuShareStockDataManager().save_trade_calendar(df_trade_calendar)

        return True

    def update_stock_basic_info(self):

        df_stdf_stock_basic_info = TuShareStockDataManager().get_stock_basic_info()
        if df_stdf_stock_basic_info is not None and not df_stdf_stock_basic_info.empty:
            lastest_update_at = df_stdf_stock_basic_info['update_at'].iloc[-1]
            self.logger.info(f"lastest_update_at: {lastest_update_at}")

            now_date_obj = datetime.datetime.now().date()
            local_lastest_trade_date_obj = datetime.datetime.strptime(lastest_update_at, "%Y-%m-%d").date()
            # 计算时间差并判断是否小于等于 7 天
            # 注意：使用 abs() 取绝对值，防止 local_lastest_date 晚于 query_date 导致负数
            days_diff = abs((now_date_obj - local_lastest_trade_date_obj).days)
            is_within_7_days = days_diff <= 7
            self.logger.info(f"相差天数: {days_diff} 天")
            self.logger.info(f"是否在 7 天内: {is_within_7_days}")
            if is_within_7_days:  # 7天内使用本地数据
                self.logger.info(f"使用本地个股信息数据")
                return True
            

        if not self.is_initialized():
            self.logger.info("Tushare is not initialized.")
            return False

        # 接口(stock_basic)频率超限(1次/小时)，具体频次详情：https://tushare.pro/document/1?doc_id=108。
        df_stock_basic_info = self.tushare_pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,market,list_date')
        if df_stock_basic_info is None or df_stock_basic_info.empty: 
            self.logger.info("Failed to retrieve stock basic info data.")
            return False

        df_stock_basic_info['version'] = VERSION
        # result['update_at'] = str_query_date

        # df_stock_basic_info type: <class 'pandas.DataFrame'>, columns: Index(['ts_code', 'symbol', 'name', 'area', 'industry', 'market', 'list_date'], dtype='str'), len: 5562
        self.logger.info(f"df_stock_basic_info type: {type(df_stock_basic_info)}, columns: {df_stock_basic_info.columns}, len: {len(df_stock_basic_info)}")

        self.logger.info(f"df_stock_basic_info head: {df_stock_basic_info.head(3)}")
        self.logger.info(f"df_stock_basic_info tail: {df_stock_basic_info.tail(3)}")

        TuShareStockDataManager().update_stock_basic_info(df_stock_basic_info)
        self.df_stock_basic_info = TuShareStockDataManager().get_stock_basic_info()

        TuShareStockDataManager().clear_stock_basic_info_db_data()
        TuShareStockDataManager().save_stock_basic_info(df_stock_basic_info)

        return True

    
        
