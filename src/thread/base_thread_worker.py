from PyQt5.QtCore import QThread, pyqtSignal
import traceback

class BaseThreadWorker(QThread):
    """
    高级工作线程类，支持任务取消和更详细的控制
    """
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self._is_cancelled = False
        
    def run(self):
        try:
            self.progress.emit(f"开始执行任务: {getattr(self.task_func, '__name__', 'Unknown')}")
            
            # 检查是否已被取消
            if self._is_cancelled:
                self.progress.emit("任务已被取消")
                self.finished.emit(None)
                return
                
            # 执行任务函数
            self.result = self.task_func(*self.args, **self.kwargs)
            
            if self._is_cancelled:
                self.progress.emit("任务执行完成但已被取消")
                self.finished.emit(None)
            else:
                self.progress.emit("任务完成")
                self.finished.emit(self.result)
                
        except Exception as e:
            if not self._is_cancelled:
                error_msg = f"执行任务时出错: {str(e)}\n{traceback.format_exc()}"
                self.progress.emit(error_msg)
                self.error.emit(error_msg)
    
    def cancel(self):
        """取消任务执行"""
        self._is_cancelled = True