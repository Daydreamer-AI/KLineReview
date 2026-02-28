import platform
import os
import json
import configparser
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from manager.logging_manager import get_logger

def get_user_config_dir():
    """获取用户配置目录，与ConfigManager保持一致"""
    system = platform.system()
    
    if system == "Windows":
        # Windows: %APPDATA%\MPolicy\
        config_dir = Path(os.environ.get('APPDATA', '')) / 'MPolicy'
    elif system == "Darwin":  # macOS
        # macOS: ~/Library/Application Support/MPolicy/
        config_dir = Path.home() / 'Library' / 'Application Support' / 'MPolicy'
    else:  # Linux and other Unix-like systems
        # Linux: ~/.config/MPolicy/
        config_dir = Path.home() / '.config' / 'MPolicy'
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

class BaseConfigHandler:
    """配置处理器基类"""
    
    def load_config(self, file_path: Path) -> Union[Dict, configparser.ConfigParser]:
        """加载配置文件"""
        raise NotImplementedError
    
    def save_config(self, config_data: Union[Dict, configparser.ConfigParser], file_path: Path) -> bool:
        """保存配置文件"""
        raise NotImplementedError


class IniConfigHandler(BaseConfigHandler):
    """INI格式配置处理器"""
    
    def load_config(self, file_path: Path) -> configparser.ConfigParser:
        """加载INI配置文件"""
        config = configparser.ConfigParser()
        if file_path.exists():
            config.read(file_path, encoding='utf-8')
        return config
    
    def save_config(self, config_data: configparser.ConfigParser, file_path: Path) -> bool:
        """保存INI配置文件"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as configfile:
            config_data.write(configfile)
        return True


class JsonConfigHandler(BaseConfigHandler):
    """JSON格式配置处理器"""
    
    def load_config(self, file_path: Path) -> Dict:
        """加载JSON配置文件"""
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_config(self, config_data: Dict, file_path: Path) -> bool:
        """保存JSON配置文件"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        return True

# class YamlConfigHandler(BaseConfigHandler):
#     def load_config(self, file_path: Path) -> Dict:
#         import yaml
#         if file_path.exists():
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 return yaml.safe_load(f) or {}
#         return {}
    
#     def save_config(self, config_data: Dict, file_path: Path) -> bool:
#         import yaml
#         file_path.parent.mkdir(parents=True, exist_ok=True)
#         with open(file_path, 'w', encoding='utf-8') as f:
#             yaml.safe_dump(config_data, f, default_flow_style=False, allow_unicode=True)
#         return True

# # 注册YAML处理器
# ConfigManager.register_format_handler('.yaml', YamlConfigHandler)


class ConfigManager:
    """
    增强版配置管理器。
    支持动态修改配置文件路径，并自动管理配置数据的加载与同步。
    支持多种配置文件格式（INI、JSON等）。
    """

    _instance = None
    _lock = threading.Lock()

    # 支持的配置文件格式映射
    _FORMAT_HANDLERS = {
        '.ini': IniConfigHandler,
        '.cfg': IniConfigHandler,
        '.conf': IniConfigHandler,
        '.json': JsonConfigHandler,
    }

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.__initialized = False  # 标记未初始化
            return cls._instance

    def __init__(self):
        """初始化管理器。真正的初始化在 set_config_path 中完成。"""
        if getattr(self, '__initialized', False):
            return
        
        self.logger = get_logger(__name__)
            
        # 使用统一的配置目录函数
        config_dir = get_user_config_dir()
        self._config_path = config_dir / 'config.ini'  # 当前管理的配置文件路径
        self.logger.info(f"正在使用配置文件 '{self._config_path}'")
        
        # 根据文件扩展名选择处理器
        self._config_handler = self._get_handler_for_path(self._config_path)
        self._config_data = self._config_handler.load_config(self._config_path)  # 内存中的配置数据
        self._file_mtime = 0  # 记录文件最后修改时间，用于判断是否需重载
        self._lock = threading.RLock()  # 实例级别的可重入锁，用于线程安全
        self.__initialized = True  # 标记已初始化

    def _get_handler_for_path(self, config_path: Path) -> BaseConfigHandler:
        """根据文件扩展名获取对应的处理器"""
        extension = config_path.suffix.lower()
        if extension in self._FORMAT_HANDLERS:
            return self._FORMAT_HANDLERS[extension]()
        else:
            # 默认使用INI处理器
            self.logger.warning(f"不支持的配置文件格式: {extension}，使用默认INI处理器")
            return IniConfigHandler()

    def set_config_path(self, config_path: Union[str, Path]) -> bool:
        """
        设置或更改配置文件路径，并自动加载该文件。
        如果传入的是相对路径，会将其放在用户配置目录下。

        参数:
            config_path: 新的配置文件路径。

        返回:
            成功加载返回 True，否则返回 False（但会初始化空配置）。
        """
        config_path = Path(config_path)
        
        # 如果是相对路径，将其放置在用户配置目录下
        if not config_path.is_absolute():
            config_dir = get_user_config_dir()
            config_path = config_dir / config_path
        
        with self._lock:
            self._config_path = config_path
            self._config_handler = self._get_handler_for_path(self._config_path)
            return self._load_config()

    def get_config_path(self) -> Optional[Path]:
        """获取当前管理的配置文件路径。"""
        return self._config_path

    def _load_config(self) -> bool:
        """内部方法：从当前路径加载配置到内存。"""
        if self._config_path is None:
            self._config_data = self._config_handler.load_config(Path())  # 加载空配置
            self._file_mtime = 0
            return False

        if self._config_path.exists():
            try:
                # 读取并更新修改时间
                new_mtime = self._config_path.stat().st_mtime
                # 如果文件被修改过，才重新加载
                if new_mtime != self._file_mtime:
                    self._config_data = self._config_handler.load_config(self._config_path)
                    self._file_mtime = new_mtime
                return True
            except (OSError, configparser.Error, json.JSONDecodeError) as e:
                self.logger.error(f"加载配置文件失败: {e}")
                # 加载失败，使用空配置，但不改变原有记忆的mtime，防止覆盖
                self._config_data = self._config_handler.load_config(Path())
                return False
        else:
            # 文件不存在，初始化一个空配置
            self._config_path.parent.mkdir(parents=True, exist_ok=True)  # 确保目录存在
            self._config_data = self._config_handler.load_config(self._config_path)
            self._file_mtime = 0
            self.logger.info(f"配置文件 '{self._config_path}' 不存在，已初始化空配置。")
            return False

    def _ensure_loaded(self) -> None:
        """内部方法：确保内存中的数据是最新的。"""
        if self._config_path is not None:
            self._load_config()  # 简单重载，内部会判断是否需更新

    def save(self, save_path: Union[str, Path, None] = None) -> bool:
        """
        将当前内存中的配置保存到文件。
        如果传入的是相对路径，会将其放在用户配置目录下。

        参数:
            save_path: 指定的保存路径。如果为 None，则使用当前管理的路径。

        返回:
            成功保存返回 True，否则返回 False。
        """
        with self._lock:
            if save_path is not None:
                target_path = Path(save_path)
                # 如果是相对路径，将其放置在用户配置目录下
                if not target_path.is_absolute():
                    config_dir = get_user_config_dir()
                    target_path = config_dir / target_path
            else:
                target_path = self._config_path
                
            if target_path is None:
                self.logger.error("错误：未指定保存路径且当前无管理路径。")
                return False

            try:
                success = self._config_handler.save_config(self._config_data, target_path)
                if success:
                    # 更新内存中记录的文件修改时间
                    self._file_mtime = target_path.stat().st_mtime if target_path.exists() else 0
                return success
            except (OSError, configparser.Error, TypeError) as e:
                self.logger.error(f"保存配置文件失败: {e}")
                return False

    def get(self, section: str, key: str, default: Any = None) -> Optional[str]:
        """获取字符串配置值。支持INI和JSON格式"""
        with self._lock:
            self._ensure_loaded()
            
            # 如果是INI格式
            if isinstance(self._config_data, configparser.ConfigParser):
                try:
                    return self._config_data[section][key]
                except KeyError:
                    return default
            # 如果是JSON格式
            elif isinstance(self._config_data, dict):
                try:
                    return str(self._config_data[section][key])
                except KeyError:
                    return default
            else:
                return default

    def getint(self, section: str, key: str, default: int = None) -> Optional[int]:
        """获取整数配置值。支持INI和JSON格式"""
        with self._lock:
            self._ensure_loaded()
            
            # 如果是INI格式
            if isinstance(self._config_data, configparser.ConfigParser):
                try:
                    return self._config_data.getint(section, key)
                except (ValueError, configparser.NoSectionError, configparser.NoOptionError):
                    return default
            # 如果是JSON格式
            elif isinstance(self._config_data, dict):
                try:
                    value = self._config_data[section][key]
                    return int(value)
                except (KeyError, ValueError, TypeError):
                    return default
            else:
                return default

    def getbool(self, section: str, key: str, default: bool = None) -> Optional[bool]:
        """获取布尔配置值。支持INI和JSON格式"""
        with self._lock:
            self._ensure_loaded()
            
            # 如果是INI格式
            if isinstance(self._config_data, configparser.ConfigParser):
                try:
                    return self._config_data.getboolean(section, key)
                except (ValueError, configparser.NoSectionError, configparser.NoOptionError):
                    return default
            # 如果是JSON格式
            elif isinstance(self._config_data, dict):
                try:
                    value = self._config_data[section][key]
                    if isinstance(value, bool):
                        return value
                    elif isinstance(value, str):
                        return value.lower() in ('true', '1', 'yes', 'on')
                    elif isinstance(value, (int, float)):
                        return bool(value)
                    else:
                        return default
                except KeyError:
                    return default
            else:
                return default

    def set(self, section: str, key: str, value: Any) -> None:
        """设置配置值。支持INI和JSON格式"""
        with self._lock:
            self._ensure_loaded()  # 确保操作的是最新配置
            
            # 如果是INI格式
            if isinstance(self._config_data, configparser.ConfigParser):
                if not self._config_data.has_section(section):
                    self._config_data.add_section(section)
                self._config_data[section][key] = str(value)
            # 如果是JSON格式
            elif isinstance(self._config_data, dict):
                if section not in self._config_data:
                    self._config_data[section] = {}
                self._config_data[section][key] = value

    def remove_key(self, section: str, key: str) -> bool:
        """删除配置项。支持INI和JSON格式"""
        with self._lock:
            self._ensure_loaded()
            
            # 如果是INI格式
            if isinstance(self._config_data, configparser.ConfigParser):
                try:
                    return self._config_data.remove_option(section, key)
                except (configparser.NoSectionError, configparser.NoOptionError):
                    return False
            # 如果是JSON格式
            elif isinstance(self._config_data, dict):
                try:
                    if section in self._config_data and key in self._config_data[section]:
                        del self._config_data[section][key]
                        # 如果section变空，删除整个section
                        if not self._config_data[section]:
                            del self._config_data[section]
                        return True
                    return False
                except KeyError:
                    return False
            else:
                return False

    def remove_section(self, section: str) -> bool:
        """删除整个配置块。支持INI和JSON格式"""
        with self._lock:
            self._ensure_loaded()
            
            # 如果是INI格式
            if isinstance(self._config_data, configparser.ConfigParser):
                return self._config_data.remove_section(section)
            # 如果是JSON格式
            elif isinstance(self._config_data, dict):
                try:
                    if section in self._config_data:
                        del self._config_data[section]
                        return True
                    return False
                except KeyError:
                    return False
            else:
                return False

    def has_section(self, section: str) -> bool:
        """检查配置块是否存在。支持INI和JSON格式"""
        with self._lock:
            self._ensure_loaded()
            
            # 如果是INI格式
            if isinstance(self._config_data, configparser.ConfigParser):
                return self._config_data.has_section(section)
            # 如果是JSON格式
            elif isinstance(self._config_data, dict):
                return section in self._config_data
            else:
                return False

    def has_key(self, section: str, key: str) -> bool:
        """检查配置项是否存在。支持INI和JSON格式"""
        with self._lock:
            self._ensure_loaded()
            
            # 如果是INI格式
            if isinstance(self._config_data, configparser.ConfigParser):
                return self._config_data.has_option(section, key)
            # 如果是JSON格式
            elif isinstance(self._config_data, dict):
                return section in self._config_data and key in self._config_data[section]
            else:
                return False

    def reload(self) -> bool:
        """强制从当前配置文件重新加载，丢弃未保存的更改。"""
        with self._lock:
            return self._load_config()

    def clear_in_memory(self) -> None:
        """清空内存中的配置数据（不删除文件）。"""
        with self._lock:
            self._config_data = self._config_handler.load_config(Path())
            self._file_mtime = 0

    def get_all_sections(self) -> List[str]:
        """获取所有配置节的名称。支持INI和JSON格式"""
        with self._lock:
            self._ensure_loaded()
            
            # 如果是INI格式
            if isinstance(self._config_data, configparser.ConfigParser):
                return list(self._config_data.sections())
            # 如果是JSON格式
            elif isinstance(self._config_data, dict):
                return list(self._config_data.keys())
            else:
                return []

    def get_section(self, section: str) -> Dict[str, Any]:
        """获取指定节的所有配置项。支持INI和JSON格式"""
        with self._lock:
            self._ensure_loaded()
            
            # 如果是INI格式
            if isinstance(self._config_data, configparser.ConfigParser):
                if self._config_data.has_section(section):
                    return dict(self._config_data[section])
                else:
                    return {}
            # 如果是JSON格式
            elif isinstance(self._config_data, dict):
                return self._config_data.get(section, {})
            else:
                return {}

    @classmethod
    def register_format_handler(cls, extension: str, handler_class: type):
        """注册新的配置文件格式处理器"""
        if not issubclass(handler_class, BaseConfigHandler):
            raise TypeError("处理器必须继承自 BaseConfigHandler")
        
        cls._FORMAT_HANDLERS[extension.lower()] = handler_class
        cls._FORMAT_HANDLERS[extension.lower()] = handler_class


# 使用示例
if __name__ == "__main__":
    # 创建配置管理器实例
    manager = ConfigManager()

    # 1. 使用INI格式 - 相对路径会被放在用户配置目录下
    manager.set_config_path('config_a.ini')  # 实际路径: 用户配置目录/config_a.ini
    manager.set('Database', 'host', 'host_a.com')
    manager.set('Database', 'port', 5432)
    manager.set('App', 'debug', True)
    manager.save()

    # 2. 切换到JSON格式
    manager.set_config_path('config_b.json')  # 实际路径: 用户配置目录/config_b.json
    manager.set('Database', 'host', 'host_b.com')
    manager.set('Database', 'port', 3306)
    manager.set('App', 'debug', False)
    manager.save()

    # 3. 读取配置
    db_host = manager.get('Database', 'host')
    db_port = manager.getint('Database', 'port')
    is_debug = manager.getbool('App', 'debug')
    
    print(f"Host: {db_host}, Port: {db_port}, Debug: {is_debug}")