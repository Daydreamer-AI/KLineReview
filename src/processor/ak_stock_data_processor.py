import akshare as ak
import pandas as pd
import sqlite3
import os
import datetime
from pathlib import Path
from db_base.stock_info_db_base import StockInfoDBBasePool
from db_base.stock_db_base import StockDbBase
import datetime
from indicators import stock_data_indicators as sdi
import random
import time
from common.common_api import *
import threading
from manager.logging_manager import get_logger

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
class AKStockDataProcessor:
    '''
    
    维护：
    1. 所有股票日线、周线数据？内存能否扛住？
    2. 不维护股票数据，随用随删。
    '''
    def __init__(self):
        self.logger = get_logger(__name__)
        self.logger.info("AKStockDataProcessor::__init__ begin")
        self.stock_info_db_base = StockInfoDBBasePool().get_manager(0)
        self.logger.info("AKStockDataProcessor--StockInfoDBBasePool().get_manager(0) end")
        self.stock_db_base = StockDbBase("./data/database/stocks/db/akshare")

        self.dict_stocks = {}   # key: 板块，value：板块对应的股票信息（证券代码、证券名称）- pandas.DataFrame对象
        self.df_stocks_eastmoney = pd.DataFrame() # 带有市值信息的股票数据 - pandas.DataFrame对象
        self.dict_chip_distribution_data_eastmoney = {}   # 东方财富的筹码分布数据 - 字典对象，key：股票代码，value： pandas.DataFrame对象
        self.logger.info("AKStockDataProcessor::__init__ done")

    def initialize(self) -> bool:
        self.logger.info("AKStockDataProcessor::initialize begin")
        self.dict_stocks = self.get_stock_info_from_db()
        self.df_stocks_eastmoney = self.stock_info_db_base.get_latest_eastmoney_stock_data()
        # if file_exists('./stocks/excel/stocks_eastmoney.xlsx'):
        #     self.df_stocks_eastmoney = pd.read_excel('./stocks/excel/stocks_eastmoney.xlsx')
        # else:
        #     self.logger.info('未找到./stocks/excel/stocks_eastmoney.xlsx')

        # self.query_eastmoney_stock_chip_distribution_data()       # 筹码分布数据不再维护
        self.logger.info("AKStockDataProcessor::initialize done")

        return True
    
    def cleanup(self) -> None:
        pass

    def get_stocks_eastmoney(self):
        return self.df_stocks_eastmoney

    # 股票数据接口
    def get_stocks_info_and_save_to_db(self):
        # 初始化数据库  ./stocks/db/stocks.db

        # 获取股票代码和名称
        # 获取A股所有股票代码和名称
        df = ak.stock_info_a_code_name()
        # self.logger.info("原始数据验证:\n", df.tail(3))

        df.columns = ['证券代码', '证券名称']
        # self.logger.info("验证:\n", df.tail(3))

        # 建表。self.stock_info_db_base初始化时已创建
        # self.stock_info_db_base.create_table("stock_basic_info", "CREATE TABLE IF NOT EXISTS stock_basic_info (证券代码 TEXT PRIMARY KEY, 证券名称 TEXT)")


        # 保存到数据库
        self.stock_info_db_base.insert_dataframe_to_table("stock_basic_info", df, "replace")
    def get_stock_info_from_db(self):
        df_stocks_info = self.stock_info_db_base.get_table_data("stock_basic_info")
        dick_stocks = classify_a_stocks_by_board(df_stocks_info)
        # self.logger.info("上海主板股票：", dick_stocks['sh_main'].tail(3))
        # self.logger.info("\n")
        # self.logger.info("深圳主板股票：", dick_stocks['sz_main'].tail(3))
        # self.logger.info("\n")
        # self.logger.info("创业板股票：", dick_stocks['gem'].tail(3))
        # self.logger.info("\n")
        # self.logger.info("科创板股票：", dick_stocks['star'].tail(3))
        # self.logger.info("\n")
        # self.logger.info("北交所股票：", dick_stocks['bse'].tail(3))

        statistics = get_board_stock_statistics(df_stocks_info)
        for board, count in statistics.items():
            self.logger.info(f"{board}: {count} 只股票")
        
        return dick_stocks


    # ------------------------------------------------------------同花顺行业板块一览表接口-----------------------------------------
    def auto_process_and_save_ths_board_industry(self):
        '''
            获取、处理并插入同花顺行业板块一览表，每天调用
        '''
        max_retries = 3  # 最大重试次数
        retry_count = 0
        
        # 获取行业板块数据
        while retry_count < max_retries:
            try:
                b_ret = self.process_and_save_ths_board_industry()
                if b_ret:
                    break  # 成功则跳出循环
                else:
                    retry_count += 1
                    self.logger.info(f"获取数据失败，正在进行第 {retry_count} 次重试")
                    
                    # 重试前等待一段时间，避免过于频繁的请求
                    if retry_count < max_retries:
                        time.sleep(random.uniform(3, 5))  # 随机延迟3-5秒
                    
            except Exception as e:
                retry_count += 1
                self.logger.info(f"获取数据失败: {e}，正在进行第 {retry_count} 次重试")
                
                # 重试前等待一段时间
                if retry_count < max_retries:
                    time.sleep(random.uniform(3, 5))
        
        # 检查是否达到最大重试次数
        if retry_count >= max_retries:
            self.logger.error(f"经过 {max_retries} 次重试后仍然获取数据失败")
            return False
        
        # 验证数据完整性
        lastest_ths_industry_data = self.get_latest_ths_board_industry_data()
        if lastest_ths_industry_data is None or lastest_ths_industry_data.empty:
            self.logger.error("获取到的数据为空")
            return False
            
        lastest_date = lastest_ths_industry_data['date'].iloc[0]
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")

        if lastest_date == current_date:
            self.logger.info("今日数据已存在，获取成功")
            return True
        
        return False


    def process_and_save_ths_board_industry(self):
        '''
            获取、处理并插入同花顺行业板块一览表，收盘后调用
        '''
        # 获取行业板块数据
        try:
            df = ak.stock_board_industry_summary_ths()
        except Exception as e:
            self.logger.info(f"获取数据失败: {e}")
            return False
        
        # self.logger.info(df.head(3))

        # 处理百分比字段
        df['涨跌幅'] = df['涨跌幅'].apply(convert_percentage)
        df['领涨股-涨跌幅'] = df['领涨股-涨跌幅'].apply(convert_percentage)
        
        # 处理数值字段
        df['上涨家数'] = df['上涨家数'].fillna(0).astype(int)
        df['下跌家数'] = df['下跌家数'].fillna(0).astype(int)
        df['领涨股'] = df['领涨股'].astype(str)  # 确保领涨股为字符串
        
        # 添加日期字段
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        df['日期'] = today

        return self.stock_info_db_base.insert_ths_board_industry_data_to_db(df)

    def query_ths_board_industry_data(self, date=None, industry_name=None):
        return self.stock_info_db_base.query_ths_board_industry_data(date, industry_name)

    def get_latest_ths_board_industry_data(self):
        return self.stock_info_db_base.get_latest_ths_board_industry_data()


    # --------------------------------------------------------同花顺概念板块信息表接口----------------------------------------------------------
    def query_ths_concept_board_info(self):
        try: 
            df = ak.stock_board_concept_name_ths()
            self.logger.info(f"获取到{len(df)} 个同花顺概念")
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            df['date'] = today
            # self.logger.info(df.head(3))
            return self.stock_info_db_base.insert_ths_concept_board_info_to_db(df)

        except Exception as e:
            self.logger.info(f"获取数据失败: {e}")
            return False
        
    def get_latest_ths_concept_board_info(self):
        return self.stock_info_db_base.get_latest_ths_concept_board_info()
    
    # --------------------------------------------------------同花顺概念板块概览表接口----------------------------------------------------------
    def process_ths_board_concept_overview_data(self):
        if not self.query_ths_concept_board_info():
            return False
        
        lastest_ths_concept_board_info = self.get_latest_ths_concept_board_info()
        count = 1
        try: 
            for row in lastest_ths_concept_board_info.itertuples():
                self.logger.info(f"开始处理第 {count} 个概念: {row.concept_name}, 概念代码: {row.concept_code}")
                df = ak.stock_board_concept_info_ths(symbol=row.concept_name)

                if df is None or df.empty:  # 如果数据为空，则跳过
                    self.logger.warning(f"获取的概念: {row.concept_name}, 概念代码: {row.concept_code}数据为空，跳过处理")
                    continue

                # self.logger.info(f"返回数据类型：{type(df)}")   # <class 'pandas.core.frame.DataFrame'>
                # self.logger.info(df)

                # today = datetime.datetime.now().strftime('%Y-%m-%d')
                # df['date'] = today
                # self.logger.info(df.head(3))
                # self.stock_info_db_base.insert_ths_concept_board_info_to_db(df)

                # 插入详细信息到数据库
                self.stock_info_db_base.insert_ths_board_concept_overview(row.concept_name, row.concept_code, df)

                sleep_time = random.uniform(0.3, 1)
                time.sleep(sleep_time)

                count += 1
                # if count >=50:
                #     break

            return True

        except Exception as e:
            self.logger.info(f"获取数据失败: {e}")
            return False

    def query_ths_board_concept_overview(self, concept_name=None, date=None):
        return self.stock_info_db_base.query_ths_board_concept_overview(concept_name, date)
    
    def get_latest_ths_board_concept_overview(self):
        return self.stock_info_db_base.get_latest_ths_concept_board_overview()


    # --------------------------------------------------------东方财富概念板块信息表接口----------------------------------------------------------
     # 通过stock_board_concept_name_em接口日更概念板块，再通过stock_board_concept_cons_em接口日更概念板块所有成分股

    
    # ------------------------------------------------------------------------------------------------------------------

    # ======================================================================东方财富接口============================================================

    # ------------------------------------------------------------东方财富股票数据表stock_data_eastmoney接口-----------------------------------------
    # 获取A股所有股票信息
    def get_all_stocks_from_eastmoney(self):
        self.logger.info(self.df_stocks_eastmoney.tail(3))
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        if self.df_stocks_eastmoney is not None and not self.df_stocks_eastmoney.empty and today in self.df_stocks_eastmoney['date'].values:
            self.logger.info("已是最新日期数据")
            return

        self.df_stocks_eastmoney = pd.DataFrame()
        for key, value in self.dict_stocks.items():
            # 检查 DataFrame 是否为空
            if value.empty:
                continue
            
            index = 1
            for index, row in value.iterrows():
                try:
                    stock_code = row['证券代码']
                    # self.logger.info("stock_code的类型：", type(stock_code))
                    # self.logger.info(f"正在获取第 {index} 只股票：{stock_code}")
                    stock_individual_info_em_df = ak.stock_individual_info_em(symbol=stock_code, timeout=30000)
                    # self.logger.info("stock_individual_info_em_df的类型：", type(stock_individual_info_em_df))
                    # add_stock_data(self.df_stocks_eastmoney, stock_individual_info_em_df)
                    # self.logger.info("stock_individual_info_em_df:", stock_individual_info_em_df)

                    # 将键值对形式的DataFrame转换为一行数据
                    # 方法1: 使用pivot或set_index + unstack
                    stock_data = stock_individual_info_em_df.set_index('item')['value'].to_dict()
                    
                    # 转换为DataFrame的一行
                    stock_row = pd.DataFrame([stock_data])
                    # self.logger.info("转换后的数据:", stock_row)
                    
                    # 合并到总数据中
                    self.df_stocks_eastmoney = pd.concat([self.df_stocks_eastmoney, stock_row], ignore_index=True)
                    

                    sleep_time = random.uniform(0.5, 1)
                    time.sleep(sleep_time)

                except Exception as e:
                    self.logger.info(f"处理股票 {stock_code} 时出错: {e}")
                    continue
        
        # 打印最后处理的股票数据
        self.df_stocks_eastmoney['日期'] = today
        self.logger.info("\n处理后的数据:\n")
        self.logger.info(self.df_stocks_eastmoney.tail(3))
        # self.df_stocks_eastmoney.to_excel('./stocks/excel/stocks_eastmoney.xlsx', index=False)
        self.stock_info_db_base.insert_eastmoney_stock_data_to_db(self.df_stocks_eastmoney)

    def query_eastmoney_stock_data(self):
        return self.stock_info_db_base.query_eastmoney_stock_data()

    def get_latest_eastmoney_stock_data(self):
        return self.stock_info_db_base.get_latest_eastmoney_stock_data()
    

    # ------------------------------------------------------------东方财富股票行业板块接口-----------------------------------------
    def auto_process_and_save_em_industry_board_data(self):
        '''
            获取、处理并插入东方财富行业板块一览表，每天调用
        '''
        max_retries = 3  # 最大重试次数
        retry_count = 0
        
        # 获取行业板块数据
        while retry_count < max_retries:
            try:
                b_ret = self.process_and_save_em_industry_board_data()
                if b_ret:
                    break  # 成功则跳出循环
                else:
                    retry_count += 1
                    self.logger.info(f"获取数据失败，正在进行第 {retry_count} 次重试")
                    
                    # 重试前等待一段时间，避免过于频繁的请求
                    if retry_count < max_retries:
                        time.sleep(random.uniform(3, 5))  # 随机延迟3-5秒
                    
            except Exception as e:
                retry_count += 1
                self.logger.info(f"获取数据失败: {e}，正在进行第 {retry_count} 次重试")
                
                # 重试前等待一段时间
                if retry_count < max_retries:
                    time.sleep(random.uniform(3, 5))
        
        # 检查是否达到最大重试次数
        if retry_count >= max_retries:
            self.logger.error(f"经过 {max_retries} 次重试后仍然获取数据失败")
            return False
        
        # 验证数据完整性
        lastest_ths_industry_data = self.get_latest_ths_board_industry_data()
        if lastest_ths_industry_data is None or lastest_ths_industry_data.empty:
            self.logger.error("获取到的数据为空")
            return False
            
        lastest_date = lastest_ths_industry_data['date'].iloc[0]
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")

        if lastest_date == current_date:
            self.logger.info("今日数据已存在，获取成功")
            return True
        
        return False
    
    def process_and_save_em_industry_board_data(self):
        '''
            获取、处理并插入东方财富行业板块一览表，收盘后调用
        '''
        # 获取行业板块数据
        try:
            df = ak.stock_board_industry_name_em()
        except Exception as e:
            self.logger.info(f"获取数据失败: {e}")
            return False
        
        self.logger.info(df.head(3))

        # 处理百分比字段
        df['涨跌幅'] = df['涨跌幅'].apply(convert_percentage)
        df['领涨股票-涨跌幅'] = df['领涨股票-涨跌幅'].apply(convert_percentage)
        df['换手率'] = df['换手率'].apply(convert_percentage)
        
        # 处理数值字段
        df['上涨家数'] = df['上涨家数'].fillna(0).astype(int)
        df['下跌家数'] = df['下跌家数'].fillna(0).astype(int)
        df['领涨股票'] = df['领涨股票'].astype(str)  # 确保领涨股为字符串
        
        # 添加日期字段
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        df['日期'] = today

        return self.stock_info_db_base.insert_em_industry_board_data_to_db(df)
    
    def query_em_industry_board_data(self, date=None, industry_name=None):
        return self.stock_info_db_base.query_em_industry_board_data(date, industry_name)

    def get_latest_em_industry_board_data(self):
        return self.stock_info_db_base.get_latest_em_industry_board_data()
    
    # ------------------------------------------------------------东方财富股票行业板块成分股接口-----------------------------------------
    # def process_and_save_em_industry_board_cons(self):
    #     '''
    #         获取、处理并保存东方财富行业板块成分股，收盘后调用
    #     '''
    #     # 获取行业板块数据
    #     try:
    #         lastest_em_industry_board_data = self.get_latest_em_industry_board_data()

    #         df_industry_board_cons_data = {}  # {'code' , 'name', 'industry'}
    #         for index, row in lastest_em_industry_board_data.iterrows():
    #             # self.process_and_save_em_industry_board_cons(row['name'])
    #             self.logger.info(f'正在获取 {row['name']} 成分股')
    #             stock_board_industry_cons_em_df = ak.stock_board_industry_cons_em(symbol=row['name'])
    #             print(stock_board_industry_cons_em_df)

    #             for index, stock_row in stock_board_industry_cons_em_df.iterrows():  # 获取板块内所有股票
    #                 stock_code = stock_row['code']
    #                 stock_name = stock_row['name']
    #                 industry_name = row['name']

    #                 # 如果 stock_code 不存在，插入新记录
    #                 if stock_code not in df_industry_board_cons_data:
    #                     df_industry_board_cons_data[stock_code] = {
    #                         'code': stock_code,
    #                         'name': stock_name,
    #                         'industries': [industry_name]  # 使用列表存储多个行业
    #                     }
    #                 else:
    #                     # 如果 stock_code 已存在，补充所属行业（去重）
    #                     if industry_name not in df_industry_board_cons_data[stock_code]['industries']:
    #                         df_industry_board_cons_data[stock_code]['industries'].append(industry_name)

    #         df_result = pd.DataFrame([
    #             {
    #                 'code': code,
    #                 'name': data['name'],
    #                 'industries': ','.join(data['industries'])  # 将行业列表转为逗号分隔字符串
    #             }
    #             for code, data in df_industry_board_cons_data.items()
    #         ])
    #         df_result['date'] = datetime.datetime.now().strftime('%Y-%m-%d')

    #         self.logger.info("处理完成，结果如下：")
    #         self.logger.info(df_result.tail(3))

    #         self.stock_info_db_base.insert_em_industry_board_cons_to_db(df_result)

    #         return True

    #     except Exception as e:
    #         self.logger.info(f"获取数据失败: {e}")
    #         return False
        
    #     return True

    def process_and_save_em_industry_board_cons(self):
        '''
            获取、处理并保存东方财富行业板块成分股，收盘后调用
        '''
        try:
            # 获取最新的行业板块数据
            latest_em_industry_board_data = self.get_latest_em_industry_board_data()
            if latest_em_industry_board_data is None or latest_em_industry_board_data.empty:
                self.logger.warning("未获取到行业板块数据")
                return False

            # 初始化 DataFrame 存储成分股数据
            df_industry_board_cons_data = pd.DataFrame(columns=['code', 'name', 'industry'])

            # 遍历每个行业板块
            for _, row in latest_em_industry_board_data.iterrows():
                sector_name = row['name']
                self.logger.info(f'正在获取 {sector_name} 成分股')

                try:
                    # 获取板块成分股数据
                    stock_board_industry_cons_em_df = ak.stock_board_industry_cons_em(symbol=sector_name)
                    if stock_board_industry_cons_em_df is None or stock_board_industry_cons_em_df.empty:
                        self.logger.warning(f"板块 {sector_name} 返回空数据")
                        continue

                    stock_board_industry_cons_em_df = stock_board_industry_cons_em_df.rename(columns={'代码': 'code', '名称': 'name'})

                    # 提取成分股信息并添加行业字段
                    temp_df = stock_board_industry_cons_em_df[['code', 'name']].copy()
                    temp_df['industry'] = sector_name

                    # 合并到主 DataFrame
                    df_industry_board_cons_data = pd.concat([df_industry_board_cons_data, temp_df], ignore_index=True)

                    sleep_time = random.uniform(1, 3)
                    time.sleep(sleep_time)

                except Exception as e:
                    self.logger.error(f"获取板块 {sector_name} 成分股失败: {e}")
                    break

            # 去重：同一股票在同一行业中不能重复记录
            df_industry_board_cons_data = df_industry_board_cons_data.drop_duplicates(subset=['code', 'industry'])

            # 添加日期字段
            df_industry_board_cons_data['date'] = datetime.datetime.now().strftime('%Y-%m-%d')

            # 打印处理结果
            self.logger.info("处理完成，结果如下：")
            self.logger.info(df_industry_board_cons_data.tail(3))

            # 保存到数据库
            self.stock_info_db_base.insert_em_industry_board_cons_to_db(df_industry_board_cons_data)

            return True

        except Exception as e:
            self.logger.error(f"处理东方财富行业板块成分股时发生未知错误: {e}")
            return False

    
    def query_em_industry_board_cons_data(self, code, date):
        pass

    def get_latest_em_industry_board_cons_data(self):
        return self.stock_info_db_base.get_latest_em_industry_board_cons_data()


    # ------------------------------------------------------------东方财富股票概念板块接口-----------------------------------------



    # ------------------------------------------------------------东方财富股票筹码分布表stock_chip_distribution_data_eastmoney接口-----------------------------------------
    def get_and_insert_eastmoney_stock_chip_distribution_data_to_db(self):
        pass

    def update_and_insert_eastmoney_stock_chip_distribution_data_to_db(self):
        pass

    def process_and_insert_eastmoney_stock_chip_distribution_data_to_db(self):
        # self.dict_chip_distribution_data_eastmoney.clear()
        for board, df_data in self.dict_stocks.items():
            # 检查 DataFrame 是否为空
            if board == "" or df_data.empty:
                continue

            if board == "bse" or board == "star":
                continue

            self.logger.info(f"正在处理 {board} 数据...")
            
            db_dir = self.stock_db_base.get_src_db_dir()
            db_dir = db_dir / board
            self.logger.info(f"db_dir: {db_dir}")
            self.stock_db_base.set_db_dir(db_dir)

            for index, row in df_data.iterrows():
                stock_code = row['证券代码']
                # self.logger.info("stock_code的类型：", type(stock_code))

                self.logger.info(f"正在获取第 {index} 只股票的筹码分布信息：{stock_code}")

                try:
                    # 注意：stock_cyq_em接口会超时
                    stock_cyq_em_df = ak.stock_cyq_em(symbol=stock_code, adjust="qfq")
                    # self.logger.info("stock_cyq_em_df的类型：", stock_cyq_em_df)

                    # if self.dict_chip_distribution_data_eastmoney[stock_code].empty:
                    #     # 不存在则全量更新
                    #     self.stock_db_base.insert_eastmoney_stock_chip_distribution_data_to_db(stock_code, stock_cyq_em_df)
                    #     # 优化：策略筛选只需要最后一行数据
                    #     self.dict_chip_distribution_data_eastmoney[stock_code] = stock_cyq_em_df
                    # else:
                    #     # 存在则增量更新
                    #     # combined_df = pd.concat([self.dict_chip_distribution_data_eastmoney[stock_code], stock_cyq_em_df], axis=0, ignore_index=True)
                    #     # 删除重复行（基于所有列）
                    #     # unique_df = combined_df.drop_duplicates()

                    #     self.dict_chip_distribution_data_eastmoney[stock_code]['日期'] = pd.to_datetime(self.dict_chip_distribution_data_eastmoney[stock_code]['日期'])
                    #     stock_cyq_em_df['日期'] = pd.to_datetime(stock_cyq_em_df['日期'])

                    #     # 找到 df1 中的最大日期（最后日期）
                    #     last_date_in_df1 = self.dict_chip_distribution_data_eastmoney[stock_code]['日期'].max()
                    #     self.logger.info(f"df1 中的最后日期是: {last_date_in_df1}")

                    #     # 在 df2 中筛选所有日期大于 df1 最后日期的行
                    #     new_data_in_df2 = stock_cyq_em_df[stock_cyq_em_df['日期'] > last_date_in_df1] # 使用布尔索引进行条件筛选[2](@ref)

                    #     # 显示新增的数据
                    #     self.logger.info(f"df2 中在 {last_date_in_df1} 之后的新增数据行数为: {len(new_data_in_df2)}")
                    #     self.logger.info(new_data_in_df2)

                        # # 新增数据添加到数据库中
                        # self.stock_db_base.insert_eastmoney_stock_chip_distribution_data_to_db(stock_code, new_data_in_df2)

                    # 获取到的数据直接插入，接口内部会做去重
                    self.stock_db_base.insert_eastmoney_stock_chip_distribution_data_to_db(stock_code, stock_cyq_em_df)

                    sleep_time = random.uniform(0.1, 0.5)
                    time.sleep(sleep_time)
                    
                except Exception as e:
                        self.logger.info(f"处理股票 {stock_code} 的筹码分布信息时出错: {e}")
                        continue
                

    def query_eastmoney_stock_chip_distribution_data(self):
        self.dict_chip_distribution_data_eastmoney.clear()
        for board, df_data in self.dict_stocks.items():
            # 检查 DataFrame 是否为空
            if board == "" or df_data.empty:
                continue
            
            db_dir = self.stock_db_base.get_src_db_dir()
            db_dir = db_dir / board
            self.logger.info(f"db_dir: {db_dir}")
            self.stock_db_base.set_db_dir(db_dir)
            for index, row in df_data.iterrows():
                stock_code = row['证券代码']
                df_chip_distribution_data = self.stock_db_base.query_eastmoney_stock_chip_distribution_data(stock_code)

                # 优化：策略筛选只需要最后一行数据
                self.dict_chip_distribution_data_eastmoney[stock_code] = df_chip_distribution_data

    def get_latest_eastmoney_stock_chip_distribution_data(self, code):
        pass

    # ------------------------------------------------------------东方财富人气榜股票表接口-----------------------------------------
    def get_popularity_rank_stock_data_from_eastmoney(self):
        # 获取人气榜
        try:
            df = ak.stock_hot_rank_em()
            # print(stock_hot_rank_em_df)
            self.logger.info(f"获取数据成功")
            self.logger.info(df)
        except Exception as e:
            self.logger.info(f"获取数据失败: {e}")
            return False
        
        # 添加日期字段
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        df['日期'] = today

        return self.stock_info_db_base.insert_popularity_rank_stock_data_to_db(df)
    
    def query_popularity_rank_stock_data(self, date=None, industry_name=None):
        return self.stock_info_db_base.query_popularity_rank_stock_data(date, industry_name)

    def get_latest_popularity_rank_stock_data(self):
        return self.stock_info_db_base.get_latest_popularity_rank_stock_data()

    # ------------------------------------------------------------东方财富人气飙升榜股票表接口-----------------------------------------

    # ------------------------------------------------------------暂不需要：东方财富股票历史趋势及粉丝特征表接口-----------------------------------------


    # ------------------------------------------------------------暂不需要：东方财富个股人气榜-实时变动表接口-----------------------------------------

    # ------------------------------------------------------------乐咕每日赚钱效应-----------------------------------------
    def process_market_activity_legu(self):
        stock_market_activity_legu_df = ak.stock_market_activity_legu()
        self.logger.info(f'stock_market_activity_legu_df 类型：{type(stock_market_activity_legu_df)}')
        self.logger.info(f'stock_market_activity_legu_df: {stock_market_activity_legu_df}')

        today = datetime.datetime.now().strftime('%Y-%m-%d')
        stock_market_activity_legu_df['date'] = today

        return self.stock_info_db_base.save_market_activity_legu(stock_market_activity_legu_df)
    
    def query_market_activity_legu_data(self, date=None, item=None):
        return self.stock_info_db_base.query_market_activity_legu_data(date, item)
    def get_latest_market_activity_legu_data(self):
        return self.stock_info_db_base.get_latest_market_activity_legu_data()




# 测试代码
if __name__ == "__main__":
    # 测试函数
    # test_stock_code = "000001"
    
    # 测试获取最近一个交易日的数据
    # latest_daily_result = process_latest_daily_data(test_stock_code)
    # self.logger.info(f"最近交易日数据处理结果: {'成功' if latest_daily_result else '失败'}")
    
    # 测试获取最近一周的周线数据
    # latest_weekly_result = process_latest_weekly_data(test_stock_code)
    # self.logger.info(f"最近周线数据处理结果: {'成功' if latest_weekly_result else '失败'}")
    print("stock_data_processor.py run")