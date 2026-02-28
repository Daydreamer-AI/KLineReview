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
            return "./data/database/stocks/db/baostock/stocks.db"
        elif db_type == 2:
            return "./data/database/stocks/db/efinance/stocks.db"
        else:
            return "./data/database/stocks/db/akshare/stocks.db"

    def init_baostock_db(self):
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS stock_basic_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,      -- 添加自增ID作为主键
            "证券代码" TEXT NOT NULL,
            "交易状态" TEXT NOT NULL,
            "证券名称" TEXT NOT NULL,
            "更新日期" DATE NOT NULL DEFAULT CURRENT_DATE,
            "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE("证券代码", "更新日期")              -- 保持复合唯一约束
        )
        """
        self.create_table('stock_basic_info', create_table_sql)

    def init_efinance_db(self):
        self.create_table('stock_basic_info', '''
                    CREATE TABLE IF NOT EXISTS stock_basic_info (
                        stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        stock_code VARCHAR(10) NOT NULL UNIQUE,
                        stock_name VARCHAR(50) NOT NULL,
                        board_type TEXT CHECK(board_type IN ('MAIN','GEM','STAR','BSE')),
                        is_st BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

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

    # ========================================================================AKShare相关接口========================================================================
    # AKShare
    def init_akshare_db(self):
        """初始化AKShare数据库表结构"""
        
        # 1. 创建A股所有股票表 - 使用父类方法（推荐）
        self.create_table('stock_basic_info', '''
            CREATE TABLE IF NOT EXISTS stock_basic_info (
                证券代码 TEXT PRIMARY KEY NOT NULL,
                证券名称 TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. 创建同花顺行业板块一览表 - 使用父类方法
        self.create_table('board_industry', '''
            CREATE TABLE IF NOT EXISTS board_industry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number INTEGER NOT NULL,
                industry_name TEXT NOT NULL,
                change_percent REAL NOT NULL,
                total_volume REAL NOT NULL,
                total_amount REAL NOT NULL,
                net_inflow REAL NOT NULL,
                rising_count INTEGER NOT NULL,
                falling_count INTEGER NOT NULL,
                avg_price REAL NOT NULL,
                leading_stock TEXT NOT NULL,
                leading_stock_price REAL NOT NULL,
                leading_stock_change_percent REAL NOT NULL,
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(industry_name, date)  -- 关键：基于行业名称和日期的唯一约束
            )
        ''')

        # 创建同花顺概念板块信息表 - ths_board_concept_info
        self.create_table('ths_board_concept_info', '''
            CREATE TABLE IF NOT EXISTS ths_board_concept_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concept_name TEXT NOT NULL,
                concept_code TEXT NOT NULL,
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(concept_name, concept_code, date)  -- 关键：基于概念名称和日期的唯一约束
            )
        ''')

        # 创建同花顺概念板块一览表 - ths_board_concept_overview
        self.create_table('ths_board_concept_overview', '''
        CREATE TABLE IF NOT EXISTS ths_board_concept_overview (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept_name TEXT NOT NULL,
            concept_code TEXT NOT NULL,
            open_price REAL,
            previous_close REAL,
            low_price REAL,
            high_price REAL,
            volume REAL,
            board_change_percent REAL,
            change_rank TEXT,
            rise_fall_count TEXT,
            net_inflow REAL,
            turnover REAL,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(concept_name, concept_code, date)
        )
    ''')

        # 3. 创建东方财富股票数据表 - 使用父类方法
        self.create_table('stock_data_eastmoney', '''
            CREATE TABLE IF NOT EXISTS stock_data_eastmoney (
                stock_code TEXT NOT NULL,
                date TEXT NOT NULL,
                latest_price REAL,
                stock_name TEXT,
                total_shares REAL,
                float_shares REAL,
                total_market_cap REAL,
                float_market_cap REAL,
                industry TEXT,
                list_date TEXT,
                PRIMARY KEY (stock_code, date)
            )
        ''')

        # 创建东方财富股票人气表
        self.create_table('stock_popularity_eastmoney', '''
            CREATE TABLE IF NOT EXISTS stock_popularity_eastmoney (
                rank INTEGER NOT NULL,
                stock_code TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                latest_price REAL NOT NULL,
                change_amount REAL NOT NULL,
                change_percent REAL NOT NULL,
                date TEXT NOT NULL,
                PRIMARY KEY (stock_code, date)
            )
        ''')

        # 创建东方财富行业板块一览表
        self.create_table('em_industry_board_data', '''
            CREATE TABLE IF NOT EXISTS em_industry_board_data (
                rank INTEGER NOT NULL,
                name TEXT NOT NULL,
                code TEXT NOT NULL,
                latest_price REAL NOT NULL,
                change_amount REAL NOT NULL,
                change_percent REAL NOT NULL,
                market_cap REAL NOT NULL,
                turnover_rate REAL NOT NULL,
                rising_count INTEGER NOT NULL,
                falling_count INTEGER NOT NULL,
                leading_stock TEXT NOT NULL,
                leading_stock_change_percent REAL NOT NULL,     
                date TEXT NOT NULL,
                PRIMARY KEY (name, code, date)
            )
        ''')

        # 东方财富行业板块成分股表
        self.create_table('stock_industry_board_cons_data_em', '''
            CREATE TABLE IF NOT EXISTS stock_industry_board_cons_data_em (
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                industry TEXT NOT NULL,
                date DATE NOT NULL,
                PRIMARY KEY (code, industry, date)
            )
        ''')


        # 创建市场情绪表
        self.create_table('market_activity_legu', '''
            CREATE TABLE IF NOT EXISTS market_activity_legu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL,
                value TEXT NOT NULL,
                date TEXT NOT NULL
            )
        ''')


        # 4. 创建索引 - 使用专门的方法或直接SQL
        try:
            with self._get_connection() as cur:
                # 同花顺行业板块索引
                cur.execute('CREATE INDEX IF NOT EXISTS idx_board_industry_date ON board_industry(date)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_board_industry_industry_name ON board_industry(industry_name)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_board_industry_change_percent ON board_industry(change_percent)')

                # 同花顺概念板块信息表索引
                cur.execute('CREATE INDEX IF NOT EXISTS idx_ths_board_concept_info_name ON ths_board_concept_info(concept_name)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_ths_board_concept_info_code ON ths_board_concept_info(concept_code)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_ths_board_concept_info_date ON ths_board_concept_info(date)')

                # 同花顺概念板块一览索引
                cur.execute('CREATE INDEX IF NOT EXISTS idx_ths_board_concept_overview_name ON ths_board_concept_overview(concept_name)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_ths_board_concept_overview_code ON ths_board_concept_overview(concept_code)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_ths_board_concept_overview_date ON ths_board_concept_overview(date)')
                
                # 东方财富股票数据索引
                cur.execute('CREATE INDEX IF NOT EXISTS idx_stock_data_eastmoney_stock_code ON stock_data_eastmoney(stock_code)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_stock_data_eastmoney_data_date ON stock_data_eastmoney(date)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_stock_data_eastmoney_industry_name ON stock_data_eastmoney(industry)')

                # 东方财富股票人气索引
                cur.execute('CREATE INDEX IF NOT EXISTS idx_stock_popularity_eastmoney_stock_code ON stock_popularity_eastmoney(stock_code)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_stock_popularity_eastmoney_date ON stock_popularity_eastmoney(date)')

                # 东方财富行业板块信息表索引
                cur.execute('CREATE INDEX IF NOT EXISTS idx_em_industry_board_data_name ON em_industry_board_data(name)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_em_industry_board_data_code ON em_industry_board_data(code)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_em_industry_board_data_date ON em_industry_board_data(date)')

                # 东方财富行业板块成分股表索引
                cur.execute('CREATE INDEX IF NOT EXISTS idx_stock_industry_board_cons_data_em_code ON stock_industry_board_cons_data_em(code)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_stock_industry_board_cons_data_em_industry ON stock_industry_board_cons_data_em(industry)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_stock_industry_board_cons_data_em_date ON stock_industry_board_cons_data_em(date)')

                # 市场情绪表索引
                cur.execute('CREATE INDEX IF NOT EXISTS idx_market_activity_legu_date ON market_activity_legu(date)')

                
            self.logger.info("所有索引创建成功")
            
        except sqlite3.Error as e:
            self.logger.info(f"创建索引时发生数据库错误: {str(e)}")
            raise
        except Exception as e:
            self.logger.info(f"创建索引时发生错误: {str(e)}")
            raise
    # ------------------------------------------------------------A股股票信息表接口----------------------------------------------

    # ------------------------------------------------------------同花顺行业板块一览表接口-----------------------------------------
    def insert_ths_board_industry_data_to_db(self, df_industry_data):
        try:
            # 重命名列以匹配数据库表结构
            df = df_industry_data.rename(columns={
                '序号': 'serial_number',
                '板块': 'industry_name',
                '涨跌幅': 'change_percent',
                '总成交量': 'total_volume',
                '总成交额': 'total_amount',
                '净流入': 'net_inflow',
                '上涨家数': 'rising_count',
                '下跌家数': 'falling_count',
                '均价': 'avg_price',
                '领涨股': 'leading_stock',
                '领涨股-最新价': 'leading_stock_price',
                '领涨股-涨跌幅': 'leading_stock_change_percent',
                '日期': 'date'
            })
            
            # 使用 replace 模式，配合 UNIQUE(industry_name, date) 约束实现更新
            # 问题：会删除掉旧数据，不适用
            # inserted_count = self.insert_dataframe_to_table(
            #     'board_industry', df, 'replace',  # 使用 replace 模式
            #     validate_columns=False, fast_mode=False  # 不使用快速模式以确保约束生效
            # )
        
            # self.logger.info(f"数据插入完成，处理了 {inserted_count} 条记录")
            # return True
        
            # 方式二：使用 upsert 功能，明确指定冲突列
            upserted_count = self.upsert_data(
                'board_industry',
                df.to_dict('records'),
                conflict_columns=['industry_name', 'date']  # 明确指定冲突检测列
            )
            
            self.logger.info(f"数据upsert完成，处理了 {upserted_count} 条记录")
            return True

            
        except Exception as e:
            self.logger.info(f"插入数据失败: {e}")
            return False

    def query_ths_board_industry_data(self, date=None, industry_name=None):
        """查询行业数据"""
        conditions = []
        params = []
        
        if date:
            conditions.append("date = ?")
            params.append(date)
        
        if industry_name:
            conditions.append("industry_name LIKE ?")
            params.append(f"%{industry_name}%")

        query = "SELECT * FROM board_industry"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY date DESC, change_percent DESC"
        
        try:
            with self._get_connection() as cur:
                cur.execute(query, params)
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=column_names)
        except Exception as e:
            self.logger.info(f"查询同花顺行业板块一览表时出错: {str(e)}")
            return pd.DataFrame()

    def get_latest_ths_board_industry_data(self):
        """获取最新日期的所有行业数据"""
        try:
            with self._get_connection() as cur:
                cur.execute('''
                    SELECT * FROM board_industry 
                    WHERE date = (SELECT MAX(date) FROM board_industry)
                    ORDER BY change_percent DESC
                ''')
                
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                
                if rows:
                    return pd.DataFrame(rows, columns=column_names)
                else:
                    return pd.DataFrame()
                    
        except Exception as e:
            self.logger.info(f"查询同花顺行业板块一览表时出错: {str(e)}")
            return pd.DataFrame()


    # ------------------------------------------------------------同花顺概念板块信息表接口-----------------------------------------
    def insert_ths_concept_board_info_to_db(self, df_concept_data):
        try:
            df = df_concept_data.rename(columns={
                'name': 'concept_name',
                'code': 'concept_code'
            })

            upserted_count = self.upsert_data(
                'ths_board_concept_info',
                df.to_dict('records'),
                conflict_columns=['concept_name', 'concept_code', 'date']  # 明确指定冲突检测列，需和表定义中的UNIQUE一致
            )
            
            self.logger.info(f"数据upsert完成，处理了 {upserted_count} 条记录")
            return True

            
        except Exception as e:
            self.logger.info(f"插入数据失败: {e}")
            return False
        
    def get_latest_ths_concept_board_info(self):
        try:
            with self._get_connection() as cur:
                cur.execute('''
                    SELECT * FROM ths_board_concept_info 
                    WHERE date = (SELECT MAX(date) FROM ths_board_concept_info)
                    ORDER BY concept_name DESC
                ''')
                
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                
                if rows:
                    return pd.DataFrame(rows, columns=column_names)
                else:
                    return pd.DataFrame()
                    
        except Exception as e:
            self.logger.info(f"查询同花顺概念板块一览表时出错: {str(e)}")
            return pd.DataFrame()
        
    # ------------------------------------------------------------同花顺概念板块概览表接口-----------------------------------------
    def insert_ths_board_concept_overview(self, concept_name, concept_code, df_detail):
        """插入概念板块详细信息"""
        try:
            # 转换DataFrame格式
            data_dict = {
                'concept_name': concept_name,
                'concept_code': concept_code,
                'date': datetime.now().strftime('%Y-%m-%d')
            }
            
            # 解析DataFrame中的键值对
            for _, row in df_detail.iterrows():
                item = row['项目']
                value = row['值']
                
                if item == '今开':
                    data_dict['open_price'] = convert_to_float(value)
                elif item == '昨收':
                    data_dict['previous_close'] = convert_to_float(value)
                elif item == '最低':
                    data_dict['low_price'] = convert_to_float(value)
                elif item == '最高':
                    data_dict['high_price'] = convert_to_float(value)
                elif item == '成交量(万手)':
                    data_dict['volume'] = convert_to_float(value)
                elif item == '板块涨幅':
                    data_dict['board_change_percent'] = convert_percentage(value)
                elif item == '涨幅排名':
                    data_dict['change_rank'] = str(value)
                elif item == '涨跌家数':
                    data_dict['rise_fall_count'] = str(value)
                elif item == '资金净流入(亿)':
                    data_dict['net_inflow'] = convert_to_float(value)
                elif item == '成交额(亿)':
                    data_dict['turnover'] = convert_to_float(value)
            
            # 使用upsert插入数据
            upserted_count = self.upsert_data(
                'ths_board_concept_overview',
                [data_dict],
                conflict_columns=['concept_name', 'concept_code', 'date']
            )
            
            self.logger.info(f"概念板块详细信息upsert完成，处理了 {upserted_count} 条记录")
            return True
            
        except Exception as e:
            self.logger.error(f"插入概念板块详细信息失败: {e}")
            return False

    def query_ths_board_concept_overview(self, concept_name=None, date=None):
        """查询概念板块详细信息"""
        conditions = []
        params = []
        
        if concept_name:
            conditions.append("concept_name = ?")
            params.append(concept_name)
        
        if date:
            conditions.append("date = ?")
            params.append(date)

        query = "SELECT * FROM ths_board_concept_overview"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY date DESC, concept_name"
        
        try:
            with self._get_connection() as cur:
                cur.execute(query, params)
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=column_names)
        except Exception as e:
            self.logger.error(f"查询概念板块详细信息时出错: {str(e)}")
            return pd.DataFrame()
        
    def get_latest_ths_concept_board_overview(self):
        try:
            with self._get_connection() as cur:
                cur.execute('''
                    SELECT * FROM ths_board_concept_overview 
                    WHERE date = (SELECT MAX(date) FROM ths_board_concept_overview)
                    ORDER BY board_change_percent DESC
                ''')
                
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                
                if rows:
                    return pd.DataFrame(rows, columns=column_names)
                else:
                    return pd.DataFrame()
                    
        except Exception as e:
            self.logger.info(f"查询同花顺概念板块一览表时出错: {str(e)}")
            return pd.DataFrame()
    # ------------------------------------------------------------东方财富股票数据表stock_data_eastmoney接口-----------------------------------------
    def insert_eastmoney_stock_data_to_db(self, df_stock_data):
        try:
            # 重命名列以匹配数据库表结构
            df_filtered = df_stock_data.rename(columns={
                '股票代码': 'stock_code',
                '日期': 'date',
                '最新': 'latest_price',
                '股票简称': 'stock_name',
                '总股本': 'total_shares',
                '流通股': 'float_shares',
                '总市值': 'total_market_cap',
                '流通市值': 'float_market_cap',
                '行业': 'industry',
                '上市时间': 'list_date'
            })
            
            # 处理特殊数据
            if 'latest_price' in df_filtered.columns:
                df_filtered['latest_price'] = df_filtered['latest_price'].apply(
                    lambda x: None if x == '-' or pd.isna(x) else float(x)
                )
            
            # 使用 upsert 功能，基于股票代码和日期的复合主键进行更新
            upserted_count = self.upsert_data(
                'stock_data_eastmoney',
                df_filtered.to_dict('records'),
                conflict_columns=['stock_code', 'date']  # 基于股票代码和日期的冲突检测
            )
            
            self.logger.info(f"数据upsert完成，处理了 {upserted_count} 条记录")
            return True
                
        except Exception as e:
            self.logger.info(f"插入数据失败: {e}")
            return False

    def query_eastmoney_stock_data(self, date=None, stock_code=None, industry_name=None):
        """查询东方财富股票数据"""
        conditions = []
        params = []
        
        if date:
            conditions.append("date = ?")
            params.append(date)
        
        if stock_code:
            conditions.append("stock_code = ?")
            params.append(stock_code)
        
        if industry_name:
            conditions.append("industry LIKE ?")
            params.append(f"%{industry_name}%")

        query = "SELECT * FROM stock_data_eastmoney"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY date DESC, stock_code"
        
        try:
            with self._get_connection() as cur:
                cur.execute(query, params)
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=column_names)
        except Exception as e:
            self.logger.info(f"查询东方财富股票数据表时出错: {str(e)}")
            return pd.DataFrame()

    def get_latest_eastmoney_stock_data(self):
        """获取最新日期的所有股票数据"""
        try:
            with self._get_connection() as cur:
                cur.execute('''
                    SELECT * FROM stock_data_eastmoney 
                    WHERE date = (SELECT MAX(date) FROM stock_data_eastmoney)
                    ORDER BY date DESC
                ''')
                
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                
                if rows:
                    return pd.DataFrame(rows, columns=column_names)
                else:
                    return pd.DataFrame()
                    
        except Exception as e:
            self.logger.info(f"查询东方财富股票数据表时出错: {str(e)}")
            return pd.DataFrame()

    def get_stock_data_by_code(self, stock_code, limit_days=30):
        """获取指定股票最近N天的数据"""
        try:
            with self._get_connection() as cur:
                cur.execute('''
                    SELECT * FROM stock_data_eastmoney 
                    WHERE stock_code = ?
                    ORDER BY date DESC
                    LIMIT ?
                ''', (stock_code, limit_days))
                
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                
                if rows:
                    return pd.DataFrame(rows, columns=column_names)
                else:
                    return pd.DataFrame()
                    
        except Exception as e:
            self.logger.info(f"查询东方财富股票数据表时出错: {str(e)}")
            return pd.DataFrame()


    # ------------------------------------------------------------东方财富股票行业板块接口-----------------------------------------
    def insert_em_industry_board_data_to_db(self, df_industry_data):
        try:
            # 重命名列以匹配数据库表结构
            df = df_industry_data.rename(columns={
                '排名': 'rank',
                '板块名称': 'name',
                '板块代码': 'code',
                '最新价':'latest_price',
                '涨跌额': 'change_amount',
                '涨跌幅': 'change_percent',
                '总市值': 'market_cap',
                '换手率': 'turnover_rate',
                '上涨家数': 'rising_count',
                '下跌家数': 'falling_count',
                '领涨股票': 'leading_stock',
                '领涨股票-涨跌幅': 'leading_stock_change_percent',
                '日期': 'date'
            })
            
        
            # 使用 upsert 功能，明确指定冲突列
            upserted_count = self.upsert_data(
                'em_industry_board_data',
                df.to_dict('records'),
                conflict_columns=['name', 'code', 'date']  # 明确指定冲突检测列
            )
            
            self.logger.info(f"数据upsert完成，处理了 {upserted_count} 条记录")
            return True

            
        except Exception as e:
            self.logger.info(f"插入数据失败: {e}")
            return False
        
    def query_em_industry_board_data(self, date=None, industry_name=None):
        """查询行业数据"""
        conditions = []
        params = []
        
        if date:
            conditions.append("date = ?")
            params.append(date)
        
        if industry_name:
            conditions.append("industry_name LIKE ?")
            params.append(f"%{industry_name}%")

        query = "SELECT * FROM em_industry_board_data"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY date DESC, change_percent DESC"
        
        try:
            with self._get_connection() as cur:
                cur.execute(query, params)
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=column_names)
        except Exception as e:
            self.logger.info(f"查询东方财富行业板块一览表时出错: {str(e)}")
            return pd.DataFrame()
        
    def get_latest_em_industry_board_data(self):
        """获取最新日期的所有行业数据"""
        try:
            with self._get_connection() as cur:
                cur.execute('''
                    SELECT * FROM em_industry_board_data 
                    WHERE date = (SELECT MAX(date) FROM em_industry_board_data)
                    ORDER BY change_percent DESC
                ''')
                
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                
                if rows:
                    return pd.DataFrame(rows, columns=column_names)
                else:
                    return pd.DataFrame()
                    
        except Exception as e:
            self.logger.info(f"查询东方财富行业板块一览表时出错: {str(e)}")
            return pd.DataFrame()
        
    # ------------------------------------------------------------东方财富股票行业板块成分股接口-----------------------------------------
    def insert_em_industry_board_cons_to_db(self, df):
        try:
            # 使用 upsert 功能，明确指定冲突列
            upserted_count = self.upsert_data(
                'stock_industry_board_cons_data_em',
                df.to_dict('records'),
                conflict_columns=['code', 'industry', 'date']  # 明确指定冲突检测列
            )
            
            self.logger.info(f"数据upsert完成，处理了 {upserted_count} 条记录")
            return True
            
        except Exception as e:
            self.logger.info(f"插入数据失败: {e}")
            return False
        
    def query_em_industry_board_cons_data(self, code=None, industry=None, date=None):
        """
        查询东方财富行业板块成分股数据
        
        :param code: 股票代码（可选）
        :param industry: 行业名称（可选）
        :param date: 查询日期（可选）
        :return: 返回查询结果的 pandas.DataFrame

        示例：
        # 查询某只股票的所有行业归属
        df = db.query_em_industry_board_cons_data(code="000001")

        # 查询某个行业的所有成分股
        df = db.query_em_industry_board_cons_data(industry="金融")

        # 查询某只股票在指定日期的行业归属
        df = db.query_em_industry_board_cons_data(code="000001", date="2023-10-01")

        # 查询某个行业在指定日期的成分股
        df = db.query_em_industry_board_cons_data(industry="金融", date="2023-10-01")

        # 查询所有数据
        df = db.query_em_industry_board_cons_data()

        """
        conditions = []
        params = []

        # 构建查询条件
        if code:
            conditions.append("code = ?")
            params.append(code)
        
        if industry:
            conditions.append("industry = ?")
            params.append(industry)
        
        if date:
            conditions.append("date = ?")
            params.append(date)

        # 构建 SQL 查询语句
        query = "SELECT * FROM stock_industry_board_cons_data_em"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY date DESC, code"

        try:
            # 执行查询
            with self._get_connection() as cur:
                cur.execute(query, params)
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=column_names)
        except Exception as e:
            self.logger.error(f"查询东方财富行业板块成分股数据时出错: {str(e)}")
            return pd.DataFrame()

    def get_latest_em_industry_board_cons_data(self):
        try:
            with self._get_connection() as cur:
                cur.execute('''
                    SELECT * FROM stock_industry_board_cons_data_em 
                    WHERE date = (SELECT MAX(date) FROM stock_industry_board_cons_data_em)
                ''')
                
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                
                if rows:
                    return pd.DataFrame(rows, columns=column_names)
                else:
                    return pd.DataFrame()
                    
        except Exception as e:
            self.logger.info(f"查询东方财富行业板块一览表时出错: {str(e)}")
            return pd.DataFrame()


    # ------------------------------------------------------------东方财富股票人气榜表stock_popularity_eastmoney接口-----------------------------------------
    def insert_popularity_rank_stock_data_to_db(self, df_stock_data):
        try:
            # 重命名列以匹配数据库表结构
            df_filtered = df_stock_data.rename(columns={
                '当前排名': 'rank',
                '代码': 'stock_code',
                '股票名称': 'stock_name',
                '最新价': 'last_price',
                '涨跌额': 'change_amount',
                '涨跌幅': 'change_percent',
                '日期': 'date'
            })
            
            # 处理特殊数据
            if 'latest_price' in df_filtered.columns:
                df_filtered['latest_price'] = df_filtered['latest_price'].apply(
                    lambda x: None if x == '-' or pd.isna(x) else float(x)
                )
            
            # 使用 upsert 功能，基于股票代码和日期的复合主键进行更新
            upserted_count = self.upsert_data(
                'stock_popularity_eastmoney',
                df_filtered.to_dict('records'),
                conflict_columns=['date']  # 基于股票代码和日期的冲突检测
            )
            
            self.logger.info(f"东方财富股票人气榜数据upsert完成，处理了 {upserted_count} 条记录")
            return True
                
        except Exception as e:
            self.logger.info(f"东方财富股票人气榜插入数据失败: {e}")
            return False
        
    def query_popularity_rank_stock_data(self, date=None, stock_code=None, industry_name=None):
        """查询东方财富人气榜股数据"""
        conditions = []
        params = []
        
        if date:
            conditions.append("date = ?")
            params.append(date)
        
        if stock_code:
            conditions.append("stock_code = ?")
            params.append(stock_code)
        
        if industry_name:
            conditions.append("industry LIKE ?")
            params.append(f"%{industry_name}%")

        query = "SELECT * FROM stock_popularity_eastmoney"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY date DESC, stock_code"
        
        try:
            with self._get_connection() as cur:
                cur.execute(query, params)
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=column_names)
        except Exception as e:
            self.logger.info(f"查询东方财富股票人气榜表时出错: {str(e)}")
            return pd.DataFrame()
        
    
    def get_latest_popularity_rank_stock_data(self):
        """获取最新日期的所有人气榜股票数据"""
        try:
            with self._get_connection() as cur:
                cur.execute('''
                    SELECT * FROM stock_popularity_eastmoney 
                    WHERE date = (SELECT MAX(date) FROM stock_popularity_eastmoney)
                    ORDER BY date DESC
                ''')
                
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                
                if rows:
                    return pd.DataFrame(rows, columns=column_names)
                else:
                    return pd.DataFrame()
                    
        except Exception as e:
            self.logger.info(f"查询东方财富人气榜股票表时出错: {str(e)}")
            return pd.DataFrame()

    # ------------------------------------------------------------市场情绪接口-----------------------------------------
    def save_market_activity_legu(self, df_market_activity_legu):
        try:
            # 使用 upsert 功能，明确指定冲突列
            upserted_count = self.upsert_data(
                'market_activity_legu',
                df_market_activity_legu.to_dict('records')
            )
            
            self.logger.info(f"数据upsert完成，处理了 {upserted_count} 条记录")
            return True

            
        except Exception as e:
            self.logger.info(f"插入数据失败: {e}")
            return False
        
    def query_market_activity_legu_data(self, date=None, item=None):
        """
        查询市场活跃度数据
        
        :param date: 查询指定日期的数据（可选）
        :param item: 查询指定项目的值（可选）
        :return: 返回查询结果的 pandas.DataFrame
        """
        conditions = []
        params = []

        # 构建查询条件
        if date:
            conditions.append("date = ?")
            params.append(date)
        
        if item:
            conditions.append("item = ?")
            params.append(item)

        # 构建 SQL 查询语句
        query = "SELECT * FROM market_activity_legu"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY date DESC, item"

        try:
            # 执行查询
            with self._get_connection() as cur:
                cur.execute(query, params)
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=column_names)
        except Exception as e:
            self.logger.error(f"查询市场活跃度数据时出错: {str(e)}")
            return pd.DataFrame()
        
    def get_latest_market_activity_legu_data(self):
        """
        获取最新的市场活跃度数据
        """
        try:
            with self._get_connection() as cur:
                cur.execute('''
                    SELECT * FROM market_activity_legu 
                    WHERE date = (SELECT MAX(date) FROM market_activity_legu)
                    ORDER BY item
                ''')
                column_names = [description[0] for description in cur.description]
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=column_names)
        except Exception as e:
            self.logger.error(f"获取最新市场活跃度数据时出错: {str(e)}")
            return pd.DataFrame()

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
    def save_tao_stocks_to_db(self, stocks_data, table_name="stock_basic_info"):
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
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,      -- 添加自增ID作为主键
            "证券代码" TEXT NOT NULL,
            "交易状态" TEXT NOT NULL,
            "证券名称" TEXT NOT NULL,
            "更新日期" DATE NOT NULL DEFAULT CURRENT_DATE,
            "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE("证券代码", "更新日期")              -- 保持复合唯一约束
        )
        """
        
        self.create_table(table_name, create_table_sql)
        
        # 数据预处理
        if not stocks_data.empty:
            # 确保必要列存在
            required_columns = ['证券代码', '交易状态', '证券名称', '更新日期']
            for col in required_columns:
                if col not in stocks_data.columns:
                    raise ValueError(f"缺少必要列: {col}")
            
            try:
                # 使用upsert插入数据
                inserted_count = self.upsert_data(
                    table_name,
                    stocks_data.to_dict('records'),
                    conflict_columns=['证券代码', '更新日期']  # 明确指定冲突检测列
                )
                
                self.logger.info(f"成功保存 {inserted_count} 条 {table_name} 股票数据")
                return inserted_count
            except Exception as e:
                self.logger.error(f"插入数据失败: {e}")
                return False
        
        self.logger.info(f"没有数据需要保存到 {table_name}")
        return 0

    def get_stocks_with_filter(self, table_name, status_filter=None):
        """
        获取股票数据并支持状态过滤
        
        :param table_name: 表名
        :param status_filter: 交易状态过滤条件
        :return: DataFrame格式的股票数据
        """
        df = self.get_table_data(table_name)
        
        if status_filter and not df.empty:
            df = df[df['交易状态'] == status_filter]
        
        return df
    def get_sh_main_stocks(self):
        return self.get_table_data('sh_main')
        
    def get_sz_main_stocks(self):
        return self.get_table_data('sz_main')

    def get_gem_stocks(self):
        return self.get_table_data('gem')
    
    def get_star_stocks(self):
        return self.get_table_data('star')
    
    def get_lastest_stocks(self, table_name='stock_basic_info'):
        """获取最新日期的股票信息数据"""
        try:
            with self._get_connection() as cur:
                cur.execute(f'''
                    SELECT * FROM {table_name} 
                    WHERE 更新日期 = (SELECT MAX(更新日期) FROM {table_name})
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