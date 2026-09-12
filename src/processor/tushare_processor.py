import tushare as ts
import threading
import traceback
import gc

from PyQt5.QtCore import QObject, pyqtSignal

from manager.logging_manager import get_logger
from manager.environment_config_manager import EnvironmentConfigManager

TUSHARE_PRO_API_KEY = "Tushare_Pro_API_KEY"

def singleton(cls):
    """
    一个线程安全的单例装饰器。
    使用双重检查锁模式确保在多线程环境下也只创建一个实例。
    """
    instances = {}  # 用于存储被装饰类的唯一实例
    lock = threading.Lock()  # 创建一个锁对象，用于同步

    def get_instance(*args, **kwargs):
        # 第一次检查（无锁）：如果实例已存在，直接返回，避免绝大多数不必要的锁开销
        if cls not in instances:
            with lock:  # 加锁，确保同一时间只有一个线程能进入下面的代码块
                # 第二次检查（有锁）：防止在等待锁的过程中，已有其他线程创建了实例
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)  # 创建唯一的实例
        return instances[cls]

    return get_instance

# 使用装饰器
@singleton
class TushareProcessor:
    def __init__(self):
        super().__init__() 
        self.logger = get_logger(__name__)

        self.tushare_pro = None
        self._is_initialized = False # 初始化状态标志

    def initialize(self) -> bool:
        """显式登录TuShare系统。应在程序开始时调用。"""
        try:
            key_value = EnvironmentConfigManager.get(TUSHARE_PRO_API_KEY)
            # self.logger.info(f"Tushare login successful. API key: {key_value}")

            if key_value == '' or key_value is None: 
                self.logger.info("Tushare login failed. API key is empty.")
                return False

            self.tushare_pro = ts.pro_api(key_value)
            
            # self.logger.info(f"self.tushare_pro type: {type(self.tushare_pro)}, self.tushare_pro: {self.tushare_pro}")

            if self.tushare_pro is not None: 
                self.logger.info("Tushare login successful.")
                self._is_initialized = True
                return True
            else:
                self.logger.info("Tushare login failed.")
                return False
            
        except Exception as e:
            self.logger.info("An error occurred during Tushare login.")
            self.logger.info(f"Traceback: {traceback.format_exc()}")
            return False
