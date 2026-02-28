import os
import sys
import logging
import logging.config
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Dict, Optional, Union
import json
from datetime import datetime  # 添加datetime导入

class LogManager:
    """
        通用的日志管理类，支持多环境配置和模块化日志记录
    
        示例：
        main():
            # 初始化日志系统
            setup_logging(
                log_dir="logs",
                level="INFO",
                enable_file_log=True,
                max_bytes=10 * 1024 * 1024,
                backup_count=5,
                unique_log_file=True  # 启用唯一日志文件名
            )
        
            logger = get_logger(__name__)
            logger.info("应用程序启动")

        模块中使用：
        logger = get_logger(__name__)
        logger.info("模块日志记录")

        类中使用：
        self.logger = get_logger(__name__)
        self.logger.info("类日志记录")
    """
    
    # 默认配置模板
    DEFAULT_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'detailed': {
                'format': '%(asctime)s.%(msecs)03d [%(levelname)-8s] %(name)s:%(filename)s:%(lineno)d - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'json': {
                'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "file": "%(filename)s", "line": %(lineno)d, "message": "%(message)s"}',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            }
        },
        'loggers': {
            '': {  # 根日志器
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False
            }
        }
    }
    
    _initialized = False
    
    @classmethod
    def setup_logging(
        cls,
        log_dir: str = "logs",
        level: str = "INFO",
        enable_file_log: bool = True,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        when: str = "midnight",  # 时间轮转间隔
        interval: int = 1,
        json_format: bool = False,
        config_file: Optional[str] = None,
        unique_log_file: bool = False  # 新增参数控制是否使用唯一文件名
    ) -> None:
        """
        设置日志系统
        
        Args:
            log_dir: 日志文件目录
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            enable_file_log: 是否启用文件日志
            max_bytes: 单个日志文件最大大小（字节）
            backup_count: 保留的备份文件数量
            when: 时间轮转间隔 ('S', 'M', 'H', 'D', 'W0-W6', 'midnight')
            interval: 轮转间隔数值
            json_format: 是否使用JSON格式（适合日志分析系统）
            config_file: 外部配置文件路径（JSON或YAML）
            unique_log_file: 是否为每次运行创建唯一的日志文件名
        """
        if cls._initialized:
            return
            
        # 使用外部配置文件（如果提供）
        if config_file and os.path.exists(config_file):
            cls._setup_from_config_file(config_file)
        else:
            cls._setup_from_parameters(
                log_dir, level, enable_file_log, max_bytes, 
                backup_count, when, interval, json_format, unique_log_file  # 传递新参数
            )
        
        # 设置全局异常处理
        cls._setup_global_exception_handler()
        cls._initialized = True
        
        # 记录日志系统启动信息
        logger = cls.get_logger(__name__)
        logger.info("日志系统初始化完成 - 级别: %s, 文件输出: %s", level, enable_file_log)
    
    @classmethod
    def _setup_from_config_file(cls, config_file: str) -> None:
        """从配置文件设置日志"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.endswith('.json'):
                    config = json.load(f)
                elif config_file.endswith(('.yaml', '.yml')):
                    import yaml
                    config = yaml.safe_load(f)
                else:
                    raise ValueError("不支持的配置文件格式，支持 JSON 或 YAML")
                
            logging.config.dictConfig(config)
        except Exception as e:
            print(f"加载日志配置文件失败: {e}，使用默认配置")
            logging.basicConfig(level=logging.INFO)
    
    @classmethod
    def _setup_from_parameters(
        cls, log_dir: str, level: str, enable_file_log: bool, 
        max_bytes: int, backup_count: int, when: str, interval: int, 
        json_format: bool, unique_log_file: bool  # 添加新参数
    ) -> None:
        """通过参数设置日志"""
        config = cls.DEFAULT_CONFIG.copy()
        
        # 设置格式器
        formatter_name = 'json' if json_format else 'detailed'
        
        # 确保日志目录存在
        if enable_file_log:
            os.makedirs(log_dir, exist_ok=True)
            
            # 根据unique_log_file参数决定文件名
            if unique_log_file:
                # 使用当前时间生成唯一的日志文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_filename = os.path.join(log_dir, f'app_{timestamp}.log')
            else:
                # 使用默认的日志文件名
                log_filename = os.path.join(log_dir, 'app.log')
            
            # 添加文件处理器
            config['handlers']['file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': level,
                'formatter': formatter_name,
                'filename': log_filename,  # 使用新的文件名
                'maxBytes': max_bytes,
                'backupCount': backup_count,
                'encoding': 'utf-8'
            }
            
            # 添加错误日志文件处理器
            config['handlers']['error_file'] = {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'level': 'ERROR',
                'formatter': formatter_name,
                'filename': os.path.join(log_dir, 'error.log'),
                'when': when,
                'interval': interval,
                'backupCount': backup_count,
                'encoding': 'utf-8'
            }
            
            # 更新根日志器配置
            config['loggers']['']['handlers'] = ['console', 'file', 'error_file']
        else:
            # 仅控制台输出
            config['loggers']['']['handlers'] = ['console']
        
        # 设置日志级别
        config['loggers']['']['level'] = level
        config['handlers']['console']['level'] = level
        
        # 应用配置
        logging.config.dictConfig(config)
    
    @classmethod
    def _setup_global_exception_handler(cls) -> None:
        """设置全局异常处理器"""
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
                
            logger = cls.get_logger('global_exception')
            logger.critical(
                "未处理的异常", 
                exc_info=(exc_type, exc_value, exc_traceback)
            )
        
        sys.excepthook = handle_exception
    
    @classmethod
    def get_logger(cls, name: str = None) -> logging.Logger:
        """
        获取日志记录器
        
        Args:
            name: 日志记录器名称，通常使用 __name__
            
        Returns:
           配置好的日志记录器实例
        """
        if name is None:
            name = 'root'
        
        logger = logging.getLogger(name)
        return logger
    
    @classmethod
    def set_level(cls, level: Union[str, int]) -> None:
        """
        动态设置日志级别
        
        Args:
            level: 日志级别 ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') 或对应数值
        """
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        
        logging.getLogger().setLevel(level)
        for handler in logging.getLogger().handlers:
            handler.setLevel(level)

# 便捷函数
def setup_logging(**kwargs) -> None:
    """便捷函数：设置日志系统"""
    LogManager.setup_logging(**kwargs)

def get_logger(name: str = None) -> logging.Logger:
    """便捷函数：获取日志记录器"""
    return LogManager.get_logger(name)