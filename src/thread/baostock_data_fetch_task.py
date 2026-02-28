from processor.baostock_processor import BaoStockProcessor
from thread.base_task import BaseTask
import random
import time
from PyQt5.QtCore import QObject, pyqtSignal

from manager.period_manager import TimePeriod

class BaostockDataFetchTask(BaseTask):
    sig_progress_changed = pyqtSignal(int, int)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_board_type = None
        self._current_level = None
        self._current_stock_index = 0
        self._total_stocks = 0

    def execute(self):
        """执行任务的主要方法"""
        board_types = ['sh_main', 'sz_main']
        levels = ['15', '30', '60']
        
        total_tasks = len(board_types) * len(levels)
        completed_tasks = 0
        self.sig_progress_changed.emit(0, total_tasks)

        # BaoStockProcessor().process_sh_main_stock_data()

        # sleep_time = random.uniform(0.3, 0.5)
        # time.sleep(sleep_time)

        # BaoStockProcessor().process_sz_main_stock_data()
        
        for board_type in board_types:
            # 检查暂停状态
            self._check_pause()
            
            # 检查取消状态
            if self.is_cancelled():
                return {"status": "cancelled", "message": "Task was cancelled"}
            
            sleep_time = random.uniform(0.3, 0.5)
            time.sleep(sleep_time)
            
            for level in levels:
                # 检查暂停状态
                self._check_pause()
                
                # 检查取消状态
                if self.is_cancelled():
                    return {"status": "cancelled", "message": "Task was cancelled"}
                
                # 记录当前处理的类型和级别，便于状态跟踪
                self._current_board_type = board_type
                self._current_level = level
                
                # 执行具体的股票数据获取任务
                BaoStockProcessor().process_minute_level_stock_data_with_board_type(board_type, level, self)
                
                completed_tasks += 1
                progress = int((completed_tasks / total_tasks) * 100)
                self.sig_progress_changed.emit(completed_tasks, total_tasks)
                self.set_progress(progress)
        
        # 校验更新结果
        return {
            "status": "completed", 
            "message": f"Successfully processed all data for {board_types} with levels {levels}",
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks
        }

    def get_task_status_info(self):
        """获取任务详细状态信息"""
        return {
            "current_board_type": self._current_board_type,
            "current_level": self._current_level,
            "is_paused": self.is_paused(),
            "is_cancelled": self.is_cancelled(),
            "status": self.status.value
        }
    

class BaostockDataFetchTask2(BaseTask):
    sig_progress_changed = pyqtSignal(int, int)
    def __init__(self, code=None, start_date=None, end_date=None, period=None, **kwargs):
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
        self.sig_progress_changed.emit(0, 1)

        # 检查暂停状态
        self._check_pause()
        
        # 检查取消状态
        if self.is_cancelled():
            return {"status": "cancelled", "message": "Task was cancelled"}

        if TimePeriod.is_minute_level(self.period):
            BaoStockProcessor().process_and_save_minute_level_stock_data(self.code, TimePeriod.get_number_label(self.period))
        else:
            if TimePeriod == TimePeriod.DAY:
                result = BaoStockProcessor().process_and_save_daily_stock_data(self.code)
            elif TimePeriod == TimePeriod.WEEK:
                result = BaoStockProcessor().process_and_save_weekly_stock_data(self.code)

        self.sig_progress_changed.emit(1, 1)
        self.set_progress(1)

        # 校验更新结果
        return {
            "status": "completed", 
            "message": f"Successfully processed all data",
            "completed_tasks": 1,
            "total_tasks": 1
        }