import os
import sys
import platform
import subprocess
from typing import Optional, Any, Dict
from dotenv import load_dotenv, set_key, unset_key

class EnvironmentConfigManager:
    _instance = None
    _env_file = ".env"

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(EnvironmentConfigManager, cls).__new__(cls)
            load_dotenv(cls._env_file)  
        return cls._instance

    # ================= 1. 读取 (Get) =================
    @staticmethod
    def get(key: str, default: Any = None, required: bool = False, cast: type = str) -> Any:
        value = os.environ.get(key)
        if value is None:
            if required:
                error_msg = f"[配置错误] 缺少必需的环境变量: {key}"
                print(error_msg, file=sys.stderr)
                raise EnvironmentError(error_msg)
            return default
        try:
            if cast == bool:
                return value.lower() in ('true', '1', 'yes', 'y')
            return cast(value)
        except (ValueError, TypeError) as e:
            print(f"[配置警告] 环境变量 {key} 无法转换为 {cast.__name__} 类型: {e}", file=sys.stderr)
            return default

    # ================= 2. 设置/修改 (Set) =================
    @staticmethod
    def set(key: str, value: Any, persist: bool = False, to_system: bool = False):
        """
        设置或修改环境变量。
        :param persist: 是否写入项目本地的 .env 文件
        :param to_system: 是否写入操作系统的永久环境变量（需要重启IDE或终端生效）
        """
        str_value = str(value)
        
        # 1. 始终更新当前进程的内存环境
        os.environ[key] = str_value
        
        # 2. 写入本地 .env 文件
        if persist:
            try:
                set_key(EnvironmentConfigManager._env_file, key, str_value)
            except Exception as e:
                print(f"[配置警告] 写入 .env 文件失败: {e}", file=sys.stderr)
                
        # 3. 【核心修复】写入操作系统永久环境变量
        if to_system:
            try:
                current_os = platform.system()
                if current_os == "Windows":
                    # 使用 setx 命令写入 Windows 用户级环境变量
                    # 注意：setx 有 1024 字符长度限制，API Key 通常没问题
                    subprocess.run(["setx", key, str_value], check=True, capture_output=True)
                    print(f"[系统配置] 已写入 Windows 系统环境变量: {key} (请重启终端或IDE生效)")
                    
                elif current_os in ("Linux", "Darwin"):
                    # macOS / Linux 追加到 ~/.bashrc 或 ~/.zshrc
                    shell_rc = os.path.expanduser("~/.zshrc") if current_os == "Darwin" else os.path.expanduser("~/.bashrc")
                    export_line = f'export {key}="{str_value}"\n'
                    
                    # 简单防重复写入检查
                    with open(shell_rc, "r") as f:
                        if export_line not in f.read():
                            with open(shell_rc, "a") as f_append:
                                f_append.write(export_line)
                            print(f"[系统配置] 已追加到 {shell_rc} (请执行 source {shell_rc} 或重启终端生效)")
                else:
                    print(f"[系统警告] 不支持的操作系统: {current_os}")
            except Exception as e:
                print(f"[系统警告] 写入系统环境变量失败: {e}", file=sys.stderr)

    # ================= 3. 删除 (Delete) =================
    @staticmethod
    def delete(key: str, persist: bool = False, from_system: bool = False):
        if key in os.environ:
            del os.environ[key]
            
        if persist:
            try:
                unset_key(EnvironmentConfigManager._env_file, key)
            except Exception as e:
                print(f"[配置警告] 从 .env 文件删除失败: {e}", file=sys.stderr)
                
        if from_system:
            try:
                if platform.system() == "Windows":
                    # Windows 下将值设为空字符串即可删除
                    subprocess.run(["setx", key, ""], check=True, capture_output=True)
                else:
                    print("[系统提示] Linux/macOS 请手动编辑 ~/.zshrc 或 ~/.bashrc 删除对应 export 行")
            except Exception as e:
                print(f"[系统警告] 删除系统环境变量失败: {e}", file=sys.stderr)

    # ================= 5. 检查是否存在 (Exists) =================
    @staticmethod
    def exists(key: str) -> bool:
        return key in os.environ