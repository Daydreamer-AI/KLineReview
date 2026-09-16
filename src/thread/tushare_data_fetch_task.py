from processor.baostock_processor import TushareProcessor
from thread.base_task import BaseTask
import random
import time
from PyQt5.QtCore import QObject, pyqtSignal

from manager.period_manager import TimePeriod
from manager.bao_stock_data_manager import BaostockDataManager
from indicators import stock_data_indicators as sdi

class TushareUnadjustedDataFetchTask(BaseTask):
    def __init__(self, code=None, start_date=None, end_date=None, period=None, **kwargs):
        super().__init__(**kwargs)

        self.code = code
        self.start_date = start_date
        self.end_date = end_date
        self.period = period

    def execute(self):
        self.set_progress(0)

        # 检查暂停状态
        self._check_pause()
        
        # 检查取消状态
        if self.is_cancelled():
            return {"status": "cancelled", "message": "TushareUnadjustedDataFetchTask was cancelled"}

        df_data = TushareProcessor().query_stock_unadjusted_data(self.code, self.start_date, self.end_date, self.period)
        bRet = df_data is not None and len(df_data) > 0

        self.set_progress(100)

        task_status = "Failed"
        task_msg = "Failed query_stock_unadjusted_data"
        if bRet:
            task_status = "completed"
            task_msg = f"Successfully query_stock_unadjusted_data"

        return {
            "result": bRet,
            "status": task_status, 
            "message": task_msg,
            "completed_tasks": 1,
            "total_tasks": 1, 
            "data": df_data
        }

class TushareAdjustedDataFetchTask(BaseTask):
    def __init__(self, code=None, start_date=None, end_date=None, freq=None, adjustflag=None, **kwargs):
        super().__init__(**kwargs)

        self.code = code
        self.start_date = start_date
        self.end_date = end_date
        self.freq = freq
        self.adjustflag = adjustflag

    def execute(self):
        self.set_progress(0)
        
        # 检查暂停状态
        self._check_pause()
        
        # 检查取消状态
        if self.is_cancelled():
            return {"status": "cancelled", "message": "TushareAdjustedDataFetchTask was cancelled"}

        df_data = TushareProcessor().query_stock_adjusted_data(self.code, self.start_date, self.end_date, self.adjustflag, self.freq)
        bRet = df_data is not None and len(df_data) > 0

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
            "total_tasks": 1, 
            "data": df_data
        }
