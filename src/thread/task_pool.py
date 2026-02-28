# file: d:/PythonProject/MPolicy/src/thread/task_pool.py
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThreadPool, pyqtSlot
from typing import Dict, List, Callable, Any, Optional
import time

from thread.base_task import BaseTask, TaskStatus

class TaskPool(QObject):
    """Qt集成的任务线程池"""
    
    # 信号
    pool_started = pyqtSignal()
    pool_stopped = pyqtSignal()
    task_submitted = pyqtSignal(str)  # task_id
    task_finished = pyqtSignal(str)   # task_id
    pool_status_changed = pyqtSignal(int, int)  # running_tasks, pending_tasks
    
    def __init__(self, max_workers: int = 5, name: str = "TaskPool"):
        super().__init__()
        self.max_workers = max_workers
        self.name = name
        self._shutdown = False
        
        # Qt线程池
        self._qt_thread_pool = QThreadPool.globalInstance()
        self._qt_thread_pool.setMaxThreadCount(max_workers)
        
        # 任务管理
        self._tasks: Dict[str, BaseTask] = {}
        self._task_queue: List[BaseTask] = []
        self._running_tasks: List[BaseTask] = []
        
        # 信号连接
        self._connect_signals()
        
        # 监控定时器
        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._update_pool_status)
        self._monitor_timer.start(1000)  # 每秒更新一次状态
    
    def _connect_signals(self):
        """连接任务信号"""
        pass  # 在添加任务时动态连接
    
    def submit(self, task: BaseTask) -> str:
        """提交任务到线程池"""
        if self._shutdown:
            raise RuntimeError("TaskPool is shutdown")
        
        # 设置任务ID
        if task.task_id is None:
            import uuid
            task.task_id = str(uuid.uuid4())
        
        # 存储任务
        self._tasks[task.task_id] = task
        self._task_queue.append(task)
        
        # 连接任务信号
        task.task_started.connect(self._on_task_started)
        task.task_progress.connect(self._on_task_progress)
        task.task_completed.connect(self._on_task_completed)
        task.task_error.connect(self._on_task_error)
        task.task_cancelled.connect(self._on_task_cancelled)
        
        # 发送提交信号
        self.task_submitted.emit(task.task_id)
        
        # 尝试启动任务
        self._try_start_task()
        
        return task.task_id
    
    def _try_start_task(self):
        """尝试启动任务"""
        if (len(self._running_tasks) < self.max_workers and 
            self._task_queue and not self._shutdown):
            
            task = self._task_queue.pop(0)
            self._running_tasks.append(task)
            
            # 在Qt线程池中执行任务
            self._qt_thread_pool.start(task.run)
    
    @pyqtSlot(str)
    def _on_task_started(self, task_id: str):
        """任务开始回调"""
        task = self._tasks.get(task_id)
        if task:
            print(f"Task {task_id} started")
    
    @pyqtSlot(str, int)
    def _on_task_progress(self, task_id: str, progress: int):
        """任务进度回调"""
        print(f"Task {task_id} progress: {progress}%")
    
    @pyqtSlot(str, object)
    def _on_task_completed(self, task_id: str, result: Any):
        """任务完成回调"""
        task = self._tasks.get(task_id)
        if task and task in self._running_tasks:  # 添加检查任务是否在运行列表中
            self._running_tasks.remove(task)
            self.task_finished.emit(task_id)
            self._try_start_task()  # 尝试启动新任务
    
    @pyqtSlot(str, str)
    def _on_task_error(self, task_id: str, error: str):
        """任务错误回调"""
        task = self._tasks.get(task_id)
        if task and task in self._running_tasks:  # 添加检查任务是否在运行列表中
            self._running_tasks.remove(task)
            self.task_finished.emit(task_id)
            self._try_start_task()  # 尝试启动新任务
    
    @pyqtSlot(str)
    def _on_task_cancelled(self, task_id: str):
        """任务取消回调"""
        task = self._tasks.get(task_id)
        if task and task in self._running_tasks:  # 添加检查任务是否在运行列表中
            self._running_tasks.remove(task)
            self.task_finished.emit(task_id)
            self._try_start_task()  # 尝试启动新任务
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        task = self._tasks.get(task_id)
        return task.status if task else None
    
    def get_task_result(self, task_id: str) -> Any:
        """获取任务结果"""
        task = self._tasks.get(task_id)
        return task.result if task else None
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if task:
            task.cancel()
            if task in self._task_queue:
                self._task_queue.remove(task)
            return True
        return False

    def cancel_all_tasks(self):
        """取消所有任务（包括正在运行的和待执行的）"""
        # 取消所有待执行的任务
        for task in self._task_queue[:]:
            self.cancel_task(task.task_id)
        
        # 取消所有正在运行的任务
        for task in self._running_tasks[:]:
            task.cancel()
    
    def _update_pool_status(self):
        """更新线程池状态"""
        running_count = len(self._running_tasks)
        pending_count = len(self._task_queue)
        self.pool_status_changed.emit(running_count, pending_count)
    
    def get_pool_status(self) -> tuple:
        """获取线程池状态 (running_tasks, pending_tasks)"""
        return len(self._running_tasks), len(self._task_queue)
    
    def shutdown(self, wait: bool = True, cancel_running: bool = False):
        """关闭线程池
        
        Args:
            wait: 是否等待任务完成
            cancel_running: 是否取消正在运行的任务
        """
        self._shutdown = True
        self._monitor_timer.stop()
        
        if cancel_running:
            # 取消所有任务
            self.cancel_all_tasks()
        
        # 取消所有待执行任务
        for task in self._task_queue[:]:
            self.cancel_task(task.task_id)
        
        if wait and not cancel_running:
            # 如果不取消运行中的任务，等待它们完成
            self._qt_thread_pool.waitForDone()
        elif cancel_running:
            # 如果取消了运行中的任务，也需要等待线程池清空
            self._qt_thread_pool.waitForDone()
        
        self.pool_stopped.emit()


# ---------------------------------------------------------------------------------------------------

# 默认全局实例
default_task_pool = TaskPool()

def get_default_task_pool() -> TaskPool:
    """获取默认任务池实例"""
    return default_task_pool