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

class TuShareStockBasicInfoDB(CommonDBBase):
    """
    股票数据库管理类，用于管理stocks/db/stocks.db股票数据库, 存储的是A股所有非ST股票信息
    day目录：存储日线数据
    two_days目录：存储两日线数据
    three_days目录：存储三日线数据
    week目录：存储周线数据
    month目录：存储月线数据
    """
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TuShareStockBasicInfoDB, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.logger = get_logger(__name__)

        self.trade_calendar_table = "trade_calendar"
        self.stocks_basic_info_table = "stock_basic_info"

        db_path_tmp = self._get_db_path()
        
        # 调用父类构造函数
        super().__init__(db_path_tmp)
        self.logger.info("TuShareStockBasicInfoDB--self._init_db()")
        self._init_db()

    def _get_db_path(self):
        """获取数据库路径"""
        return str(get_database_root("tushare") / "stocks.db")


    def _init_db(self):
        """初始化数据库表结构"""
        self.create_trade_calendar_table()
        self.create_stocks_basic_info_table()
        self.logger.info(f"股票基本信息数据库已初始化: {self.db_path}")

    def create_trade_calendar_table(self):
        '''
            创建交易日历表
            字段说明：
                exchange: 交易所代码， SSE上交所 SZSE深交所
                cal_date: 日历日期
                is_open: 是否交易，0休市1交易
                pretrade_date: 上一交易日
                update_at: 更新时间
                created_at: 创建时间
        '''
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.trade_calendar_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                cal_date TEXT NOT NULL,
                is_open TEXT NOT NULL,
                pretrade_date TEXT NOT NULL,
                update_at DATE NOT NULL DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cal_date, update_at)
            )
            """
        self.create_table(self.trade_calendar_table, create_table_sql)

    def create_stocks_basic_info_table(self):
        '''
            创建股票基本信息表
            字段说明：
                ts_code: TS代码
                symbol: 股票代码
                name: 股票名称
                area: 所在地域
                industry: 所属行业
                fullname: 股票全称
                enname: 英文全称
                cnspell: 拼音缩写
                market: 市场(主板/创业板/科创板/CDR)
                exchange: 交易所代码
                curr_type: 交易货币
                list_status: 上市状态，L上市 D退市 G过会未交易 P暂停上市 UN未上市
                list_date: 上市日期
                delist_date: 退市日期
                is_hs: 是否沪深港通标的, N否 H沪股通 S深股通
                act_name: 实控人名称
                act_ent_type: 实控人企业性质
        '''
        create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.stocks_basic_info_table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    name TEXT NOT NULL,
                    area TEXT DEFAULT '',
                    industry TEXT DEFAULT '',
                    fullname TEXT DEFAULT '',
                    enname TEXT DEFAULT '',
                    cnspell TEXT DEFAULT '',
                    market TEXT DEFAULT '',
                    exchange TEXT DEFAULT '',
                    curr_type TEXT DEFAULT '',
                    list_status TEXT DEFAULT '',
                    list_date TEXT DEFAULT '',
                    delist_date TEXT DEFAULT '',
                    is_hs TEXT DEFAULT '',
                    act_name TEXT DEFAULT '',
                    act_ent_type TEXT DEFAULT '',

                    is_deleted INTEGER  NOT NULL DEFAULT 0,
                    version Text NOT NULL DEFAULT '1.0.0',
                    update_at DATE NOT NULL DEFAULT CURRENT_DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ts_code, symbol, update_at)
                )
                """
        self.create_table(self.stocks_basic_info_table, create_table_sql)

    def save_data(self, df_data, table_name, list_conflict_columns):
        try:
            # 使用upsert插入数据
            inserted_count = self.upsert_data(
                table_name,
                df_data.to_dict('records'),
                conflict_columns=list_conflict_columns  # 明确指定冲突检测列
            )
            
            self.logger.info(f"成功保存 {inserted_count} 条 {table_name} 数据")
            return inserted_count
        except Exception as e:
            self.logger.error(f"插入数据失败: {e}")
            return 0

    def query_lastest_db_data(self, table_name):
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

    def save_trade_calendar(self, trade_calendar_data):
        return self.save_data(trade_calendar_data, self.trade_calendar_table, ['cal_date', 'update_at'])

    def query_lastest_trade_calendar(self):
        return self.query_lastest_db_data(self.trade_calendar_table)

    def clear_trade_calendar_db_data(self):
        self.truncate_table(self.trade_calendar_table)

    def save_stock_basic_info(self, stock_basic_info_data):
        return self.save_data(stock_basic_info_data, self.stocks_basic_info_table, ['ts_code', 'symbol', 'update_at'])

    def query_lastest_stock_basic_info(self):
        return self.query_lastest_db_data(self.stocks_basic_info_table)

    def clear_stock_basic_info_db_data(self):
        self.truncate_table(self.stocks_basic_info_table)