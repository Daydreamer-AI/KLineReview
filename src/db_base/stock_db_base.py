import os
import sqlite3
import pandas as pd
from pathlib import Path
from contextlib import contextmanager
from common.common_api import *
import threading
import numpy as np
import datetime

import weakref
from collections import OrderedDict

from manager.logging_manager import get_logger

'''
    常规插入：executemany+ 分批提交
    超大数据：DataFrame.to_sql或原生 LOAD DATA/COPY
'''

class StockDbBase:
    """
    股票数据库管理基类
    """
    def __init__(self, db_dir=None):
        """
        初始化数据库管理器
        
        参数:
            db_dir (str, optional): 数据库目录路径，默认为./data/database/stocks/db/baostock
            对应各个板块目录：
                baostock(or akshare)/
                    sh_main/
                    sz_main/
                    gem/
                    star/
                    bse/
                    other/
            
        """
        self.logger = get_logger(__name__)
        if db_dir is None:
            self.db_dir = Path("./data/database/stocks/db/akshare")
        else:
            self.db_dir = Path(db_dir)

        self.src_db_dir = self.db_dir
        
        # 确保目录存在
        self.db_dir.mkdir(parents=True, exist_ok=True)

        self._local = threading.local()     # 多线程隔离
        self._lock = threading.Lock()       # 保护​​共享资源​​

    @contextmanager
    def _get_connection(self, db_path, max_connections=5):
        """线程安全的数据库连接获取（LRU连接池）"""
        if not hasattr(self._local, 'connections'):
            self._local.connections = OrderedDict()
        
        # 如果连接不存在且达到最大连接数，关闭最久未使用的连接
        if (db_path not in self._local.connections and 
            len(self._local.connections) >= max_connections):
            oldest_path, oldest_conn = self._local.connections.popitem(last=False)
            oldest_conn.close()
        
        if db_path not in self._local.connections:
            conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
            conn.execute('PRAGMA journal_mode=WAL')
            self._local.connections[db_path] = conn
        else:
            # 移动到末尾表示最近使用
            conn = self._local.connections.pop(db_path)
            self._local.connections[db_path] = conn
        
        try:
            cursor = self._local.connections[db_path].cursor()
            yield cursor
            self._local.connections[db_path].commit()
        except sqlite3.Error as e:
            self._local.connections[db_path].rollback()
            raise e

    @contextmanager
    def _get_connection_object(self, db_path, max_connections=5):
        """线程安全的数据库连接获取（返回连接对象，带LRU连接池）"""
        # 使用OrderedDict实现LRU缓存
        if not hasattr(self._local, 'connections'):
            self._local.connections = OrderedDict()
        
        # 如果连接不存在且达到最大连接数，关闭最久未使用的连接
        if (db_path not in self._local.connections and 
            len(self._local.connections) >= max_connections):
            oldest_path, oldest_conn = self._local.connections.popitem(last=False)
            oldest_conn.close()
        
        if db_path not in self._local.connections:
            conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
            conn.execute('PRAGMA journal_mode=WAL')
            self._local.connections[db_path] = conn
        else:
            # 移动到末尾表示最近使用
            conn = self._local.connections.pop(db_path)
            self._local.connections[db_path] = conn
        
        try:
            yield self._local.connections[db_path]
            self._local.connections[db_path].commit()
        except sqlite3.Error as e:
            self._local.connections[db_path].rollback()
            raise e

    def close_connection(self):
        """关闭当前线程的所有数据库连接"""
        if hasattr(self._local, 'connections'):
            for conn in self._local.connections.values():
                conn.close()
            self._local.connections.clear()
    def create_table(self, db_path, table_name, create_table_sql):
        # 参数验证
        # if not file_exists(db_path):
        #     raise ValueError("数据库文件不存在")

        if not table_name:
            raise ValueError("表名不能为空")
        
        if not create_table_sql:
            raise ValueError("建表SQL语句不能为空")
        
        # 确保SQL语句是创建表的语句
        if not create_table_sql.strip().upper().startswith("CREATE TABLE"):
            raise ValueError("SQL语句必须是CREATE TABLE语句")
        
        # 使用线程安全的连接方式创建表
        with self._get_connection(db_path) as cur:
            try:
                cur.execute(create_table_sql)
                # self.logger.info(f"表 {table_name} 创建成功或已存在")
                return True
            except sqlite3.Error as e:
                self.logger.info(f"创建表 {table_name} 失败: {str(e)}")
                raise

    def get_table_data(self, db_path, table="stock_data", start_date=None, end_date=None, code=None):
        try:
            # 使用线程安全的连接方式执行查询
            with self._get_connection(db_path) as cur:
                # 基础查询
                query = f"SELECT * FROM {table}"
                
                # 添加条件过滤
                conditions = []
                params = []
                
                # 日期范围过滤
                if start_date:
                    conditions.append("date >= ?")
                    params.append(start_date)
                
                if end_date:
                    conditions.append("date <= ?")
                    params.append(end_date)
                
                # 股票代码过滤
                if code:
                    conditions.append("code = ?")
                    params.append(code)
                
                # 如果有条件，则添加WHERE子句
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                # 添加排序
                query += " ORDER BY date"
                
                cur.execute(query, params)
                # 获取列名
                column_names = [description[0] for description in cur.description]
                # 获取所有数据
                rows = cur.fetchall()
                
                # 转换为 DataFrame
                df = pd.DataFrame(rows, columns=column_names)
                return df
        except Exception as e:
            self.logger.info(f"获取股票数据时出错: {str(e)}")
            return pd.DataFrame()
        
    def insert_dataframe_to_table(self, db_path, table_name, df_data, if_exists="replace"):
        """将 DataFrame 数据插入数据库表
        :param table_name: 表名
        :param df_data: DataFrame 数据, 列名和表列名对应才能使用该接口插入
        :param if_exists: 插入方式，默认为替换
        """
        # 参数验证
        if not file_exists(db_path):
            raise ValueError("数据库路径不存在")

        if not table_name:
            raise ValueError("表名不能为空")
        
        if df_data is None or df_data.empty:
            self.logger.info(f"警告: 要插入的数据为空，未执行插入操作")
            return 0
        
        if not isinstance(df_data, pd.DataFrame):
            raise ValueError("df_data必须是pandas.DataFrame类型")
            
        if if_exists not in ["replace", "append", "fail", "ignore"]:
            raise ValueError("if_exists参数必须是'replace', 'append', 'fail', 'ignore'之一")

        try:
            # 检查表是否存在数据
            with self._get_connection(db_path) as cur:
                cur.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                table_exists = cur.fetchone()[0] > 0
                
                if table_exists:
                    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cur.fetchone()[0]
                    
                    if row_count > 0:
                        if if_exists == "fail":
                            raise ValueError(f"表 {table_name} 中已存在数据，根据if_exists='fail'参数，操作被终止")
                        elif if_exists == "replace":
                            cur.execute(f"DELETE FROM {table_name}")
                            self.logger.info(f"已清空表 {table_name} 中的 {row_count} 行数据")
                        elif if_exists == "ignore":
                            # 对于ignore模式，我们检查主键冲突，只插入不重复的数据
                            self.logger.info(f"表 {table_name} 中已存在数据，将忽略重复数据进行插入")
                else:
                    self.logger.info(f"表 {table_name} 不存在，将创建新表")

            # 获取DataFrame的列名
            columns = list(df_data.columns)
            if not columns:
                raise ValueError("DataFrame没有有效的列")
            
            # 准备插入语句
            placeholders = ', '.join('?' * len(columns))
            columns_str = ', '.join([f'"{col}"' for col in columns])  # 用引号包围列名防止关键字冲突
            
            # 根据if_exists参数选择不同的插入策略
            if if_exists == "ignore":
                insert_sql = f'INSERT OR IGNORE INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'
            else:
                insert_sql = f'INSERT OR REPLACE INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'
            
            # 将DataFrame转换为记录列表
            records = df_data.to_dict('records')
            
            # 处理缺失值，将NaN替换为None
            processed_records = []
            for record in records:
                processed_record = {}
                for key, value in record.items():
                    # 处理NaN值
                    if pd.isna(value):
                        processed_record[key] = None
                    # 处理numpy数据类型
                    elif isinstance(value, (np.integer, np.floating)):
                        processed_record[key] = value.item()  # 转换为Python原生类型
                    elif isinstance(value, np.bool_):
                        processed_record[key] = bool(value)
                    elif isinstance(value, (pd.Timestamp, datetime.datetime)):
                        # 处理时间戳类型，转换为字符串格式
                        processed_record[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, datetime.date):
                        # 处理日期类型
                        processed_record[key] = str(value)
                    else:
                        processed_record[key] = value
                processed_records.append(tuple(processed_record.values()))
            
            # 执行批量插入
            with self._get_connection(db_path) as cur:
                cur.executemany(insert_sql, processed_records)
                row_count = cur.rowcount
                # self.logger.info(f"成功向表 {table_name} {if_exists} {row_count} 行数据")
                return row_count
                
        except sqlite3.Error as e:
            error_msg = f"向表 {table_name} 插入数据时发生数据库错误: {str(e)}"
            self.logger.info(error_msg)
            raise
        except Exception as e:
            error_msg = f"向表 {table_name} 插入数据时发生错误: {str(e)}"
            self.logger.info(error_msg)
            raise


    def upsert_data(self, db_path, table_name, data, conflict_columns=None):
        """
        插入或更新数据（upsert操作）
        
        :param table_name: 表名
        :param data: 要插入或更新的数据（字典或字典列表）
        :param conflict_columns: 冲突检测列（用于ON CONFLICT子句），如果为None则使用主键
        :return: 操作的行数

        示例：db_manager.upsert_data("users", {"id": 1, "name": "User1", "email": "user1@example.com"}, ["id"])
        """
        if not table_name:
            raise ValueError("表名不能为空")
            
        if not data:
            self.logger.info("警告: 数据为空，未执行操作")
            return 0
            
        # 确保data是列表格式
        if isinstance(data, dict):
            data = [data]
            
        if not isinstance(data, list):
            raise ValueError("数据必须是字典或字典列表")
            
        try:
            inserted_count = 0
            
            with self._get_connection(db_path) as cur:
                for record in data:
                    if not record:
                        continue
                        
                    # 构造INSERT语句
                    columns = list(record.keys())
                    placeholders = ','.join(['?' for _ in columns])
                    columns_str = ','.join(columns)
                    
                    sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                    
                    # 如果指定了冲突列，则添加ON CONFLICT子句
                    if conflict_columns:
                        conflict_cols_str = ','.join(conflict_columns)
                        # 构造UPDATE子句（排除冲突列）
                        update_columns = [col for col in columns if col not in conflict_columns]
                        if update_columns:
                            update_clause = ','.join([f"{col} = excluded.{col}" for col in update_columns])
                            sql += f" ON CONFLICT({conflict_cols_str}) DO UPDATE SET {update_clause}"
                        else:
                            sql += f" ON CONFLICT({conflict_cols_str}) DO NOTHING"
                    else:
                        # 如果没有指定冲突列，使用INSERT OR REPLACE
                        sql = f"INSERT OR REPLACE INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                    
                    values = list(record.values())
                    cur.execute(sql, values)
                    inserted_count += cur.rowcount
                    
            # self.logger.info(f"成功对表 {table_name} 执行 {inserted_count} 次upsert操作")
            return inserted_count
            
        except sqlite3.Error as e:
            error_msg = f"对表 {table_name} 执行upsert操作时发生数据库错误: {str(e)}"
            self.logger.info(error_msg)
            raise
        except Exception as e:
            error_msg = f"对表 {table_name} 执行upsert操作时发生错误: {str(e)}"
            self.logger.info(error_msg)
            raise


    # =====================================================================数据库文件相关接口======================================================
    def get_stock_list_by_path(self, path):
        stock_codes = []

        for file in path.glob("*.db"):
            stock_code = file.stem  # 获取文件名（不含扩展名）
            stock_codes.append(stock_code)

        return stock_codes
    def list_all_stocks(self):
        """
        列出所有已存在的股票数据库
        
        返回:
            list: 股票代码列表
        """
        stock_codes = []
    
        # 定义所有板块目录
        board_dirs = ["sh_main", "sz_main", "gem", "star", "other"]
        
        for board_dir in board_dirs:
            dir_path = self.db_dir / board_dir
            # 确保主板块目录存在，其他板块目录可选
            if board_dir != "other":
                dir_path.mkdir(parents=True, exist_ok=True)
            
            # 只处理存在的目录
            if dir_path.exists():
                code_list = self.get_stock_list_by_path(dir_path)
                stock_codes.extend(code_list)
        
        # 去重并返回
        return list(dict.fromkeys(stock_codes))  # 保持顺序的去重

    def get_src_db_dir(self):
        """
        获取数据库源目录
        
        返回:
            str: 数据库源目录
        """
        return self.src_db_dir

    def reset_db_dir(self):
        """
        重置数据库目录
        """
        self.db_dir = self.src_db_dir
    def get_db_dir(self):
        return self.db_dir

    def set_db_dir(self, db_dir):
        if db_dir is None:
            self.db_dir = Path("./data/database/stocks/db/akshare")
        else:
            self.db_dir = Path(db_dir)

        # 确保目录存在
        self.db_dir.mkdir(parents=True, exist_ok=True)

    def get_db_path(self, stock_code):
        """
        获取指定股票代码的数据库路径
        
        参数:
            stock_code (str): 股票代码
            
        返回:
            Path: 数据库文件路径
        """
        s_board_name = identify_stock_board(stock_code)
        # self.logger.info(f"股票 {stock_code} 的板块名称为 {s_board_name}")
        return self.db_dir / s_board_name / f"{stock_code}.db"

    def check_stock_db_exists(self, stock_code):
        """
        检查指定股票的数据库是否存在
        
        参数:
            stock_code (str): 股票代码
            
        返回:
            bool: 存在返回True，否则返回False
        """
        db_path = self.get_db_path(stock_code)
        return db_path.exists()
    
    def delete_stock_db(self, stock_code):  
        """
        删除指定股票的数据库
        
        参数:
            stock_code (str): 股票代码
            
        返回:
            bool: 删除成功返回True，否则返回False
        """
        if not self.check_stock_db_exists(stock_code):
            self.logger.info(f"股票 {stock_code} 的数据库不存在")
            return False
        
        try:
            db_path = self.get_db_path(stock_code)
            os.remove(db_path)
            self.logger.info(f"成功删除股票 {stock_code} 的数据库")
            return True
        except Exception as e:
            self.logger.info(f"删除股票 {stock_code} 数据库时出错: {str(e)}")
            return False  

    # TODO: 添加股票数据库文件，修改股票数据库文件
    def add_stock_db(self, stock_code):
        pass

    def update_stock_db_info(self, stock_code, new_stock_code):
        pass

    # =======================================================================表结构相关接口=======================================================
    # 一个日期只能有一条数据，因此主键为日期
    def get_table_info(self, stock_code, table_name="stock_data"):
        """
        获取数据库表结构信息
        
        参数:
            stock_code (str): 股票代码
            table_name (str, optional): 表名，默认为stock_data
            
        返回:
            list: 表字段信息列表
        """
        if not self.check_stock_db_exists(stock_code):
            self.logger.info(f"股票 {stock_code} 的数据库不存在")
            return None
        
        if not self.check_table_exists(stock_code, table_name):
            self.logger.info(f"股票 {stock_code} 的表 {table_name} 不存在")
            return None
        
        if not self.is_valid_table_name(table_name):
            # raise ValueError("非法表名！")
            return None
        
        try:
            conn = sqlite3.connect(str(self.get_db_path(stock_code)))
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = cursor.fetchall()
            conn.close()
            return columns_info
        except Exception as e:
            self.logger.info(f"获取股票 {stock_code} 数据库表结构时出错: {str(e)}")
            return None
        
    def is_valid_table_name(self, table_name):
        """
        检查表名是否合法
        
        参数:
            table_name (str): 表名
            
        返回:
            bool: 合法返回True，否则返回False

        使用方式
            if not is_valid_table_name(table_name):
                raise ValueError("非法表名！")
        """
        allowed_tables = {"stock_data", "user_info", "transaction_log", "stock_data_1d", "stock_data_1w", "stock_data_1m", "stock_data_3m", "stock_data_5m", "stock_data_10m", "stock_data_15m", "stock_data_30m", "stock_data_45m", "stock_data_60m", "stock_data_90m", "stock_data_120m"}
        
        # 直接匹配基础表名
        if table_name in allowed_tables:
            return True
        
        # 检查是否为stock_data的周期数据表
        if table_name.startswith("stock_data_"):
            # 允许的周期格式：数字+时间单位(d/w/m/y) 或 数字+m
            import re
            if re.match(r'^stock_data_(\d+[dwmy]|\d+m)$', table_name):
                return True
        
        return False

    def check_table_exists(self, stock_code, table_name):
        """
        检查指定股票数据库中的表是否存在
        
        参数:
            stock_code (str): 股票代码
            table_name (str): 表名
            
        返回:
            bool: 表存在返回True，否则返回False
        """
        if not self.check_stock_db_exists(stock_code):
            return False
        
        db_path = self.get_db_path(stock_code)
        self
        try:
            with self._get_connection(db_path) as cur:
                cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                return cur.fetchone()[0] > 0
        except Exception as e:
            self.logger.info(f"检查表 {table_name} 存在性时出错: {str(e)}")
            return False

    def check_column_exists(self, stock_code, column_name, table_name="stock_data"):
        """
        检查指定表中是否存在某个字段
        
        参数:
            stock_code (str): 股票代码
            column_name (str): 字段名
            table_name (str, optional): 表名，默认为stock_data
            
        返回:
            bool: 字段存在返回True，否则返回False
        """

        if not self.is_valid_table_name(table_name):
            # raise ValueError("非法表名！")
            return False

        columns_info = self.get_table_info(stock_code, table_name)
        if columns_info is None:
            return False
        
        for col in columns_info:
            if col[1] == column_name:
                return True
        
        return False

    def add_column(self, stock_code, column_name, column_type, default_value=None, table_name="stock_data"):
        """
        为指定数据库表添加新字段
        
        参数:
            stock_code (str): 股票代码
            column_name (str): 新字段名
            column_type (str): 字段类型，如TEXT, INTEGER, REAL等
            default_value (any, optional): 默认值，如果为None则不设置默认值
            table_name (str, optional): 表名，默认为stock_data
            
        返回:
            bool: 添加成功返回True，否则返回False
        """
        if not self.check_stock_db_exists(stock_code):
            self.logger.info(f"股票 {stock_code} 的数据库不存在")
            return False
        
        if not self.check_table_exists(stock_code, table_name):
            self.logger.info(f"股票 {stock_code} 的表 {table_name} 不存在")
            return None
        
        if not self.is_valid_table_name(table_name):
            # raise ValueError("非法表名！")
            return False
        
        # 检查字段是否已存在
        if self.check_column_exists(stock_code, column_name, table_name):
            self.logger.info(f"字段 {column_name} 已存在于表 {table_name} 中")
            return True
        
        try:
            conn = sqlite3.connect(str(self.get_db_path(stock_code)))
            cursor = conn.cursor()
            
            # 构建SQL语句
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            if default_value is not None:
                if isinstance(default_value, str):
                    sql += f" DEFAULT '{default_value}'"
                else:
                    sql += f" DEFAULT {default_value}"
            
            cursor.execute(sql)
            conn.commit()
            conn.close()
            
            self.logger.info(f"成功为表 {table_name} 添加字段 {column_name} ({column_type})")
            return True
        except Exception as e:
            self.logger.info(f"为表 {table_name} 添加字段 {column_name} 时出错: {str(e)}")
            return False

    def add_columns(self, stock_code, columns_info, table_name="stock_data"):
        """
        为指定数据库表批量添加多个新字段
        
        参数:
            stock_code (str): 股票代码
            columns_info (list): 字段信息列表，每个元素为包含字段名、类型和默认值的元组或列表
                                 格式为 [(column_name, column_type, default_value), ...]
                                 default_value可以为None
            table_name (str, optional): 表名，默认为stock_data
            
        返回:
            dict: 字段名和添加结果的字典
        """
        if not self.check_stock_db_exists(stock_code):
            self.logger.info(f"股票 {stock_code} 的数据库不存在")
            return {}
        
        if not self.check_table_exists(stock_code, table_name):
            self.logger.info(f"股票 {stock_code} 的表 {table_name} 不存在")
            return {}
        
        if not self.is_valid_table_name(table_name):
            # raise ValueError("非法表名！")
            return False
        
        results = {}
        for column_info in columns_info:
            column_name = column_info[0]
            column_type = column_info[1]
            default_value = column_info[2] if len(column_info) > 2 else None
            
            result = self.add_column(stock_code, column_name, column_type, default_value, table_name)
            results[column_name] = result
        
        return results

    def calculate_and_add_column(self, stock_code, column_name, calculation_func, column_type="REAL", table_name="stock_data"):
        """
        计算新的指标并添加为数据库表的新字段
        
        参数:
            stock_code (str): 股票代码
            column_name (str): 新字段名
            calculation_func (function): 计算函数，接收DataFrame作为参数，返回Series或列表
            column_type (str, optional): 字段类型，默认为REAL
            table_name (str, optional): 表名，默认为stock_data
            
        返回:
            bool: 添加成功返回True，否则返回False
        """
        # 获取股票数据
        df = self.get_stock_data(stock_code)
        if df is None or df.empty:
            self.logger.info(f"无法获取股票 {stock_code} 的数据")
            return False
        
        if not self.is_valid_table_name(table_name):
            # raise ValueError("非法表名！")
            return False
        
        try:
            # 计算新指标
            new_column_data = calculation_func(df)
            
            # 添加到DataFrame
            df[column_name] = new_column_data
            
            # 检查字段是否已存在，如果存在则先添加
            if not self.check_column_exists(stock_code, column_name, table_name):
                self.add_column(stock_code, column_name, column_type, None, table_name)
            
            # 更新数据库
            conn = sqlite3.connect(str(self.get_db_path(stock_code)))
            
            # 更新每一行
            for index, row in df.iterrows():
                date = row['日期']
                value = row[column_name]
                
                # 更新该日期的记录
                sql = f"UPDATE {table_name} SET {column_name} = ? WHERE 日期 = ?"
                conn.execute(sql, (value, date))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"成功计算并添加字段 {column_name} 到表 {table_name}")
            return True
        except Exception as e:
            self.logger.info(f"计算并添加字段 {column_name} 时出错: {str(e)}")
            return False

    # TODO: 修改指定table的指定列，删除指定table指定列 
    def update_column(self, stock_code, column_name, new_column_name, table_name="stock_data"):
        # 不支持修改列数据类型或约束
        pass

    def delete_column(self, stock_code, column_name, table_name="stock_data"):
        # 不支持直接删除列（需通过创建新表迁移数据）
        pass

    def rename_table(self, stock_code, old_table_name, new_table_name):
        try:
            conn = sqlite3.connect(self.get_db_path())
            cursor = conn.cursor()
            
            # 重命名表
            cursor.execute(f"ALTER TABLE {old_table_name} RENAME TO {new_table_name};")
            conn.commit()
            self.logger.info(f"表名已从 '{old_table_name}' 改为 '{new_table_name}'")
        
        except sqlite3.OperationalError as e:
            self.logger.info(f"操作失败：{e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()


    # =================================================================AKShare表数据相关============================================
    def create_akshare_table(self, db_path):
        """
        创建股票数据表
        根据图片中的表结构创建包含所有必要字段的表
        """
        # SQL语句 - 根据图片中的表结构
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS stock_data (
            date DATE NOT NULL,
            code TEXT NOT NULL,
            open REAL,
            close REAL,
            high REAL,
            low REAL,
            volume INTEGER,
            amount REAL,
            amplitude REAL,
            change_percent REAL,
            turnover_rate REAL,
            PRIMARY KEY (date, code)
        )
        """
        self.create_table(create_table_sql)
    

    def get_akshare_stock_data(self, stock_code, start_date=None, end_date=None, table_name="stock_data"):
        """
        获取指定股票的数据
        
        参数:
            stock_code (str): 股票代码
            start_date (str, optional): 开始日期，格式为YYYY-MM-DD
            end_date (str, optional): 结束日期，格式为YYYY-MM-DD
            
        返回:
            DataFrame: 股票数据，如果数据库不存在则返回None
        """
        if not self.check_stock_db_exists(stock_code):
            self.logger.info(f"股票 {stock_code} 的数据库不存在")
            return None
        
        # if not self.check_table_exists(stock_code, table_name):
        #     self.logger.info(f"股票 {stock_code} 的表 {table_name} 不存在")
        #     return None
        
        if not self.is_valid_table_name(table_name):
            # raise ValueError("非法表名！")
            return None

        try:
            conn = sqlite3.connect(str(self.get_db_path(stock_code)))
            query = f"SELECT * FROM {table_name}"
            
            # 添加日期过滤条件
            if start_date or end_date:
                conditions = []
                if start_date:
                    conditions.append(f"date >= '{start_date}'")
                if end_date:
                    conditions.append(f"date <= '{end_date}'")
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            # 按日期排序
            query += " ORDER BY date DESC"
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            self.logger.info(f"获取股票 {stock_code} 数据时出错: {str(e)}")
            return None

    def get_latest_data(self, stock_code, count=1):
        """
        获取指定股票最近几天的数据
        
        参数:
            stock_code (str): 股票代码
            days (int, optional): 获取最近几天的数据，默认为1天
            
        返回:
            DataFrame: 最近几天的股票数据
        """
        pass


    def update_stock_data(self, stock_code, stock_data):
        """
        更新指定股票的数据库
        
        参数:
            stock_code (str): 股票代码
            stock_data (dict): 股票数据
            
        返回:
            bool: 更新成功返回True，否则返回False
        """
        pass

    def update_all_stocks(self):
        """
        更新所有股票的数据库
        
        返回:
            dict: 股票代码和更新结果的字典
        """
        pass

    # TODO: 指定table中添加数据，删除指定table数据
    def add_stock_data(self, stock_code, stock_data, table="stock_data"):
        pass

    def delete_stock_data(self, stock_code, date):
        pass

    def save_akshare_stock_data_to_db(self, stock_code, stock_data, writeWay="replace", table_name="stock_data"):
        pass

    def insert_dict_to_table(self, data_dict, table_name="stock_data"):
        pass

    # ===================================================================AKShare表数据相关====================================================================

    # ------------------------------------------------------------东方财富股票行业板块成分股接口-----------------------------
    def insert_em_industry_board_cons_to_db(self, code, df_data, table_name="stock_industry_board_cons_data_em", writeWay="replace"):
        db_path = self.get_db_path(code)
        self.logger.info("insert_em_industry_board_cons_to_db--db_path:", db_path)

        create_table_sql = f"""CREATE TABLE IF NOT EXISTS {table_name} (
                    code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    industry TEXT NOT NULL,
                    date DATE NOT NULL,
                    PRIMARY KEY (code, date)
                )"""

        self.create_table(db_path, table_name, create_table_sql)

        self.insert_dataframe_to_table(db_path, table_name, df_data, writeWay)

    def query_em_industry_board_cons_data(self, code, table_name="stock_industry_board_cons_data_em", date=None, industry=None):
        """
        查询东方财富行业板块成分股数据
        
        参数:
            code (str): 股票代码
            table_name (str, optional): 表名，默认为 stock_industry_board_cons_data_em
            date (str, optional): 查询指定日期的数据，格式为 YYYY-MM-DD
            industry (str, optional): 查询指定行业的数据
        
        返回:
            DataFrame: 查询结果，如果数据库或表不存在则返回空 DataFrame
        """
        # 检查数据库是否存在
        if not self.check_stock_db_exists(code):
            self.logger.info(f"股票 {code} 的数据库不存在")
            return pd.DataFrame()
        
        # 检查表是否存在
        if not self.check_table_exists(code, table_name):
            self.logger.info(f"股票 {code} 的表 {table_name} 不存在")
            return pd.DataFrame()
        
        try:
            db_path = self.get_db_path(code)
            
            # 使用线程安全的连接方式执行查询
            with self._get_connection(db_path) as cur:
                # 基础查询
                query = f"SELECT * FROM {table_name}"
                
                # 添加条件过滤
                conditions = []
                params = []
                
                # 日期过滤
                if date:
                    conditions.append("date = ?")
                    params.append(date)
                
                # 行业过滤
                if industry:
                    conditions.append("industry = ?")
                    params.append(industry)
                
                # 如果有条件，则添加 WHERE 子句
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                # 添加排序
                query += " ORDER BY date DESC"
                
                cur.execute(query, params)
                # 获取列名
                column_names = [description[0] for description in cur.description]
                # 获取所有数据
                rows = cur.fetchall()
                
                # 转换为 DataFrame
                df = pd.DataFrame(rows, columns=column_names)
                return df
        except Exception as e:
            self.logger.info(f"查询东方财富行业板块成分股数据时出错: {str(e)}")
            return pd.DataFrame()
        

    def get_lastest_em_industry_board_cons_data(self, stock_code, table_name="stock_industry_board_cons_data_em"):
        # 检查数据库是否存在
        if not self.check_stock_db_exists(stock_code):
            self.logger.info(f"股票 {stock_code} 的数据库不存在")
            return pd.DataFrame()
        
        # 检查表是否存在
        if not self.check_table_exists(stock_code, table_name):
            self.logger.info(f"股票 {stock_code} 的表 {table_name} 不存在")
            return pd.DataFrame()
        
        db_path = self.get_db_path(stock_code)
        
        try:
            # 使用线程安全的连接方式执行查询
            with self._get_connection(db_path) as cur:
                query = f"SELECT * FROM {table_name} WHERE date = (SELECT MAX(date) FROM {table_name}) ORDER BY date DESC"
                cur.execute(query)
                # 获取列名
                column_names = [description[0] for description in cur.description]
                # 获取所有数据
                rows = cur.fetchall()
                
                # 转换为 DataFrame
                if rows:
                    return pd.DataFrame(rows, columns=column_names)
                else:
                    return pd.DataFrame()
        except Exception as e:
            self.logger.info(f"获取股票数据时出错: {str(e)}, code: {stock_code}")
            return pd.DataFrame()


    # ------------------------------------------------------------东方财富股票筹码分布表stock_chip_distribution_data_eastmoney接口-----------------------------
    # 待优化
    def insert_eastmoney_stock_chip_distribution_data_to_db(self, code, df_data, table_name="stock_chip_distribution_data_eastmoney"):
        db_path = self.get_db_path(code)
        self.logger.info("insert_eastmoney_stock_chip_distribution_data_to_db--db_path:", db_path)

        # 检查表是否已存在
        with self._get_connection(db_path) as cur:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            table_exists = cur.fetchone()
            
        if not table_exists:
            create_table_sql = '''
                CREATE TABLE IF NOT EXISTS stock_chip_distribution_data_eastmoney (
                    日期 TEXT PRIMARY KEY,
                    获利比例 REAL,
                    平均成本 REAL,
                    "90成本-低" REAL,
                    "90成本-高" REAL,
                    "90集中度" REAL,
                    "70成本-低" REAL,
                    "70成本-高" REAL,
                    "70集中度" REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(日期)
                )
                '''
            self.create_table(db_path, table_name, create_table_sql)

        # 如果数据为空，直接返回
        if df_data is None or df_data.empty:
            self.logger.info("警告: 要插入的数据为空，未执行插入操作")
            return True
        
        try:
            # 先查询数据库中已存在的数据
            with self._get_connection_object(db_path) as conn:
                existing_data = pd.read_sql_query(
                    "SELECT 日期 FROM stock_chip_distribution_data_eastmoney", conn)
            
            # 从新数据中移除已存在的数据
            if not existing_data.empty:
                # 过滤掉已存在的数据
                df_filtered = df_data[~df_data['日期'].isin(existing_data['日期'])]
            else:
                df_filtered = df_data

            self.logger.info(f"插入的数据行数：{len(df_filtered)}")
            
            # 只有当还有数据需要插入时才执行插入操作
            if not df_filtered.empty:
                # 
                # 使用原有的 insert_dataframe_to_table 方法，但使用 append 模式
                self.insert_dataframe_to_table(db_path, table_name, df_filtered, if_exists="append")
            else:
                self.logger.info("没有新数据需要插入，更新最后一天数据")
                upserted_count = self.upsert_data(
                    'stock_chip_distribution_data_eastmoney',
                    df_data.tail(1).to_dict('records'),
                    conflict_columns=['日期']
                )
            
                self.logger.info(f"数据upsert完成，处理了 {upserted_count} 条记录")
                
            return True
            
        except Exception as e:
            self.logger.info(f"插入筹码分布数据失败: {e}")
            return False

    # 待优化
    def query_eastmoney_stock_chip_distribution_data(self, code):
        if not self.check_stock_db_exists(code):
            return pd.DataFrame()
        
        # if not self.check_table_exists(code, table_name):
        #     self.logger.info(f"股票 {stock_code} 的表 {table_name} 不存在")
        #     return None
        
        db_path = self.get_db_path(code)
        return self.get_table_data(db_path, 'stock_chip_distribution_data_eastmoney')

    # 待优化
    def get_latest_eastmoney_stock_chip_distribution_data(self, code):
        if not self.check_stock_db_exists(code):
            return pd.DataFrame()
        
        # if not self.check_table_exists(code, table_name):
        #     self.logger.info(f"股票 {stock_code} 的表 {table_name} 不存在")
        #     return None
        
        db_path = self.get_db_path(code)

        try:
            with self._get_connection_object(db_path) as conn:
                # 直接使用连接对象查询最大日期
                latest_date = pd.read_sql_query(
                    "SELECT MAX(日期) as max_date FROM stock_chip_distribution_data_eastmoney", 
                    conn
                ).iloc[0]['max_date']

                # self.logger.info("latest_date: ", latest_date)
                if not latest_date:
                    self.logger.info(f"没有找到最后日期{latest_date}的股票数据", latest_date)
                    return pd.DataFrame()
                
                # 获取该日期的所有数据
                df = pd.read_sql_query('''
                SELECT * FROM stock_chip_distribution_data_eastmoney 
                WHERE 日期 = ?
                ''', conn, params=[latest_date])
                
                return df
        
        except Exception as e:
            self.logger.info(f"查询东方财富股票数据表时出错: {str(e)}")
            return pd.DataFrame()


    # ===================================================================Baostock表数据相关====================================================================
    def get_baostock_create_table_sql(self, table_name='stock_data'):
        sql = ""
        if table_name == 'stock_data' or table_name == 'stock_data_1d' or table_name == 'stock_data_1w' or table_name == 'stock_data_1m':
            sql = f"""CREATE TABLE IF NOT EXISTS {table_name} (
                    date DATE NOT NULL,
                    code TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    amount REAL,
                    change_percent REAL,
                    turnover_rate REAL,
                    adjustflag INTEGER,
                    PRIMARY KEY (date, code)
                )"""
        elif table_name == 'stock_data_3m' or table_name == 'stock_data_5m' or table_name == 'stock_data_10m' or table_name == 'stock_data_15m' or table_name == 'stock_data_30m' or table_name == 'stock_data_45m' or table_name == 'stock_data_60m' or table_name == 'stock_data_90m' or table_name == 'stock_data_120m':
            sql = f"""CREATE TABLE IF NOT EXISTS {table_name} (
                    date DATE NOT NULL,
                    time DATETIME NOT NULL,
                    code TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    amount REAL,
                    adjustflag INTEGER,
                    PRIMARY KEY (date, time, code)
                )"""
        else:
            raise ValueError(f"Invalid table name: {table_name}")
        
        return sql
    def create_baostock_table(self, db_path, table_name='stock_data'):
        allowed_table = ['stock_data', 'stock_data_1d', 'stock_data_1w', 'stock_data_1m', 'stock_data_5m', 'stock_data_15m', 'stock_data_30m', 'stock_data_60m', 'stock_data_120m']

        if table_name not in allowed_table:
            raise ValueError(f"Invalid table name: {table_name}")

        create_table_sql = self.get_baostock_create_table_sql(table_name)
        self.create_table(db_path, table_name, create_table_sql)

        self.create_baostock_table_index(db_path, table_name)


    def create_baostock_table_index_by_code(self, code, table_name):
        db_path = self.get_db_path(code)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.create_baostock_table_index(db_path, table_name)
    def create_baostock_table_index(self, db_path, table_name):
        allowed_table = ['stock_data', 'stock_data_1d', 'stock_data_1w', 'stock_data_1m', 
                        'stock_data_5m', 'stock_data_15m', 'stock_data_30m', 'stock_data_60m', 'stock_data_120m']

        if table_name not in allowed_table:
            raise ValueError(f"Invalid table name: {table_name}")

        # 主索引：复合索引满足最常见的查询需求
        primary_index_sql = ""
        
        # 辅助索引：满足特定查询需求
        additional_indexes = []

        if table_name in ['stock_data', 'stock_data_1d', 'stock_data_1w', 'stock_data_1m']:
            # 日线数据索引
            primary_index_sql = f"CREATE INDEX IF NOT EXISTS idx_{table_name}_date_code ON {table_name} (date, code)"
            # 为单独按股票代码查询添加索引
            additional_indexes.append(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_code ON {table_name} (code)")
            
        elif table_name in ['stock_data_5m', 'stock_data_15m', 'stock_data_30m', 'stock_data_60m', 'stock_data_120m']:
            # 分钟级别数据索引
            primary_index_sql = f"CREATE INDEX IF NOT EXISTS idx_{table_name}_date_time_code ON {table_name} (date, time, code)"
            # 为单独按股票代码查询添加索引
            additional_indexes.append(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_code ON {table_name} (code)")

        with self._get_connection(db_path) as cur:
            try:
                # 创建主索引
                cur.execute(primary_index_sql)
                
                # 创建辅助索引
                for index_sql in additional_indexes:
                    cur.execute(index_sql)
                
                # self.logger.info(f"成功为表 {table_name} 创建索引")
                return True
            except sqlite3.Error as e:
                self.logger.error(f"创建表 {table_name} 索引失败: {str(e)}")
                raise

    def get_bao_stock_data(self, stock_code, table_name="stock_data", start_date=None, end_date=None):
        db_path = self.get_db_path(stock_code)
        # self.logger.info("db_path:", db_path)
        # if not self.check_stock_db_exists(stock_code):
        #     # self.logger.info(f"股票 {stock_code} 的数据库不存在")
        #     return None
        
        # if not self.check_table_exists(stock_code, table_name):
        #     # self.logger.info(f"股票 {stock_code} 的表 {table_name} 不存在, 数据库路径：{db_path}")
        #     return None
        
        if not self.is_valid_table_name(table_name):
            raise ValueError(f"非法表名{table_name}！")
        
        return self.get_table_data(db_path, table_name, start_date=start_date, end_date=end_date)
    
    def get_lastest_stock_data(self, stock_code, table_name="stock_data"):
        if not self.is_valid_table_name(table_name):
            raise ValueError(f"非法表名{table_name}！")
        
        db_path = self.get_db_path(stock_code)
        
        try:
            # 使用线程安全的连接方式执行查询
            with self._get_connection(db_path) as cur:
                query = f"SELECT * FROM {table_name} WHERE date = (SELECT MAX(date) FROM {table_name}) ORDER BY date DESC"
                cur.execute(query)
                # 获取列名
                column_names = [description[0] for description in cur.description]
                # 获取所有数据
                rows = cur.fetchall()
                
                # 转换为 DataFrame
                if rows:
                    return pd.DataFrame(rows, columns=column_names)
                else:
                    return pd.DataFrame()
        except Exception as e:
            self.logger.info(f"获取股票数据时出错: {str(e)}, code: {stock_code}")
            return pd.DataFrame()

    def save_bao_stock_data_to_db(self, stock_code, stock_data, writeWay="replace", table_name="stock_data"):
        db_path = self.get_db_path(stock_code)

        # 只在数据库不存在时创建数据库和表
        # if not self.check_stock_db_exists(stock_code):
        #     self.logger.info(f"股票 {stock_code} 的数据库不存在，自动创建：{db_path}")
        #     # 创建数据库目录
        #     db_path.parent.mkdir(parents=True, exist_ok=True)
        #     # 创建表
        #     self.create_baostock_table(db_path, table_name)
        # # 如果数据库存在但表不存在，则创建表
        # elif not self.check_table_exists(stock_code, table_name):
        #     self.logger.info(f"股票 {stock_code} 的表 {table_name} 不存在, 自动创建")
        #     self.create_baostock_table(db_path, table_name)

        # 确保数据库目录存在
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 直接创建表（IF NOT EXISTS 会处理存在性检查）
        self.create_baostock_table(db_path, table_name)
            

        self.insert_dataframe_to_table(db_path, table_name, stock_data, writeWay)
    

    def delete_data_by_date(self, code, cutoff_date, table_name='stock_data'):
        """
        根据日期删除表中的数据
        
        :param cutoff_date: 删除 cutoff_date 之前的数据
        :return: 删除的行数
        """
        try:
            db_path = self.get_db_path(code)
            with self._get_connection(db_path) as cur:
                sql = f"DELETE FROM {table_name} WHERE date >= '{cutoff_date}'"
                cur.execute(sql)

                row_count = cur.rowcount
                self.logger.info(f"成功从表 {table_name} 删除 {row_count} 行数据")
                return row_count
                
        except sqlite3.Error as e:
            error_msg = f"从表 {table_name} 删除数据时发生数据库错误: {str(e)}"
            self.logger.info(error_msg)
            raise
        except Exception as e:
            error_msg = f"从表 {table_name} 删除数据时发生错误: {str(e)}"
            self.logger.info(error_msg)
            raise


    # 测试代码
if __name__ == "__main__":
    print("stock_db_base.py run")