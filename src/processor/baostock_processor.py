import baostock as bs
import pandas as pd
import numpy as np
from db_base.stock_info_db_base import StockInfoDBBasePool
from db_base.stock_db_base import StockDbBase
from indicators import stock_data_indicators as sdi
import random
import time
import datetime
import threading
from datetime import date, timedelta
from manager.config_manager import ConfigManager
from common.common_api import *
from manager.logging_manager import get_logger
import traceback
import gc

from PyQt5.QtWidgets import QApplication

from PyQt5.QtCore import QObject, pyqtSignal

from thread.base_thread_worker import BaseThreadWorker

import json

from manager.bao_stock_data_manager import BaostockDataManager
from manager.period_manager import TimePeriod

from thread.task_pool import get_default_task_pool

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
class BaoStockProcessor(QObject):

    sig_stock_data_load_finished = pyqtSignal(object)
    sig_stock_data_load_error = pyqtSignal(str)
    sig_stock_data_load_progress = pyqtSignal(str)

    def __init__(self):
        super().__init__() 
        self.logger = get_logger(__name__)

        self.b_stop_process = False
        self.lock = threading.Lock()  
        self._is_initialized = False # 初始化状态标志

    def initialize(self) -> bool:
        """显式登录Baostock系统。应在程序开始时调用。"""
        try:
            self.init_config()

            return self.init_baostock_login()
            
        except Exception as e:
            self.logger.info("An error occurred during Baostock login.")
            self.logger.info(f"Traceback: {traceback.format_exc()}")
            return False
        
    def init_config(self):
        pass

    def init_baostock_login(self):
        self.logger.info("登录Baostock系统")
        lg = bs.login()
        # 显示登陆返回信息
        self.logger.info('login respond error_code:'+lg.error_code)
        self.logger.info('login respond  error_msg:'+lg.error_msg)

        if lg.error_code == '0':
            self._is_initialized = True
            self.logger.info("Baostock login successful.")

            self.df_trade_dates = self.get_current_trade_dates()
            if self.is_trading_day_today():
                self.logger.info("今天是交易日")
                # self.can_update_today_data()
            else:
                self.logger.info("今天不是交易日")
            
            return True
        else:
            self.logger.info(f"Baostock login failed: {lg.error_msg}")
            return False

    def cleanup(self) -> None:
        """显式登出Baostock系统。应在程序结束时调用。"""
        if self._is_initialized:
            try:
                bs.logout()
                self.logger.info("Baostock logged out successfully.")
            except Exception as e:
                # 此时发生异常可能由于解释器正在关闭，记录警告即可
                self.logger.info(f"Baostock logout encountered an error (may be during shutdown): {e}")
            finally:
                self._is_initialized = False

    def start_background_loading(self):
        """启动后台加载本地Baostock股票数据"""
        try:
            # 创建并启动工作线程来执行特定任务
            self.load_worker = BaseThreadWorker(BaoStockProcessor().load_all_local_stock_data)
            self.load_worker.finished.connect(self.slot_stock_data_loading_finished)
            self.load_worker.progress.connect(self.slot_stock_data_loading_progress)
            self.load_worker.error.connect(self.slot_stock_data_loading_error)
            self.load_worker.start()
            
            self.logger.info("已启动后台加载本地Baostock股票数据")
        except Exception as e:
            self.logger.error(f"启动后台加载本地Baostock股票数据失败: {e}")

    def load_all_local_stock_data(self):
        """
        遍历所有股票代码并进行处理
        """
        return BaostockDataManager().load_1d_local_stock_data()
    

    # --------------------------------------------------------------------

    def get_current_year_dates(self):
        """
        获取当前年份的起始和结束日期
        
        Returns:
            tuple: (start_date, end_date) 格式为 "YYYY-MM-DD"
        """
        current_year = datetime.datetime.now().year
        start_date = f"{current_year}-01-01"
        end_date = f"{current_year}-12-31"
        return start_date, end_date

    # 获取当年交易日信息
    def get_current_trade_dates(self):

        #### 获取交易日信息 ####
        start_date, end_date = self.get_current_year_dates()
        rs = bs.query_trade_dates(start_date=start_date, end_date=end_date)
        self.logger.info('query_trade_dates respond error_code:'+rs.error_code)
        self.logger.info('query_trade_dates respond  error_msg:'+rs.error_msg)

        #### 打印结果集 ####
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)

        #### 结果集输出到csv文件 ####   
        # result.to_csv("D:\\trade_datas.csv", encoding="gbk", index=False)
        # self.logger.info("2025年交易日：", result)

        return result

    def is_trading_day(self, day_str=''):
        if day_str == '':
            day_str = datetime.datetime.now().strftime('%Y-%m-%d')

        if day_str in self.df_trade_dates['calendar_date'].values:
            trading_status = self.df_trade_dates.loc[self.df_trade_dates['calendar_date'] == day_str, 'is_trading_day'].iloc[0]
            return trading_status == '1'
        else:
            return False # 或者根据你的需求返回 None 或抛出异常

    # 判断当天是否是交易日
    def is_trading_day_today(self):
        today_str = datetime.datetime.now().strftime('%Y-%m-%d')
        return self.is_trading_day(today_str)

    # 判断能否更新当天交易数据
    def can_update_today_data(self):
        # 获取当前日期和时间
        now = datetime.datetime.now()

        # 创建今天17:30的datetime对象
        target_datetime = datetime.datetime(now.year, now.month, now.day, 18, 00)

        # 直接比较
        if now > target_datetime:
            # self.logger.info("当前时间在17:30之后")
            return True
        else:
            # self.logger.info("当前时间在17:30之前或等于20:30")
            return False

    def count_fridays_since(self, specific_date_str):
        """
        计算从指定日期到今天之间有多少个星期五。

        参数:
        specific_date_str (str): 字符串格式的日期，期望格式为 "YYYY-MM-DD"，例如 "2025-08-29"。

        返回:
        int: 星期五的数量。
        """
        try:
            # 1. 将字符串转换为日期对象
            specific_date = datetime.datetime.strptime(specific_date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("日期格式错误，请使用 'YYYY-MM-DD' 格式。")

        # 2. 获取今天的日期
        today = date.today()

        # 确保输入的日期不晚于今天
        if specific_date > today:
            return 0

        # 3. 初始化计数器
        friday_count = 0
        # 4. 循环遍历从指定日期到今天的每一天
        current_date = specific_date
        while current_date <= today:
            # 5. 判断当前日期是否为星期五 (Monday=0, Sunday=6)
            if current_date.weekday() == 4:
                friday_count += 1
            # 6. 移动到下一天
            current_date += timedelta(days=1)

        return friday_count
    
    def count_trading_days(self, s_begin_date, s_end_date=None):
        '''计算指定日期范围内的交易日天数'''
        try:
            # 1. 将字符串转换为日期对象
            start_date = datetime.datetime.strptime(s_begin_date, '%Y-%m-%d').date()
            
            # 如果未指定结束日期，则使用今天
            if s_end_date is None:
                end_date = date.today()
            else:
                end_date = datetime.datetime.strptime(s_end_date, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("日期格式错误，请使用 'YYYY-MM-DD' 格式。")

        # 确保日期合理
        if end_date < start_date:
            return 0
        
        # 确保交易日数据已加载
        if not hasattr(self, 'df_trade_dates') or self.df_trade_dates is None:
            self.logger.warning("交易日数据未初始化，返回0")
            return 0
        
        # 筛选指定日期范围内的交易日
        mask = (
            (pd.to_datetime(self.df_trade_dates['calendar_date']).dt.date >= start_date) &
            (pd.to_datetime(self.df_trade_dates['calendar_date']).dt.date <= end_date) &
            (self.df_trade_dates['is_trading_day'] == '1')
        )
        
        return len(self.df_trade_dates[mask])
        

    # 日线全量更新
    def process_daily_stock_data(self, code, start_date=None, end_date=None):
        if start_date == None or end_date == None:
            # 默认计算近3年的日期范围
            end_date = (datetime.datetime.now()).strftime("%Y-%m-%d")
            start_date = (datetime.datetime.now() - datetime.timedelta(days=365*3)).strftime("%Y-%m-%d")
            # self.logger.info(f"获取股票 {stock_code} 数据，时间范围：{start_date} 至 {end_date}")
        
        # sleep_time = random.uniform(0.1, 0.3)
        # time.sleep(sleep_time)

        with self.lock:
            rs = bs.query_history_k_data_plus(code,
                "date,code,open,high,low,close,volume,amount,pctChg,turn,adjustflag",
                start_date=start_date, end_date=end_date,
                frequency="d", adjustflag="2")
        # self.logger.info(rs.error_code)      # 0
        # self.logger.info(rs.error_msg)       # success
        # self.logger.info("rs的类型：", type(rs))       # <class 'baostock.data.resultset.ResultData'>

        # 获取具体的信息
        result_list = []
        while (rs.error_code == '0') & rs.next():
            # 分页查询，将每页信息合并在一起
            result_list.append(rs.get_row_data())

        # self.logger.info("result_list的类型：", type(result_list))     # <class 'list'>
        new_columns = ['date', 'code', 'open', 'high', 'low', 'close', 'volume', 'amount', 'change_percent', 'turnover_rate', 'adjustflag']
        result = pd.DataFrame(result_list, columns=new_columns)

        BaostockDataManager().data_type_conversion(result)

        result = result.dropna()

        return result

    def process_and_save_daily_stock_data(self, code):
        result = pd.DataFrame()

        if not BaostockDataManager().check_stock_db_exists(code) or not BaostockDataManager().check_table_exists(code, TimePeriod.DAY):
            # self.logger.info(f"{code}.db 不存在，即将从Baostock获取")
            result = self.process_daily_stock_data(code)

            # 指标不再入库，使用时按需计算
            if not result.empty:

                BaostockDataManager().save_stock_data_to_db(code, result, 'replace', TimePeriod.DAY)
        else:
            # self.logger.info(f"{code}.db 存在，即将从本地数据库更新")
            result, data_to_save = self.update_daily_stock_data(code)
            if data_to_save is not None and not data_to_save.empty:
                BaostockDataManager().save_stock_data_to_db(code, data_to_save, "append",TimePeriod.DAY)

        # sleep_time = random.uniform(0.1, 0.3)
        # time.sleep(sleep_time)
        
        return result
       
    # 增量维护，收盘后调用
    def update_daily_stock_data(self, code):
        day_stock_data = pd.DataFrame()
        data_to_save = pd.DataFrame()
        if not BaostockDataManager().check_stock_db_exists(code):
            self.logger.info(f"{code}.db 不存在", code)
            return day_stock_data, data_to_save

        # 步骤一：得到当前数据库中的股票数据
        day_stock_data = BaostockDataManager().get_stock_data_from_db_by_period(code, TimePeriod.DAY)
        # self.logger.info("code: ", code)
        # self.logger.info("day_stock_data的类型：", type(day_stock_data))
        # self.logger.info(day_stock_data.tail(1))
        if day_stock_data is None or day_stock_data.empty:
            self.logger.info("day_stock_data为空")
            return day_stock_data, data_to_save

        # 判断是否存在空值
        if day_stock_data.isnull().values.any():
            # self.logger.info("存在空值")
            # 获取所有包含空值的行
            rows_with_nulls = day_stock_data[day_stock_data.isnull().any(axis=1)]
            # self.logger.info("\n所有包含空值的行:")
            # self.logger.info(rows_with_nulls)
            
            # 提取第一个包含空值的行（按索引顺序）
            first_row_with_null = rows_with_nulls.iloc[0]
            # self.logger.info("\n第一个包含空值的行:")
            # self.logger.info(first_row_with_null)

            null_data_code = first_row_with_null['code']
            # self.logger.info(f"第一个包含空值行的股票代码: {null_data_code}")
            first_null_date = first_row_with_null['date']
            # self.logger.info("第一个包含空值的行日期类型是: ", type(first_null_date))  # <class 'str'>
            # self.logger.info(f"第一个包含空值的行日期是: {first_null_date}")
    
        now_date = datetime.datetime.now().strftime("%Y-%m-%d")
        if now_date in day_stock_data['date'].values:
            # self.logger.info("已是最新日线数据")
            return day_stock_data, data_to_save
        
        last_date = None
        if day_stock_data.empty or day_stock_data is None:
            self.logger.info("数据库表为空，默认获取近3年股票数据")
            last_date = (datetime.datetime.now() - datetime.timedelta(days=365*3)).strftime("%Y-%m-%d")
        else:
            last_date = day_stock_data['date'].iloc[-1]
        # self.logger.info("最后日期（方法2）:", last_date) 

        parsed_date = datetime.datetime.strptime(last_date, "%Y-%m-%d")  # 解析为日期对象
        last_date = parsed_date + datetime.timedelta(days=1)

        # 获取数据库中最后日期至今的股票数据
        start_date = last_date.strftime("%Y-%m-%d")               # Baostock要求的日期格式
        end_date = (datetime.datetime.now()).strftime("%Y-%m-%d")   #  + datetime.timedelta(days=1)
        # self.logger.info(f"获取股票 {code} 数据，时间范围：{start_date} 至 {end_date}")
        
        # 判断数据库最后日期至今有无交易日数据需更新
        if self.is_trading_day_today():
            # 交易日18:00后才能更新当天数据
            if not self.can_update_today_data():
                # self.logger.info("今天不是交易日，未到数据更新时间，请稍后再试")
                # return day_stock_data, data_to_save

                # 判断昨日数据是否已存在，不存在则更新昨日数据
                yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                if yesterday in day_stock_data['date'].values:
                    # self.logger.info("昨日及之前数据已存在，直接返回现有数据")
                    return day_stock_data, data_to_save
        else:
            # self.logger.info("今天不是交易日，判断数据库中是否是最新数据")
            trading_day_count = self.count_trading_days(start_date, end_date)
            # self.logger.info(f"交易日数量：{trading_day_count}")
            if trading_day_count == 0:
                # self.logger.info("数据库中已是最新数据，直接返回现有数据")
                return day_stock_data, data_to_save

        
        df_new_stock_data = self.process_daily_stock_data(code, start_date, end_date)
        # 判断获取到的数据是否存在空值
        # if df_new_stock_data.isnull().values.any():
        #     self.logger.info(f"股票 {code} 的数据存在空值")
        #     return day_stock_data, data_to_save
        # if df_new_stock_data.empty:
        #     self.logger.info("process_daily_stock_data执行结果为空！")
        #     return day_stock_data, data_to_save
        
        # self.logger.info("获取到的新数据：")
        # self.logger.info(df_new_stock_data)

        df_new_stock_data = df_new_stock_data.dropna()

        if not df_new_stock_data.empty:
            # 处理空 DataFrame 的情况
            if day_stock_data.empty:
                combined_df = df_new_stock_data.copy()
                self.logger.info("原数据为空，直接使用新获取的数据")
            else:
                # BaostockDataManager().data_type_conversion(df_new_stock_data)
                # 合并计算指标
                combined_df = pd.concat([day_stock_data, df_new_stock_data], axis=0, ignore_index=True)

            # 指标数据不再入库
            data_to_save = combined_df.tail(len(df_new_stock_data))

            return combined_df, data_to_save
        
        return day_stock_data, data_to_save


    # 空值修复，暂无用
    def fix_null_value(self, code, data_to_save):
        pass

    # 周线全量更新
    def process_weekly_stock_data(self, code, start_date=None, end_date=None):
        if start_date == None or end_date == None:
            # 默认计算近3年的日期范围（周线数据通常需要更长时间来计算指标）
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
            # end_date = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
            start_date = (datetime.datetime.now() - datetime.timedelta(days=365*3)).strftime("%Y-%m-%d")

        # self.logger.info(f"获取股票 {code} 周线数据，时间范围：{start_date} 至 {end_date}")
        
        # sleep_time = random.uniform(0.1, 0.2) # 等待时间可以设得稍长一些
        # time.sleep(sleep_time)

        with self.lock:
            rs = bs.query_history_k_data_plus(code,
                "date,code,open,high,low,close,volume,amount,pctChg,turn,adjustflag",
                start_date=start_date, end_date=end_date,
                frequency="w", adjustflag="2")
        # self.logger.info(rs.error_code)      # 0
        # self.logger.info(rs.error_msg)       # success
        # self.logger.info("rs的类型：", type(rs))       # <class 'baostock.data.resultset.ResultData'>

        # 获取具体的信息
        result_list = []
        while (rs.error_code == '0') & rs.next():
            # 分页查询，将每页信息合并在一起
            result_list.append(rs.get_row_data())

        # self.logger.info("result_list的类型：", type(result_list))     # <class 'list'>
        chinese_columns = ['date', 'code', 'open', 'high', 'low', 'close', 'volume', 'amount', 'change_percent', 'turnover_rate', 'adjustflag']
        result = pd.DataFrame(result_list, columns=chinese_columns)

        BaostockDataManager().data_type_conversion(result)

        result = result.dropna()

        # self.logger.info("process_weekly_stock_data执行结果：")
        # self.logger.info(result.tail(3))

        return result

    def process_and_save_weekly_stock_data(self, code):
        result = pd.DataFrame()
        if not BaostockDataManager().check_stock_db_exists(code) or not BaostockDataManager().check_table_exists(code, TimePeriod.WEEK):
            self.logger.info(f"周线 {code}.db 不存在，即将从Baostock获取")
            result = self.process_weekly_stock_data(code)

            if not result.empty:
                BaostockDataManager().save_stock_data_to_db(code, result, 'replace', TimePeriod.WEEK)
        else:
            # self.logger.info(f"周线 {code}.db 存在，即将从本地数据库更新")
            result, data_to_save = self.update_weekly_stock_data(code)
            if data_to_save is not None and not data_to_save.empty:
                BaostockDataManager().save_stock_data_to_db(code, data_to_save, "append", TimePeriod.WEEK)

        # sleep_time = random.uniform(0.1, 0.3)
        # time.sleep(sleep_time)
        return result

    # 增量维护，周线数据不好增量维护，追加后原表中还会存在周中数据。建议：每周末（或本周收盘后）调用一次更新本周周线数据
    # 例如：周二第一次update，表中会存在周二时的周线数据，当周线再update时，周二数据（已过时）依旧会在表中。
    # 补充：周线接口只能每周最后一个交易日才可以获取，月线每月最后一个交易日才可以获取。
    def update_weekly_stock_data(self, code):
        week_stock_data = pd.DataFrame()
        data_to_save = pd.DataFrame()
        if not BaostockDataManager().check_stock_db_exists(code):
            self.logger.info(f"{code}.db 不存在")
            return week_stock_data, data_to_save

        # 步骤一：得到当前数据库中的股票数据
        week_stock_data = BaostockDataManager().get_stock_data_from_db_by_period(code, TimePeriod.WEEK)

        # self.logger.info(f"获取到的周线数据长度：{len(week_stock_data)}")
        week_stock_data = week_stock_data.dropna()
        # self.logger.info(f"dropna后的周线数据长度：{len(week_stock_data)}")
        # 手动检查可疑数据
        # for col in week_stock_data.columns:
        #     if week_stock_data[col].isnull().any():
        #         self.logger.info(f"列 {col} 包含空值")
        #         self.logger.info(f"空值位置: {week_stock_data[col].isnull()}")

        if week_stock_data is None or week_stock_data.empty:
            self.logger.info(f"{code}.db 中无周线数据")
            return week_stock_data, data_to_save
        
        # 最后一行数据日期 + 1，至今有几个周五？一个也没有说明是最新数据，无需更新。
        # now_date = datetime.datetime.now().strftime("%Y-%m-%d")
        # if now_date in week_stock_data['date'].values:
        #     self.logger.info("已是最新数据")
        #     return week_stock_data, data_to_save
        last_date = week_stock_data['date'].iloc[-1]
        parsed_date = datetime.datetime.strptime(last_date, "%Y-%m-%d")  # 解析为日期对象
        last_date = parsed_date + datetime.timedelta(days=1)
        num_fridays = self.count_fridays_since(last_date.strftime("%Y-%m-%d"))
        if not num_fridays > 0:
            # self.logger.info("已是最新周线数据")
            return week_stock_data, data_to_save
        
        # 判断今天是否周五，数据库最后日期到今天有周五存在，但今天不是周五，则可以获取之前的周数据
        current_date = datetime.datetime.now()
        if current_date.weekday() != 5:
            pass
        elif self.is_trading_day_today():
            # 交易日17:30后才能更新当天数据
            if not self.can_update_today_data():
                self.logger.info("交易日18:00后才能更新数据！")
                return week_stock_data, data_to_save
        
        last_date = week_stock_data['date'].iloc[-1]
        # self.logger.info("最后周线日期:", last_date) 

        parsed_date = datetime.datetime.strptime(last_date, "%Y-%m-%d")  # 解析为日期对象
        last_date = parsed_date + datetime.timedelta(days=1)
        # self.logger.info(last_date.strftime("%Y-%m-%d"))

        # 步骤二：获取数据库中最后日期至今的股票数据
        start_date = last_date.strftime("%Y-%m-%d")               # Baostock要求的日期格式
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")

        df_new_weekly_stock_data = self.process_weekly_stock_data(code, start_date, end_date)

        df_new_weekly_stock_data = df_new_weekly_stock_data.dropna()

        if df_new_weekly_stock_data is not None and not df_new_weekly_stock_data.empty:
            if not week_stock_data.empty:
                # 合并计算指标
                combined_df = pd.concat([week_stock_data, df_new_weekly_stock_data], axis=0, ignore_index=True)
            else:
                combined_df = df_new_weekly_stock_data.copy()
                self.logger.info("原数据为空，直接使用新获取的数据")

            data_to_save = combined_df.tail(len(df_new_weekly_stock_data))
        
        return week_stock_data, data_to_save
    
    # 分钟级数据获取接口
    def process_and_save_minute_level_stock_data(self, code, level='30'):
        result = pd.DataFrame()

        allowed_levels = ['1', '3', '5', '10', '15', '30', '45', '60', '90', '120']
        if level not in allowed_levels:
            self.logger.info(f"Invalid level: {level}")
            return result

        time_period = TimePeriod.from_minute_number_label(level)

        if not BaostockDataManager().check_stock_db_exists(code) or not BaostockDataManager().check_table_exists(code, time_period):
            # self.logger.info(f"分钟级 {code}.db 不存在，即将从Baostock获取")
            result = self.process_minute_level_stock_data(code, level)

            if result is not None and not result.empty:
                BaostockDataManager().save_stock_data_to_db(code, result, 'replace', time_period)
        else:
            # self.logger.info(f"分钟级 {code}.db 存在，即将从本地数据库更新")
            result, data_to_save = self.update_minute_level_stock_data(code, level)
            if data_to_save is not None and not data_to_save.empty:
                BaostockDataManager().save_stock_data_to_db(code, data_to_save, "append", time_period)

        return result

    def process_minute_level_stock_data(self, code, level = '1', start_date=None, end_date=None):
        result = pd.DataFrame()
        allowed_levels = ['1', '3', '5', '10', '15', '30', '45', '60', '90', '120']
        if level not in allowed_levels:
            self.logger.info(f"Invalid level: {level}")
            return result
        
        # 1分钟只能获取近3个月数据，其他分钟级别只能获取近1年的数据
        if start_date == None or end_date == None:
            # 默认计算近3年的日期范围（周线数据通常需要更长时间来计算指标）
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
            # end_date = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")

            if level == '1':
                start_date = (datetime.datetime.now() - datetime.timedelta(days=3*30)).strftime("%Y-%m-%d")
            else:
                current_year = datetime.datetime.now().year
                start_date = f"{current_year}-01-01"

        # self.logger.info(f"获取股票 {code} 分钟级数据，时间范围：{start_date} 至 {end_date}")
        
        # sleep_time = random.uniform(0.1, 0.2)
        # time.sleep(sleep_time)

        with self.lock:
            rs = bs.query_history_k_data_plus(code,
                "date,time,code,open,high,low,close,volume,amount,adjustflag",
                start_date=start_date, end_date=end_date,
                frequency=level, adjustflag="2")


        result_list = []
        while (rs.error_code == '0') & rs.next():

            result_list.append(rs.get_row_data())

        if result_list is None or result_list == []:
            return result

        rename_columns = ['date', 'time', 'code', 'open', 'high', 'low', 'close', 'volume', 'amount', 'adjustflag']
        result = pd.DataFrame(result_list, columns=rename_columns)


        # if result is not None and not result.empty:
        #     last_row = result.tail(1)
        #     if not last_row.empty:
        #         time_value = last_row['time'].iloc[0]  # 使用 iloc[0] 获取第一个元素
        #         self.logger.info(f"time列的类型：{last_row['time'].dtype}, {type(time_value)}")   # object, <class 'str'>


        BaostockDataManager().data_type_conversion(result)

        # if result is not None and not result.empty:
        #     sdi.default_indicators_auto_calculate(result)

        result = result.dropna()

        return result
    
    def update_minute_level_stock_data(self, code, level='30'):
        result = pd.DataFrame()
        data_to_save = pd.DataFrame()
        if not BaostockDataManager().check_stock_db_exists(code):
            self.logger.info("{stock_code}.db 不存在", code)
            return result, data_to_save
        
        allowed_levels = ['1', '3', '5', '10', '15', '30', '45', '60', '90', '120']
        if level not in allowed_levels:
            return result, data_to_save
        
        time_period = TimePeriod.from_minute_number_label(level)

        # 步骤一：得到当前数据库中的股票数据
        minute_stock_data = BaostockDataManager().get_stock_data_from_db_by_period(code, time_period)
        if minute_stock_data is None or minute_stock_data.empty:
            self.logger.info("minute_stock_data为空")
            return result, data_to_save

        # 判断是否存在空值
        if minute_stock_data.isnull().values.any():
            self.logger.info("存在空值")
            # minute_stock_data = minute_stock_data.dropna()
        

        # 因为分钟级也只能按天获取，因此不用小时、分级的判断
        now_date = datetime.datetime.now().strftime("%Y-%m-%d")
        if now_date in minute_stock_data['date'].values:
            # self.logger.info("已是最新日线数据")
            return minute_stock_data, data_to_save
        
        last_date = None
        if minute_stock_data.empty or minute_stock_data is None:
            # self.logger.info("数据库表为空，默认获取近1年股票数据")
            if level == '1':
                last_date = (datetime.datetime.now() - datetime.timedelta(days=3*30)).strftime("%Y-%m-%d")
            else:
                # last_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
                current_year = datetime.datetime.now().year
                last_date = f"{current_year}-01-01"
        else:
            last_date = minute_stock_data['date'].iloc[-1]
        # self.logger.info("最后日期（方法2）:", last_date) 

        parsed_date = datetime.datetime.strptime(last_date, "%Y-%m-%d")  # 解析为日期对象
        last_date = parsed_date + datetime.timedelta(days=1)

        # 获取数据库中最后日期至今的股票数据
        start_date = last_date.strftime("%Y-%m-%d")               # Baostock要求的日期格式
        end_date = (datetime.datetime.now()).strftime("%Y-%m-%d")   
        # self.logger.info(f"获取股票 {code} 数据，时间范围：{start_date} 至 {end_date}")
        
        # 判断数据库最后日期至今有无交易日数据需更新
        if self.is_trading_day_today():
            # 交易日18:00后才能更新当天数据
            if not self.can_update_today_data():
                # self.logger.info("今天不是交易日，未到数据更新时间，请稍后再试")
                # return minute_stock_data, data_to_save

                # 判断昨日数据是否已存在，不存在则更新昨日数据
                yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                if yesterday in minute_stock_data['date'].values:
                    # self.logger.info("昨日及之前数据已存在，直接返回现有数据")
                    return minute_stock_data, data_to_save
        else:
            # self.logger.info("今天不是交易日，判断数据库中是否是最新数据")
            trading_day_count = self.count_trading_days(start_date, end_date)
            # self.logger.info(f"交易日数量：{trading_day_count}")
            if trading_day_count == 0:
                # self.logger.info("数据库中已是最新数据，直接返回现有数据")
                return minute_stock_data, data_to_save

        
        df_new_stock_data = self.process_minute_level_stock_data(code, level, start_date, end_date)

        df_new_stock_data = df_new_stock_data.dropna()
        
        if df_new_stock_data is not None and not df_new_stock_data.empty:
            # 处理空 DataFrame 的情况
            if minute_stock_data.empty:
                combined_df = df_new_stock_data.copy()
                self.logger.info("原数据为空，直接使用新获取的数据")
            else:
                BaostockDataManager().data_type_conversion(df_new_stock_data)
                # 合并计算指标
                combined_df = pd.concat([minute_stock_data, df_new_stock_data], axis=0, ignore_index=True)

            data_to_save = combined_df.tail(len(df_new_stock_data))

            return combined_df, data_to_save

        return minute_stock_data, data_to_save

    # ------------------------------------------数据更新接口--------------------------------------------
    def get_chinese_board_name(self, board_name):
        if board_name == 'sh_main':
            return '沪市主板'
        elif board_name == 'sz_main':
            return '深市主板'
        elif board_name == 'gem':
            return '创业板'
        elif board_name == 'star':
            return '科创板'
        elif board_name == 'bse':
            return '北交所'
        else:
            return '其他'

    def process_stock_data(self, board_name='sh_main', TimePeriod=TimePeriod.DAY, task=None):
        allowed_board_names = ['sh_main', 'sz_main', 'gem', 'star', 'bse']
        if board_name not in allowed_board_names:
            self.logger.info(f"无效的板块名称: {board_name}")
            return

        i = 1
        board_name_chinese = self.get_chinese_board_name(board_name)
        time_period_name_chinese = TimePeriod.get_chinese_label(TimePeriod)
        self.logger.info(f"开始处理 {board_name_chinese} {time_period_name_chinese} 股票数据...")
        start_time = time.time()  # 记录开始时间

        dict_stock_info = BaostockDataManager().get_stock_info_dict()
        for index, row in dict_stock_info[board_name].iterrows():
            if task:
                # 检查暂停状态
                task._check_pause()
                
                # 检查取消状态
                if task.is_cancelled():
                    break

            value = row['证券代码']
            stock_name = row['证券名称'] if '证券名称' in row else '未知'
            # self.logger.info(f"获取第 {i} 只{board_name_chinese}股票 {value} 【{time_period_name_chinese}】数据")

            result = None
            if TimePeriod == TimePeriod.DAY:
                result = self.process_and_save_daily_stock_data(value)
            elif TimePeriod == TimePeriod.WEEK:
                result = self.process_and_save_weekly_stock_data(value)

            if result is None or result.empty:
                # self.logger.info(f"股票 {value} 数据获取失败")
                continue

            # if i > 3:
            #     self.logger.info(f"已获取到所有{board_name_chinese}股票{time_period_name_chinese}数据, i: {i}")
            #     break

            
            if i % 100 == 0:  # 每100只股票打印一次日志
                self.logger.info(f"已处理 {i} 只{board_name_chinese}股票【{time_period_name_chinese}】数据")

            i += 1

            del result

        process_elapsed_time = time.time() - start_time  # 计算耗时
        self.logger.info(f"{board_name_chinese} {time_period_name_chinese}股票数据处理完成，共处理{i}只股票，耗时: {process_elapsed_time:.2f}秒，即{process_elapsed_time/60:.2f}分钟")

        # 批处理完成后强制垃圾回收
        gc.collect()

    
    def auto_process_all_stock_data(self):
        # 一键自动 获取/更新 沪、深主板 日线、周线、15、30、60分钟k线数据
        from thread.baostock_data_fetch_task import BaostockDataFetchTask
        baostock_data_fetch_task = BaostockDataFetchTask()
        baostock_data_fetch_task.task_completed.connect(self.slot_baostock_data_fetch_task_completed)
        task_id = get_default_task_pool().submit(baostock_data_fetch_task)

    # -----------------沪市主板股票数据获取接口---------------------
    def start_sh_main_stock_data_background_update(self):
        """启动后台更新Baostock股票数据"""
        try:
            # 创建并启动工作线程来执行特定任务
            self.load_worker = BaseThreadWorker(BaoStockProcessor().process_sh_main_stock_data)
            self.load_worker.finished.connect(self.slot_process_sh_main_stock_data_finished)
            self.load_worker.progress.connect(self.slot_process_sh_main_stock_data_progress)
            self.load_worker.error.connect(self.slot_process_sh_main_stock_data_error)
            self.load_worker.start()
            
            self.logger.info("已启动后台更新Baostock沪市股票数据")
        except Exception as e:
            self.logger.error(f"启动后台更新Baostock沪市股票数据: {e}")

    def process_sh_main_stock_data(self, task=None):
        self.process_sh_main_stock_daily_data(task)
        sleep_time = random.uniform(0.5, 1)
        time.sleep(sleep_time)
        self.process_sh_main_stock_weekly_data(task)
        return True
    
    def process_sh_main_stock_daily_data(self, task=None):
        self.process_stock_data(board_name='sh_main', TimePeriod=TimePeriod.DAY, task=task)

    def process_sh_main_stock_weekly_data(self, task=None):
        self.process_stock_data(board_name='sh_main', TimePeriod=TimePeriod.WEEK, task=task)


    # -----------------深市主板股票数据获取接口---------------------
    def process_sz_main_stock_daily_data(self, task=None):
        self.process_stock_data(board_name='sz_main', TimePeriod=TimePeriod.DAY, task=task)

    def start_sz_main_stock_data_background_update(self):
        try:
            # 创建并启动工作线程来执行特定任务
            self.load_worker = BaseThreadWorker(BaoStockProcessor().process_sz_main_stock_data)
            self.load_worker.finished.connect(self.slot_process_sz_main_stock_data_finished)
            self.load_worker.progress.connect(self.slot_process_sz_main_stock_data_progress)
            self.load_worker.error.connect(self.slot_process_sz_main_stock_data_error)
            self.load_worker.start()
            
            self.logger.info("已启动后台更新Baostock深市股票数据")
        except Exception as e:
            self.logger.error(f"启动后台更新Baostock深市股票数据失败: {e}")

    def process_sz_main_stock_data(self, task=None):
        self.process_sz_main_stock_daily_data(task)
        sleep_time = random.uniform(0.5, 1)
        time.sleep(sleep_time)
        self.process_sz_main_stock_weekly_data(task)
        return True

    def process_sz_main_stock_weekly_data(self, task=None):
        self.process_stock_data(board_name='sz_main', TimePeriod=TimePeriod.WEEK, task=task)

        
    # -----------------创业板股票数据获取接口---------------------
    def start_gem_stock_data_background_update(self):
        try:
            # 创建并启动工作线程来执行特定任务
            self.load_worker = BaseThreadWorker(BaoStockProcessor().process_gem_stock_data)
            self.load_worker.finished.connect(self.slot_process_gem_stock_data_finished)
            self.load_worker.progress.connect(self.slot_process_gem_stock_data_progress)
            self.load_worker.error.connect(self.slot_process_gem_stock_data_error)
            self.load_worker.start()
            
            self.logger.info("已启动后台更新Baostock创业板股票数据")
        except Exception as e:
            self.logger.error(f"启动后台更新Baostock创业板股票数据失败: {e}")
    def process_gem_stock_data(self, task=None):
        self.process_gem_stock_daily_data(task)
        sleep_time = random.uniform(0.5, 1)
        time.sleep(sleep_time)
        self.process_gem_stock_weekly_data(task)
        return True
    def process_gem_stock_daily_data(self, task=None):
        self.process_stock_data(board_name='gem', TimePeriod=TimePeriod.DAY, task=task)

    def process_gem_stock_weekly_data(self, task=None):
        self.process_stock_data(board_name='gem', TimePeriod=TimePeriod.WEEK, task=task)

    # -----------------科创板股票数据获取接口---------------------
    def start_star_stock_data_background_update(self):
        try:
            # 创建并启动工作线程来执行特定任务
            self.load_worker = BaseThreadWorker(BaoStockProcessor().process_star_stock_data)
            self.load_worker.finished.connect(self.slot_process_star_stock_data_finished)
            self.load_worker.progress.connect(self.slot_process_star_stock_data_progress)
            self.load_worker.error.connect(self.slot_process_star_stock_data_error)
            self.load_worker.start()
            
            self.logger.info("已启动后台更新Baostock科创板股票数据")
        except Exception as e:
            self.logger.error(f"启动后台更新Baostock科创板股票数据失败: {e}")

    def process_star_stock_data(self, task=None):
        self.process_star_stock_daily_data(task)
        sleep_time = random.uniform(0.5, 1)
        time.sleep(sleep_time)
        self.process_star_stock_weekly_data(task)
        return True
    
    def process_star_stock_daily_data(self, task=None):
        self.process_stock_data(board_name='star', TimePeriod=TimePeriod.DAY, task=task)

    def process_star_stock_weekly_data(self, task=None):
        self.process_stock_data(board_name='star', TimePeriod=TimePeriod.WEEK, task=task)

        

    # -----------------分钟级别股票数据获取接口---------------------
    def start_minute_level_stock_data_background_update(self, board_type, level):
        try:
            # 创建并启动工作线程来执行特定任务
            self.load_worker = BaseThreadWorker(BaoStockProcessor().process_minute_level_stock_data_with_board_type, board_type, level)
            # self.load_worker.finished.connect(self.slot_process_star_stock_data_finished)
            # self.load_worker.progress.connect(self.slot_process_star_stock_data_progress)
            # self.load_worker.error.connect(self.slot_process_star_stock_data_error)
            self.load_worker.start()
            
            self.logger.info(f"已启动后台更新Baostock {level}分钟级别{board_type}股票数据")
        except Exception as e:
            self.logger.error(f"启动后台更新Baostock {level}分钟级别{board_type}股票数据失败: {e}")

    def process_minute_level_stock_data_with_board_type(self, board_type, level, task=None):
        allowed_board_types = ['sh_main', 'sz_main', 'gem', 'star', 'bse']
        if board_type not in allowed_board_types:
            # raise ValueError(f"Invalid board_type: {board_type}. Allowed values are: {allowed_board_types}")
            self.logger.error(f"Invalid board_type: {board_type}. Allowed values are: {allowed_board_types}")
            return
        
        allowed_levels = ['1', '3', '5', '10', '15', '30', '45', '60', '90', '120']
        if level not in allowed_levels:
            # raise ValueError(f"Invalid level: {level}. Allowed values are: {allowed_levels}")
            self.logger.error(f"Invalid level: {level}. Allowed values are: {allowed_levels}")
            return
        
        i = 1

        self.logger.info(f"开始处理{board_type}股票{level}分钟级别数据...")
        start_time = time.time()  # 记录开始时间

        dict_stock_info = BaostockDataManager().get_stock_info_dict()
        for index, row in dict_stock_info[board_type].iterrows():
            if task:
                # 检查暂停状态
                task._check_pause()
                
                # 检查取消状态
                if task.is_cancelled():
                    break

            value = row['证券代码']
            stock_name = row['证券名称'] if '证券名称' in row else '未知'
            # self.logger.info(f"获取第 {i} 只{board_type}股票 {value} {level}分钟级别数据")
            
            result = self.process_and_save_minute_level_stock_data(value, level)

            # 测试
            # result = self.process_minute_level_stock_data(value, level)

            if result is None or result.empty:
                # self.logger.info(f"股票 {value} 数据获取失败")
                continue
            
            # 测试
            # if i > 3:
            #     self.logger.info(f"已获取到所有沪市股票日线数据, i: {i}")
            #     break
            
            if i % 100 == 0:  # 每100只股票打印一次日志
                self.logger.info(f"已处理 {i} 只{board_type}股票【{level}分钟级别】数据")

            i += 1

            del result  # 及时删除避免内存泄漏

        process_elapsed_time = time.time() - start_time  # 计算耗时
        self.logger.info(f"获取{board_type}股票{level}分钟级别数据完成，共处理{i}只股票，耗时: {process_elapsed_time:.2f}秒，即{process_elapsed_time/60:.2f}分钟")

        self.logger.info(f"{board_type}股票{level}分钟级别数据获取完成")

        # 批处理完成后强制垃圾回收
        gc.collect()


    # -----------------其他接口-------------------
    def get_and_save_all_stocks_from_bao(self):
        # 显示登陆返回信息
        # self.logger.info('login respond error_code:'+lg.error_code)
        # self.logger.info('login respond  error_msg:'+lg.error_msg)

        #### 获取证券信息 ####
        query_date = datetime.datetime.now().strftime("%Y-%m-%d")
        rs = bs.query_all_stock(query_date)
        self.logger.info('query_all_stock respond error_code:'+rs.error_code)
        self.logger.info('query_all_stock respond  error_msg:'+rs.error_msg)

        #### 打印结果集 ####
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(rs.get_row_data())

        chinese_columns = ['证券代码', '交易状态', '证券名称']
        result = pd.DataFrame(data_list, columns=chinese_columns)

        result['更新日期'] = query_date
        result['更新日期'] = pd.to_datetime(result['更新日期'], format='%Y-%m-%d').dt.date

        self.logger.info(f"获取所有股票数据完成，共有{len(result)}只股票。\n获取结果如下：\n{result.head(3)}")

        dict_all_stock_info = self.filter_stocks_by_board(result)

        # 打印各板块股票数量
        for board_name, df_board in dict_all_stock_info.items():
            self.logger.info(f"{board_name} 股票数量: {len(df_board)}")

            # self.logger.info(df_board.tail(1))

            # 如需查看具体代码，可取消下一行的注释
            # self.logger.info(f"{board_name} 股票代码:\n {df_board['code'].tolist()}\n")
            if board_name == '沪市主板':
                BaostockDataManager().save_stock_info_to_db(df_board, 'sh_main')
            elif board_name == '深市主板':
                BaostockDataManager().save_stock_info_to_db(df_board, 'sz_main')
            elif board_name == '创业板':
                BaostockDataManager().save_stock_info_to_db(df_board, 'gem')
            elif board_name == '科创板':
                BaostockDataManager().save_stock_info_to_db(df_board, 'star')
            elif board_name == '北交所':
               BaostockDataManager().save_stock_info_to_db(df_board, 'bse')

        #### 结果集输出到csv文件 ####   
        # result.to_csv("./data/database/stocks/db/baostock/all_stock.csv", encoding="utf-8", index=False)
        # self.logger.info(result)
        BaostockDataManager().save_stock_info_to_db(result, 'stock_basic_info')

    def get_all_stocks_from_db(self):
        BaostockDataManager().get_all_stocks_from_db()

    def filter_stocks_by_board(self, df):
        """
        根据证券代码前缀筛选出不同板块的股票
        """
        # 初始化空 DataFrame，用于存储各板块股票
        sh_main = pd.DataFrame()   # 沪市主板
        sz_main = pd.DataFrame()   # 深市主板
        gem = pd.DataFrame()       # 创业板
        star = pd.DataFrame()      # 科创板
        bse = pd.DataFrame()       # 北交所

        # 遍历每一行数据
        for index, row in df.iterrows():
            code = row['证券代码']
            
            if code.startswith('sh.600') or code.startswith('sh.601') or code.startswith('sh.602') or code.startswith('sh.603') or code.startswith('sh.605'):
                sh_main = pd.concat([sh_main, row.to_frame().T], ignore_index=True)
            elif code.startswith('sz.000') or code.startswith('sz.001') or code.startswith('sz.002') or code.startswith('sz.003'):
                sz_main = pd.concat([sz_main, row.to_frame().T], ignore_index=True)
            elif code.startswith('sz.300') or code.startswith('sz.301'):
                gem = pd.concat([gem, row.to_frame().T], ignore_index=True)
            elif code.startswith('sh.688'):
                star = pd.concat([star, row.to_frame().T], ignore_index=True)
            elif code.startswith('bj.'):  # 北交所股票前缀
                bse = pd.concat([bse, row.to_frame().T], ignore_index=True)
        
        return {
            '沪市主板': sh_main,
            '深市主板': sz_main,
            '创业板': gem,
            '科创板': star,
            '北交所': bse
        }

    def auto_test(self):
        # result, data_to_save = self.update_weekly_stock_data('sh.600000')
        # if data_to_save is not None and not data_to_save.empty:
        #     self.logger.info(f"保存周线数据成功，共有{len(data_to_save)}行数据")
        # else:
        #     self.logger.info("没有需要保存的周线数据")
        pass
    # 增量更新
    def update_sh_main_daily_data(self):
        pass

    def create_baostock_table_indexes(self):
        """
        为所有股票数据表创建索引以提高查询性能
        """
        board_index = 0  # 初始化变量
        
        self.logger.info("开始为所有股票数据表创建索引...")
        total_start_time = time.time()

        dict_stock_info = BaostockDataManager().get_stock_info_dict()
        total_stocks = sum(len(board_data) for board_data in dict_stock_info.values())
        processed_count = 0
        
        for board_name, board_data in dict_stock_info.items():
            if board_index > 1:
                break
            board_index += 1

            self.logger.info(f"创建 {board_name} 板块股票数据库索引...")
            board_start_time = time.time()
            
            # 遍历该板块的每一行数据
            for index, row in board_data.iterrows():
                try:
                    code = row['证券代码']  # 使用正确的列名
                    
                    # 为不同时间级别的数据表创建索引
                    
                    time_periods = [TimePeriod.DAY, TimePeriod.WEEK, TimePeriod.MINUTE_15, TimePeriod.MINUTE_30, TimePeriod.MINUTE_60]

                    for period in time_periods:
                        if BaostockDataManager().check_table_exists(code, period):
                            db_path = BaostockDataManager().get_db_path(code)
                            BaostockDataManager().create_baostock_table_index(db_path, period)
                        # else:
                        #     self.logger.debug(f"表 {table_name} 不存在，跳过索引创建")
                            
                except Exception as e:
                    self.logger.error(f"为股票 {code} 创建索引时出错: {str(e)}")
                    continue

                processed_count += 1
            
                # 每处理100只股票显示一次进度
                if processed_count % 100 == 0:
                    progress = (processed_count / total_stocks) * 100
                    self.logger.info(f"索引创建进度: {progress:.1f}% ({processed_count}/{total_stocks})")

            board_create_index_elapsed_time = time.time() - board_start_time
            self.logger.info(f"{board_name} 板块股票数据库索引创建完成，耗时: {board_create_index_elapsed_time:.2f}秒，即{board_create_index_elapsed_time/60:.2f}分钟")
        
        total_elapsed_time = time.time() - total_start_time
        self.logger.info(f"所有板块股票数据库索引创建完成，总耗时: {total_elapsed_time:.2f}秒，即{total_elapsed_time/60:.2f}分钟")


    def stop_process(self):
        self.b_stop_process = True


    # --------------------------槽函数-------------------------
    def slot_stock_data_loading_finished(self, success):
        self.logger.info(f"success的类型：{type(success)}")
        if success:
            self.logger.info("后台数据加载成功完成")
        else:
            self.logger.error("后台数据加载失败")

        self.sig_stock_data_load_finished.emit(success)

    def slot_stock_data_loading_progress(self, progress):
        self.logger.info(f"progress的类型：{type(progress)}")
        self.logger.info(f"加载进度: {progress}")
        self.sig_stock_data_load_progress.emit(progress)

    def slot_stock_data_loading_error(self, error):
        self.logger.info(f"error的类型：{type(error)}")
        self.logger.error(f"后台加载出错: {error}")
        self.sig_stock_data_load_error.emit(error)


    def slot_process_sh_main_stock_data_finished(self, success):
        self.logger.info(f"沪市主板数据后台更新完成，success: {success}")
    
    def slot_process_sh_main_stock_data_progress(self, progress):
        self.logger.info(f"沪市主板数据后台更新进度: {progress}")
    
    def slot_process_sh_main_stock_data_error(self, error):
        self.logger.info(f"沪市主板数据后台更新出错: {error}") 

    def slot_process_sz_main_stock_data_finished(self, success):
        self.logger.info(f"深市主板数据后台更新完成，success: {success}")
    
    def slot_process_sz_main_stock_data_progress(self, progress):
        self.logger.info(f"深市主板数据后台更新进度: {progress}")
    
    def slot_process_sz_main_stock_data_error(self, error):
        self.logger.info(f"深市主板数据后台更新出错: {error}")

    def slot_process_gem_stock_data_finished(self, success):
        self.logger.info(f"创业板数据后台更新完成，success: {success}")

    def slot_process_gem_stock_data_progress(self, progress):
        self.logger.info(f"创业板数据后台更新进度: {progress}")    

    def slot_process_gem_stock_data_error(self, error):
        self.logger.info(f"创业板数据后台更新出错: {error}")

    def slot_process_star_stock_data_finished(self, success):
        self.logger.info(f"科创板数据后台更新完成，success: {success}")

    def slot_process_star_stock_data_progress(self, progress):
        self.logger.info(f"科创板数据后台更新进度: {progress}")  
                
    def slot_process_star_stock_data_error(self, error):
        self.logger.info(f"科创板数据后台更新出错: {error}")

    def slot_baostock_data_fetch_task_completed(self, task_id, result):
        self.logger.info(f"task_id: {task_id}, result: {result}")

if __name__ == "__main__":
    bao_stock_processor = BaoStockProcessor()
    bao_stock_processor.test()