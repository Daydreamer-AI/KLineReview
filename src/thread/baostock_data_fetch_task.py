from processor.baostock_processor import BaoStockProcessor
from thread.base_task import BaseTask
import random
import time
from PyQt5.QtCore import QObject, pyqtSignal

from manager.period_manager import TimePeriod
from manager.bao_stock_data_manager import BaostockDataManager
from indicators import stock_data_indicators as sdi
    

class BaostockDataFetchTask2(BaseTask):
    sig_progress_changed = pyqtSignal(int, int)
    def __init__(self, code=None, start_date=None, end_date=None, period=None, adjustflag='2', **kwargs):
        super().__init__(**kwargs)
        self._current_board_type = None
        self._current_level = None
        self._current_stock_index = 0
        self._total_stocks = 0

        # 初始化新增的 4 个参数
        self.code = code
        self.start_date = start_date
        self.end_date = end_date
        self.period = period
        # baostock 前复权(2)仅提供最近约三年数据；复盘随机日期已按该窗口限定
        self.adjustflag = adjustflag


    def get_task_status_info(self):
        """获取任务详细状态信息"""
        return {
            "current_board_type": self._current_board_type,
            "current_level": self._current_level,
            "is_paused": self.is_paused(),
            "is_cancelled": self.is_cancelled(),
            "status": self.status.value
        }
    
    def execute(self):
        # 检查暂停状态
        self._check_pause()
        
        # 检查取消状态
        if self.is_cancelled():
            return {"result": False, "status": "cancelled", "message": "Task was cancelled"}

        self.sig_progress_changed.emit(0, 1)
        self.set_progress(0)

        if TimePeriod.is_minute_level(self.period):
            df_data = BaoStockProcessor().process_minute_level_stock_data(
                self.code, TimePeriod.get_number_label(self.period), self.start_date, self.end_date, self.adjustflag)
        else:
            if self.period == TimePeriod.DAY:
                df_data = BaoStockProcessor().process_daily_stock_data(self.code, self.start_date, self.end_date, self.adjustflag)
            elif self.period == TimePeriod.WEEK:
                df_data = BaoStockProcessor().process_weekly_stock_data(self.code, self.start_date, self.end_date, self.adjustflag)

        df_data = self._prepare_stock_data_with_indicators(df_data)

        self.sig_progress_changed.emit(1, 1)
        self.set_progress(100)

        bSuccess = df_data is not None and not df_data.empty

        msg = f"Failed processed all data"
        if bSuccess:
            msg = f"Successfully processed all data"


        # 校验更新结果
        return {
            "result": bSuccess,
            "status": "completed", 
            "message": msg,
            "completed_tasks": 1,
            "total_tasks": 1,
            "data": df_data,
        }

    def _prepare_stock_data_with_indicators(self, df_data):
        """远程拉取的原始 K 线数据：补充股票名称并计算指标列，便于直接注入展示组件"""
        if df_data is None or df_data.empty:
            return df_data

        df_data = df_data.copy()
        name = BaostockDataManager().get_stock_name_by_code(self.code)
        df_data['name'] = str(name) if name else '未知'

        # 统一日期/时间为 ISO 字符串（与本地历史数据格式一致），
        # 避免 data_type_conversion 生成的 date/Timestamp 对象与下游字符串比较时报类型错误
        if 'date' in df_data.columns:
            df_data['date'] = df_data['date'].astype(str)
        if 'time' in df_data.columns:
            df_data['time'] = df_data['time'].astype(str)

        sdi.default_indicators_auto_calculate(df_data)
        return df_data

class BaostockInfoFetchTask(BaseTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def execute(self):
        self.set_progress(0)

        # 检查暂停状态
        self._check_pause()
        
        # 检查取消状态
        if self.is_cancelled():
            return {"status": "cancelled", "message": "BaostockInfoFetchTask was cancelled"}

        bRet = BaoStockProcessor().query_all_stock()

        self.set_progress(100)

        task_status = "Failed"
        task_msg = "Failed query_all_stock"
        if bRet:
            task_status = "completed"
            task_msg = f"Successfully query_all_stock"

        return {
            "result": bRet,
            "status": task_status, 
            "message": task_msg,
            "completed_tasks": 1,
            "total_tasks": 1
        }
