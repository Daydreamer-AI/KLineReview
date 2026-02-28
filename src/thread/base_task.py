from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime
from typing import Any, Optional
import traceback
import threading

from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"  # 新增暂停状态
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class BaseTask(QObject):
    """Qt集成的任务基类"""
    
    # Qt信号
    task_started = pyqtSignal(str)  # task_id
    task_progress = pyqtSignal(str, int)  # task_id, progress
    task_completed = pyqtSignal(str, object)  # task_id, result
    task_error = pyqtSignal(str, str)  # task_id, error_message
    task_cancelled = pyqtSignal(str)  # task_id
    task_paused = pyqtSignal(str)  # task_id - 新增暂停信号
    task_resumed = pyqtSignal(str)  # task_id - 新增恢复信号
    
    def __init__(self, task_id: Optional[str] = None, priority: int = 0, timeout: Optional[int] = None):
        super().__init__()
        self.task_id = task_id
        self.priority = priority
        self.timeout = timeout
        self.status = TaskStatus.PENDING
        self.created_time = datetime.now()
        self.start_time = None
        self.end_time = None
        self.result = None
        self.error = None
        self._cancelled = False
        self._paused = False  # 新增暂停标志
        self._pause_condition = threading.Condition(threading.Lock())  # 用于暂停/恢复的条件变量
        self._lock = threading.Lock()

    def get_task_id(self) -> str:
        return self.task_id
    
    def get_task_status(self) -> TaskStatus:
        """获取任务状态"""
        return self.status
        
    @abstractmethod
    def execute(self) -> Any:
        """执行任务的主要方法，子类必须实现"""
        pass
    
    def run(self):
        """任务执行方法"""
        with self._lock:
            if self._cancelled:
                self.status = TaskStatus.CANCELLED
                self.task_cancelled.emit(self.task_id)
                return
            
            self.status = TaskStatus.RUNNING
            self.start_time = datetime.now()
        
        # 发送开始信号
        self.task_started.emit(self.task_id)
        
        try:
            # 执行任务
            self.result = self.execute()
            
            # 发送完成信号
            with self._lock:
                # 检查是否在执行过程中被取消
                if not self._cancelled:
                    self.status = TaskStatus.COMPLETED
                    self.end_time = datetime.now()
                else:
                    # 如果在执行过程中被取消，则状态应保持为取消
                    self.status = TaskStatus.CANCELLED
                    self.end_time = datetime.now()
                    self.task_cancelled.emit(self.task_id)
                    return
            
            self.task_completed.emit(self.task_id, self.result)
            
        except Exception as e:
            # 发送错误信号
            with self._lock:
                self.status = TaskStatus.FAILED
                self.error = str(e)
                self.end_time = datetime.now()
            
            self.task_error.emit(self.task_id, str(e))
    
    def _check_pause(self):
        """内部方法：检查是否需要暂停，子类可以在执行过程中调用此方法"""
        with self._pause_condition:
            while self._paused and not self._cancelled and self.status == TaskStatus.RUNNING:
                self._pause_condition.wait()  # 等待恢复信号
    
    def pause(self):
        """暂停任务"""
        with self._lock:
            if self.status == TaskStatus.RUNNING:
                self._paused = True
                self.status = TaskStatus.PAUSED
                self.task_paused.emit(self.task_id)
    
    def resume(self):
        """恢复任务"""
        with self._lock:
            if self.status == TaskStatus.PAUSED:
                with self._pause_condition:
                    self._paused = False
                    self.status = TaskStatus.RUNNING
                    self._pause_condition.notify_all()  # 唤醒等待的线程
                self.task_resumed.emit(self.task_id)
    
    def cancel(self):
        """取消任务"""
        with self._lock:
            if self.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PAUSED]:
                self._cancelled = True
                if self.status == TaskStatus.PAUSED:
                    # 如果是暂停状态，需要唤醒线程以便它能处理取消
                    with self._pause_condition:
                        self._pause_condition.notify_all()
                self.status = TaskStatus.CANCELLED
                self.task_cancelled.emit(self.task_id)
    
    def reset(self):
        """重置任务，使其可以重新运行"""
        with self._lock:
            # 只有在已完成、失败或已取消的状态下才能重置
            if self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                self.status = TaskStatus.PENDING
                self._cancelled = False
                self._paused = False
                self.start_time = None
                self.end_time = None
                self.result = None
                self.error = None
    
    def is_cancelled(self) -> bool:
        with self._lock:
            return self._cancelled
    
    def is_paused(self) -> bool:
        """检查任务是否暂停"""
        with self._lock:
            return self._paused and self.status == TaskStatus.PAUSED
    
    def is_running(self) -> bool:
        """检查任务是否正在运行（未暂停）"""
        with self._lock:
            return self.status == TaskStatus.RUNNING
    
    def set_progress(self, progress: int):
        """设置任务进度"""
        self.task_progress.emit(self.task_id, progress)