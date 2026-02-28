
from PyQt5.QtCore import QObject, pyqtSignal
from db_base.stock_info_db_base import StockInfoDBBasePool
from db_base.stock_db_base import StockDbBase
from indicators import stock_data_indicators as sdi
from manager.logging_manager import get_logger
from common.common_api import *

from manager.period_manager import TimePeriod

import time
import traceback
import pandas as pd
import threading
from types import MappingProxyType

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
class BaostockDataManager(QObject):
    def __init__(self, parent=None):
        super().__init__() 
        self.logger = get_logger(__name__)

        self.lock = threading.Lock()

        self.dict_stocks_info = {}  # {'board': pd.DataFrame()}, 示例：{'sh_main' : pd.DataFrame()}
        # self.dict_stock_data = {}   # {'TimePeriod': {'code': DataFrame}}，示例：{'TimePeriod.Day': {'sh.600000': pd.DataFrame()}}
        self.dict_lastest_1d_stock_data = {}  # {code : pd.DataFrame}, 仅缓存最后一行数据用于快速加载股票list列表

        self.stock_info_db_base = StockInfoDBBasePool().get_manager(1)
        self.stock_db_base = StockDbBase("./data/database/stocks/db/baostock")

        self.get_all_stocks_from_db()

    def get_stock_info_dict(self):
        with self.lock:
            return MappingProxyType(self.dict_stocks_info)
        
    def get_lastest_1d_stock_data_dict_from_cache(self):
        '''
            返回缓存中的最后一天（行）的股票数据
            return: dict, {code : DataFrame}
        '''
        with self.lock:
            return MappingProxyType(self.dict_lastest_1d_stock_data)


    # ----------------------stock_info相关接口-----------------------------------------
    def get_all_stocks_from_db(self):
        with self.lock:
            # self.dict_stocks_info['sh_main'] = self.stock_info_db_base.get_sh_main_stocks()
            # self.dict_stocks_info['sz_main'] = self.stock_info_db_base.get_sz_main_stocks()
            # self.dict_stocks_info['gem'] = self.stock_info_db_base.get_gem_stocks()
            # self.dict_stocks_info['star'] = self.stock_info_db_base.get_star_stocks()

            self.dict_stocks_info['sh_main'] = self.stock_info_db_base.get_lastest_stocks(table_name='sh_main')
            self.dict_stocks_info['sz_main'] = self.stock_info_db_base.get_lastest_stocks(table_name='sz_main')
            self.dict_stocks_info['gem'] = self.stock_info_db_base.get_lastest_stocks(table_name='gem')
            self.dict_stocks_info['star'] = self.stock_info_db_base.get_lastest_stocks(table_name='star')

        sh_main_count = len(self.dict_stocks_info['sh_main'])
        sz_main_count = len(self.dict_stocks_info['sz_main'])
        gem_main_count = len(self.dict_stocks_info['gem'])
        star_main_count = len(self.dict_stocks_info['star'])

        self.logger.info(f"沪A主板股票数量：{sh_main_count}")
        self.logger.info(f"深A主板股票数量：{sz_main_count}")
        self.logger.info(f"创业板股票数量：{gem_main_count}")
        self.logger.info(f"科创板股票数量：{star_main_count}")
        self.logger.info(f"总股票数量(未计算北交所股票)：{sh_main_count + sz_main_count + gem_main_count + star_main_count}")


    def save_stock_info_to_db(self, df_data, board='stock_basic_info'):
        with self.lock:
            self.stock_info_db_base.save_tao_stocks_to_db(df_data, board)

    def get_stock_name_by_code(self, code):
        try:
            board_name = identify_stock_board(code)
            
            if board_name not in self.dict_stocks_info:
                return None

            with self.lock:
                df_board_data = self.dict_stocks_info[board_name]
            
            if df_board_data.empty:
                return None
                
            # 使用query方法（更直观）
            matched_row = df_board_data[df_board_data['证券代码'] == code]
            
            if not matched_row.empty:
                return matched_row.iloc[0].get('证券名称', '未知')
            else:
                return None
                
        except (KeyError, IndexError) as e:
            self.logger.debug(f"未找到股票 {code} 的名称: {e}")
            return None
        except Exception as e:
            self.logger.error(f"获取股票 {code} 名称时出错: {e}")
            return None
        
    # ----------------------stock_db_base相关接口-----------------------------------------
    def check_stock_db_exists(self, code):
        with self.lock:
            return self.stock_db_base.check_stock_db_exists(code)
    
    def get_db_path(self, code):
        with self.lock:
            return self.stock_db_base.get_db_path(code)

    def check_table_exists(self, code, period=TimePeriod.DAY):
        table_name = period.get_table_name()
        with self.lock:
            return self.stock_db_base.check_table_exists(code, table_name)
    
    def create_baostock_table_index(self, db_path, period=TimePeriod.DAY):
        table_name = period.get_table_name()
        with self.lock:
            self.stock_db_base.create_baostock_table_index(db_path, table_name)

    def load_1d_local_stock_data(self):
        """
        加载日线股票数据
        """
        self.get_all_lastest_row_data_dict_by_period(TimePeriod.DAY)
        return True
        total_count = 0

        dict_daily_stock_data = {}
        
        # 遍历所有板块
        board_index = 0

        self.logger.info(f"开始读取本地数据库日线股票数据...")
        start_time = time.time()  # 记录开始时间

        dict_stock_info = self.get_stock_info_dict()
        for board_name, board_data in dict_stock_info.items():
            if board_index > 1:
                break
            board_index += 1

            self.logger.info(f"读取 {board_name} 板块...")
            board_start_time = time.time()  # 记录开始时间
            
            # 遍历该板块的每一行数据
            for index, row in board_data.iterrows():
                # if index > 100:
                #     break

                try:
                    stock_code = row['证券代码']
                    stock_name = row['证券名称'] if '证券名称' in row else '未知'
                    
                    # 获取日线和周线数据
                    daily_data = self.get_stock_data_from_db_by_period_with_indicators(stock_code, TimePeriod.DAY)
        
                    
                    # 检查数据是否为None，如果是则创建空的DataFrame
                    if daily_data is None or daily_data.empty:
                        continue
                        

                    # 存储数据
                    dict_daily_stock_data[stock_code] = daily_data
                    
                    total_count += 1
                    
                except Exception as e:
                    self.logger.error(f"处理股票 {stock_code} 时发生错误: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    # 继续处理下一个股票
                    continue

            board_read_elapsed_time = time.time() - board_start_time  # 计算耗时
            self.logger.info(f"读取完成，共读取{total_count}只股票，耗时: {board_read_elapsed_time:.2f}秒，即{board_read_elapsed_time/60:.2f}分钟")

        
        all_read_elapsed_time = time.time() - start_time  # 计算耗时
        self.logger.info(f"读取完成，总耗时: {all_read_elapsed_time:.2f}秒，即{all_read_elapsed_time/60:.2f}分钟")

        # 不再加载完整的日线数据到内存
        # with self.lock:
        #     self.dict_stock_data[TimePeriod.DAY] = dict_daily_stock_data

        self.logger.info(f"总共处理了 {total_count} 只股票")
        return True  

    def get_stock_data_from_db_by_period(self, code, period=TimePeriod.DAY, start_date=None, end_date=None):
        '''从数据中获取股票指定周期的k线数据(原始数据库数据，未处理指标)'''
        table_name = period.get_table_name()
        # self.logger.info(f"处理股票: {code}, 表名：{table_name}")

        with self.lock:
            df_data = self.stock_db_base.get_bao_stock_data(code, table_name, start_date, end_date)

        df_data = df_data.dropna()

        if df_data is None or df_data.empty:
            return pd.DataFrame()
        
        return df_data
    
    def get_stock_data_from_db_by_period_with_indicators_auto(self, code, period=TimePeriod.DAY, start_date=None, end_date=None):
        # 不再加载完整日线数据到内存
        return self.get_stock_data_from_db_by_period_with_indicators(code, period, start_date, end_date)

    def get_stock_data_from_db_by_period_with_indicators(self, code, period=TimePeriod.DAY, start_date=None, end_date=None):
        '''从数据中获取股票指定周期的k线数据，并计算指标'''
        df_data = self.get_stock_data_from_db_by_period(code, period, start_date, end_date)
        # self.data_type_conversion(df_data)
        stock_name = self.get_stock_name_by_code(code)
        if stock_name is None:
            stock_name = "未知"
        df_data = df_data.assign(name=stock_name)
        sdi.default_indicators_auto_calculate(df_data)
        return df_data
    
    def get_all_lastest_row_data_dict_by_period_auto(self, period=TimePeriod.DAY):
        if self.dict_lastest_1d_stock_data:
            self.logger.info(f"返回缓存的最后一天（行数据）")
            return self.get_lastest_1d_stock_data_dict_from_cache()
        else:
            return self.get_all_lastest_row_data_dict_by_period(period)
    def get_all_lastest_row_data_dict_by_period(self, period=TimePeriod.DAY):
        '''获取所有股票的指定周期k线数据的最后一行数据，通常用于初始化list列表，不需要计算指标'''
        dict_result = {}    # {'code': DataFrame}
        table_name = period.get_table_name()

        # 遍历所有板块
        board_index = 0
        total_count = 0
        self.logger.info(f"开始读取本地数据库日线、周线股票的最后一天（行）数据...")
        start_time = time.time()  # 记录开始时间

        with self.lock:
            dict_stocks_info = self.dict_stocks_info

        for board_name, board_data in dict_stocks_info.items():
            if board_index > 1:
                break
            board_index += 1

            self.logger.info(f"读取 {board_name} 板块...")
            board_start_time = time.time()  # 记录开始时间
            
            # 遍历该板块的每一行数据
            for index, row in board_data.iterrows():
                # if index > 100:
                #     break

                try:
                    code = row['证券代码']
                    name = row['证券名称'] if '证券名称' in row else '未知'
                    
                    with self.lock:
                        lastest_1d_data = self.stock_db_base.get_lastest_stock_data(code, table_name)     

                    if lastest_1d_data is None or lastest_1d_data.empty:
                        self.logger.debug(f"股票 {code} 日线数据为空，跳过指标计算")
                        continue 

                    # 只对非空数据进行指标计算
                    # self.data_type_conversion(lastest_1d_data)
                    lastest_1d_data['name'] = name
                    # sdi.default_indicators_auto_calculate(lastest_1d_data)
                    dict_result[code] = lastest_1d_data
                    total_count += 1
                    
                except Exception as e:
                    self.logger.error(f"处理股票 {code} 时发生错误: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    # 继续处理下一个股票
                    continue

            board_read_elapsed_time = time.time() - board_start_time  # 计算耗时
            self.logger.info(f"读取完成，共读取{total_count}只股票，耗时: {board_read_elapsed_time:.2f}秒，即{board_read_elapsed_time/60:.2f}分钟")

        
        all_read_elapsed_time = time.time() - start_time  # 计算耗时
        self.logger.info(f"读取完成，总耗时: {all_read_elapsed_time:.2f}秒，即{all_read_elapsed_time/60:.2f}分钟")

        with self.lock:
            self.dict_lastest_1d_stock_data = dict_result

        return dict_result
    
    def get_lastest_row_data_dict_by_code_list_auto(self, code_list=[], period=TimePeriod.DAY):
        '''优先从缓存中获取：指定列表中的股票代码指定周期的最后一天股票数据'''
        if code_list is None or len(code_list) == 0:
            self.logger.info(f"没有指定股票代码，返回空字典")
            return {}
        
        dict_result = {}

        with self.lock:
            dict_lastest_1d_stock_data = self.dict_lastest_1d_stock_data
        if dict_lastest_1d_stock_data:
            self.logger.info(f"返回缓存的指定code列表的最后一天（行数据）")
            for code in code_list:
                dict_result[code] = dict_lastest_1d_stock_data[code]
            return dict_result  
        else:
            return self.get_lastest_row_data_dict_by_code_list(code_list, period)
    def get_lastest_row_data_dict_by_code_list(self, code_list=[], period=TimePeriod.DAY):
        '''获取指定列表中的股票代码指定周期的最后一天股票数据，通常用于初始化list列表，不需要计算指标'''
        if code_list is None or len(code_list) == 0:
            self.logger.info(f"没有指定股票代码，返回空字典")
            return {}
        
        dict_result = {}
        table_name = period.get_table_name()
        for code in code_list:
            try:
                with self.lock:
                    lastest_1d_data = self.stock_db_base.get_lastest_stock_data(code, table_name)     

                if lastest_1d_data is None or lastest_1d_data.empty:
                    self.logger.debug(f"股票 {code} 日线数据为空，跳过指标计算")
                    continue 

                # 只对非空数据进行指标计算
                # self.data_type_conversion(lastest_1d_data)
                lastest_1d_data['name'] = self.get_stock_name_by_code(code)
                # sdi.default_indicators_auto_calculate(lastest_1d_data)
                dict_result[code] = lastest_1d_data
                
            except Exception as e:
                self.logger.error(f"处理股票 {code} 时发生错误: {str(e)}")
                self.logger.error(traceback.format_exc())
                # 继续处理下一个股票
                continue

        return dict_result
    
    def get_lastest_stock_data_date(self, code, period=TimePeriod.DAY):
        '''获取指定股票的指定周期的股票数据最后一天的日期'''
        with self.lock:
            dict_lastest_1d_stock_data = self.dict_lastest_1d_stock_data
        if dict_lastest_1d_stock_data:
            s_return = dict_lastest_1d_stock_data[code].iloc[0]['date'] if code in dict_lastest_1d_stock_data else None 
            self.logger.info(f"返回缓存的最后一天（行数据）的日期： {s_return}")
            return s_return
        else:  # 从数据库中读取
            table_name = period.get_table_name()
            with self.lock:
                lastest_data = self.stock_db_base.get_lastest_stock_data(code, table_name) 
            return lastest_data.iloc[0]['date'] if lastest_data is not None and not lastest_data.empty else None

    def save_stock_data_to_db(self, code, df_data, writeWay="replace", period=TimePeriod.DAY):
        '''保存k线数据到指定周期数据库'''
        table_name = period.get_table_name()
        # self.logger.info(f"保存股票 {code} 数据到数据库 {table_name}")
        with self.lock:
            self.stock_db_base.save_bao_stock_data_to_db(code, df_data, writeWay, table_name)


    def data_type_conversion(self, result):
        # 1. 转换日期列
        if 'date' in result.columns:
            result['date'] = pd.to_datetime(result['date'], format='%Y-%m-%d').dt.date  # 转换为 datetime.date 类型，或者用 .dt.normalize() 取日期部分

        # 处理 time 字段 - 增强版
        if 'time' in result.columns:
            # 先尝试直接转换，如果失败则逐个处理
            try:
                # 首先尝试标准格式
                result['time'] = pd.to_datetime(result['time'], format='%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                try:
                    # 尝试紧凑格式 YYYYMMDDHHMMSSxxx
                    def parse_compact_time(time_str):
                        if pd.isna(time_str):
                            return None
                        
                        time_str = str(time_str).strip()
                        
                        # 处理类似 "20250102100000000" 的格式
                        if len(time_str) >= 14 and time_str.isdigit():
                            # 截取前14位作为日期时间: YYYYMMDDHHMMSS
                            if len(time_str) >= 14:
                                year = time_str[0:4]
                                month = time_str[4:6]
                                day = time_str[6:8]
                                hour = time_str[8:10]
                                minute = time_str[10:12]
                                second = time_str[12:14]
                                
                                formatted_time = f"{year}-{month}-{day} {hour}:{minute}:{second}"
                                return pd.to_datetime(formatted_time, format='%Y-%m-%d %H:%M:%S')
                        
                        # 其他格式尝试
                        return pd.to_datetime(time_str)
                    
                    # 对每个时间值单独处理
                    result['time'] = result['time'].apply(parse_compact_time)
                    
                except Exception as e:
                    self.logger.warning(f"时间字段转换出现异常: {e}")
                    # 最后的备选方案：使用 pandas 自动推断
                    try:
                        result['time'] = pd.to_datetime(result['time'], errors='coerce')
                    except:
                        # 如果还是失败，转换为字符串
                        result['time'] = result['time'].astype(str)
                        self.logger.warning(f"时间字段转换最终失败，已转换为字符串")


        # 2. 转换数值列 (开盘, 最高, 最低, 收盘, 成交额, 涨跌幅, 换手率)
        numeric_columns = ['open', 'high', 'low', 'close', 'amount', 'change_percent', 'turnover_rate']
        for col in numeric_columns:
            if col in result.columns:
                # result[col] = result[col].str.replace(',', '').str.replace('%', '').str.replace('--', '0')
                result[col] = pd.to_numeric(result[col], errors='coerce')  # errors='coerce' 将无效解析转换为NaN

        # 3. 转换成交量 (整数)
        if 'volume' in result.columns:
            result['volume'] = pd.to_numeric(result['volume'], errors='coerce').astype('Int64')  # 使用 Pandas 的可空整数类型

        # 4. 转换复权方式 (整数)
        if 'adjustflag' in result.columns:
            result['adjustflag'] = pd.to_numeric(result['adjustflag'], errors='coerce').astype('Int64')

        # 5. 转换是否ST (布尔值) - 根据你的数据实际情况定义如何映射
        # 假设你的字符串可能是 '是'/'否' 或 '1'/'0'
        if 'isST' in result.columns:
            result['isST'] = result['isST'].map({'是': True, '否': False, '1': True, '0': False, 'True': True, 'False': False})
        # 或者如果原本是字符串形式的 'True'/'False'
        # result['是否ST'] = result['是否ST'].astype(bool)
        # else:
            # self.logger.info("result中没有 是否ST 列")

        # 打印转换后的数据类型检查
        # self.logger.info(result.dtypes)