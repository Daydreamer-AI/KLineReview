import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime
import pandas as pd
import threading
import time
import numpy as np
from db_base.common_db_base import CommonDBBase
from manager.logging_manager import get_logger
from common.common_api import *
from common.paths import get_database_root

class StockInfoDBBasePool:
    """管理多个 StockInfoDBBase 实例的池（单例模式）"""
    
    # 使用类变量存储唯一实例，并添加volatile语义（通过线程锁保证可见性）
    _instance = None
    _lock = threading.RLock()  # 使用可重入锁
    
    def __new__(cls):
        """重写 __new__ 方法控制实例创建"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    # 初始化实例变量
                    cls._instance._managers = {}
        return cls._instance
    
    def __init__(self):
        """初始化方法"""
        # 确保只初始化一次
        if not hasattr(self, '_initialized'):
            with self._lock:
                if not hasattr(self, '_initialized'):
                    self._managers = {}
                    self._initialized = True
    
    def get_manager(self, db_type, key=None):
        """获取指定类型的数据库管理器实例"""
        if key is None:
            key = f"default_{db_type}"
            
        # 只使用一个锁
        if key not in self._managers:
            with self._lock:  # 使用类级别的锁
                if key not in self._managers:
                    self._managers[key] = StockInfoDBBase(db_type)
        return self._managers[key]
            
    def close_all(self):
        """关闭所有数据库管理器"""
        with self._lock:
            for key, manager in list(self._managers.items()):
                manager.close_connection()
                del self._managers[key]
                
    def __del__(self):
        """析构时自动关闭所有连接"""
        self.close_all()

class StockInfoDBBase(CommonDBBase):
    """
    股票数据库管理类，用于管理stocks/db/stocks.db股票数据库, 存储的是A股所有非ST股票信息
    day目录：存储日线数据
    two_days目录：存储两日线数据
    three_days目录：存储三日线数据
    week目录：存储周线数据
    month目录：存储月线数据
    """
    
    def __init__(self, db_type = 0):
        self.logger = get_logger(__name__)
        self.db_type = db_type
        db_path_tmp = self._get_db_path_by_type(db_type)
        
        # 调用父类构造函数
        super().__init__(db_path_tmp)
        self.logger.info("StockInfoDBBase--self._init_db()")
        self._init_db()

    def _get_db_path_by_type(self, db_type):
        """根据db_type获取数据库路径"""
        if db_type == 1:
            return str(get_database_root("baostock") / "stocks.db")
        elif db_type == 2:
            return str(get_database_root("efinance") / "stocks.db")
        else:
            return str(get_database_root("akshare") / "stocks.db")

    def init_baostock_db(self):
        self.create_baostock_stocks_info_table()

    def init_efinance_db(self):
        pass

    def _init_db(self):
        """初始化数据库表结构"""
        # with self._lock:
        # 创建股票基本信息表
        #MAIN    ​主板    上交所 + 深交所
        #GEM     ​创业板   深交所
        #STAR    ​科创板   上交所
        #BSE     ​北交所   深交所
        # 调用相应的初始化方法
        if self.db_type == 0:
            self.init_akshare_db()
        elif self.db_type == 1:
            self.init_baostock_db()
        elif self.db_type == 2:
            self.init_efinance_db()
        self.logger.info(f"股票数据库已初始化: {self.db_path}")

    def create_baostock_stocks_info_table(self):
        create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS stock_basic_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    trade_status TEXT NOT NULL,
                    name TEXT NOT NULL,
                    is_deleted INTEGER  NOT NULL DEFAULT 0,
                    version Text NOT NULL DEFAULT '1.0.0',
                    update_at DATE NOT NULL DEFAULT CURRENT_DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(code, update_at)
                )
                """
        self.create_table('stock_basic_info', create_table_sql)


    # ========================================================================AKShare相关接口========================================================================
    # AKShare
    def init_akshare_db(self):
        """初始化AKShare数据库表结构"""
        pass


    # ========================================================================BaoStock相关接口========================================================================
    def save_bao_stock_trade_dates(self, trade_dates, table_name="trade_dates"):
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,      -- 添加自增ID作为主键
            "date" DATE NOT NULL,
            "is_trading_day" TEXT NOT NULL,
            "update_date" DATE NOT NULL DEFAULT CURRENT_DATE,
            "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE("date", "update_date")              -- 保持复合唯一约束
        )
        """
        self.create_table(table_name, create_table_sql)

        try:
            # 使用upsert插入数据
            inserted_count = self.upsert_data(
                table_name,
                trade_dates.to_dict('records'),
                conflict_columns=['date', 'update_date']  # 明确指定冲突检测列
            )
            
            self.logger.info(f"成功保存 {inserted_count} 条 {table_name} 交易日数据")
            return inserted_count
        except Exception as e:
            self.logger.error(f"插入数据失败: {e}")
            return False
        
    def query_newest_bao_stock_trade_dates(self, table_name="trade_dates"):
        try:
            with self._get_connection() as cur:
                cur.execute(f'''
                    SELECT * FROM {table_name} 
                    WHERE update_date = (SELECT MAX(update_date) FROM {table_name})
                ''')
                
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                
                if rows:
                    return pd.DataFrame(rows, columns=column_names)
                else:
                    return pd.DataFrame()
                    
        except Exception as e:
            self.logger.info(f"获取最新的交易日信息数据时出错: {str(e)}")
            return pd.DataFrame()

    # Baostock
    def save_bao_stocks_to_db(self, stocks_data, table_name="stock_basic_info"):
        """
        线程安全地保存股票数据到数据库
        
        :param stocks_data: 股票数据 (pandas.DataFrame)
        :param writeWay: 写入方式 ("replace", "append", "fail")
        :param table_name: 表名
        :return: 插入的行数
        """
        allowed_table_names = ['stock_basic_info', 'sh_main', 'sz_main', 'gem', 'star', 'bse']
        if table_name not in allowed_table_names:
            raise ValueError(f"Invalid table name: {table_name}")

        # 确保表存在 - 使用复合唯一键，不设主键
        self.create_baostock_stocks_info_table()
        
        # 数据预处理
        if not stocks_data.empty:
            try:
                # 使用upsert插入数据
                inserted_count = self.upsert_data(
                    table_name,
                    stocks_data.to_dict('records'),
                    conflict_columns=['code', 'update_at']  # 明确指定冲突检测列
                )
                
                self.logger.info(f"成功保存 {inserted_count} 条 {table_name} 股票数据")
                return True
            except Exception as e:
                self.logger.error(f"插入数据失败: {e}")
                return False
        
        self.logger.info(f"没有数据需要保存到 {table_name}")
        return True

    def get_stocks_with_filter(self, table_name, status_filter=None):
        """
        获取股票数据并支持状态过滤
        
        :param table_name: 表名
        :param status_filter: 交易状态过滤条件
        :return: DataFrame格式的股票数据
        """
        df = self.get_table_data(table_name)
        
        if status_filter and not df.empty:
            df = df[df['trade_status'] == status_filter]
        
        return df

    def get_lastest_stocks(self, table_name='stock_basic_info'):
        """获取最新日期的股票信息数据"""
        try:
            with self._get_connection() as cur:
                cur.execute(f'''
                    SELECT * FROM {table_name} 
                    WHERE update_at = (SELECT MAX(update_at) FROM {table_name})
                ''')
                
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                
                if rows:
                    return pd.DataFrame(rows, columns=column_names)
                else:
                    return pd.DataFrame()
                    
        except Exception as e:
            self.logger.info(f"获取最新日期的股票信息数据时出错: {str(e)}")
            return pd.DataFrame()


# 测试代码
if __name__ == "__main__":
    # self.logger.info("stocks_db_manager.py run")
    pass
