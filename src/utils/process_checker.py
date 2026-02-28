#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用进程检查工具
用于检测特定程序是否正在运行，避免冲突执行
"""

import os
import sys
import psutil
import platform
import time
from typing import List, Dict, Tuple, Optional
from src.manager.logging_manager import get_logger

class ProcessChecker:
    """
    通用进程检查器
    """
    
    def __init__(self, logger_name: str = __name__):
        """
        初始化进程检查器
        
        Args:
            logger_name: 日志记录器名称
        """
        self.logger = get_logger(logger_name)
        self.current_pid = os.getpid()
        
    def find_processes_by_name(self, process_name: str) -> List[Dict]:
        """
        根据进程名称查找进程
        
        Args:
            process_name: 进程名称（部分匹配）
            
        Returns:
            匹配的进程列表，每个元素包含pid、name、cmdline信息
        """
        matched_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # 跳过当前进程
                if proc.info['pid'] == self.current_pid:
                    continue
                    
                # 检查进程名称匹配
                if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                    matched_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    })
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # 忽略无法访问的进程
                continue
                
        return matched_processes
    
    def find_processes_by_cmdline(self, cmdline_keywords: List[str]) -> List[Dict]:
        """
        根据命令行关键字查找进程
        
        Args:
            cmdline_keywords: 命令行关键字列表，必须全部匹配才算匹配
            
        Returns:
            匹配的进程列表
        """
        matched_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # 跳过当前进程
                if proc.info['pid'] == self.current_pid:
                    continue
                    
                cmdline_str = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                
                # 检查所有关键字是否都在命令行中
                if all(keyword in cmdline_str for keyword in cmdline_keywords):
                    matched_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': cmdline_str
                    })
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # 忽略无法访问的进程
                continue
                
        return matched_processes
    
    def is_process_running_by_name(self, process_name: str) -> Tuple[bool, List[Dict]]:
        """
        检查指定名称的进程是否正在运行
        
        Args:
            process_name: 进程名称
            
        Returns:
            (是否运行, 进程列表)
        """
        processes = self.find_processes_by_name(process_name)
        return len(processes) > 0, processes
    
    def is_process_running_by_cmdline(self, cmdline_keywords: List[str]) -> Tuple[bool, List[Dict]]:
        """
        检查包含指定命令行关键字的进程是否正在运行
        
        Args:
            cmdline_keywords: 命令行关键字列表
            
        Returns:
            (是否运行, 进程列表)
        """
        processes = self.find_processes_by_cmdline(cmdline_keywords)
        return len(processes) > 0, processes
    
    def wait_for_process_exit(self, 
                            cmdline_keywords: List[str], 
                            timeout: int = 300, 
                            check_interval: int = 10) -> bool:
        """
        等待指定进程退出
        
        Args:
            cmdline_keywords: 命令行关键字列表
            timeout: 超时时间（秒）
            check_interval: 检查间隔（秒）
            
        Returns:
            True: 进程已退出或超时
            False: 被中断
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            is_running, processes = self.is_process_running_by_cmdline(cmdline_keywords)
            if not is_running:
                self.logger.info("目标进程已退出")
                return True
                
            # 显示正在运行的进程信息
            self.logger.info(f"检测到 {len(processes)} 个目标进程正在运行:")
            for i, proc in enumerate(processes, 1):
                self.logger.info(f"  {i}. PID: {proc['pid']}, 命令: {proc['cmdline'][:100]}...")
                
            remaining_time = int(timeout - (time.time() - start_time))
            self.logger.info(f"等待进程退出... (剩余 {remaining_time} 秒)")
            time.sleep(check_interval)
        
        self.logger.warning(f"等待进程退出超时 ({timeout}秒)")
        return False
    
    def terminate_process(self, pid: int, timeout: int = 10) -> bool:
        """
        终止指定PID的进程
        
        Args:
            pid: 进程ID
            timeout: 等待进程终止的超时时间
            
        Returns:
            True: 成功终止
            False: 终止失败
        """
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            proc.wait(timeout=timeout)
            self.logger.info(f"成功终止进程 PID: {pid}")
            return True
        except psutil.NoSuchProcess:
            self.logger.warning(f"进程 PID: {pid} 不存在")
            return True
        except psutil.TimeoutExpired:
            self.logger.warning(f"进程 PID: {pid} 终止超时，尝试强制杀死")
            try:
                proc.kill()
                proc.wait(timeout=5)
                self.logger.info(f"成功强制杀死进程 PID: {pid}")
                return True
            except Exception as e:
                self.logger.error(f"强制杀死进程 PID: {pid} 失败: {e}")
                return False
        except Exception as e:
            self.logger.error(f"终止进程 PID: {pid} 失败: {e}")
            return False

# 便捷函数
# def check_main_program_running() -> Tuple[bool, List[Dict]]:
#     """
#     检查主程序是否正在运行
    
#     Returns:
#         (是否运行, 进程列表)
#     """
#     checker = ProcessChecker()
#     return checker.is_process_running_by_cmdline(['main.py'])
def check_main_program_running() -> Tuple[bool, List[Dict]]:
    """
    检查主程序是否正在运行
    
    Returns:
        (是否运行, 进程列表)
    """
    checker = ProcessChecker()
    # 优先检查环境变量标识
    is_running, processes = checker.is_process_running_by_cmdline(['--mpolicy-main-process'])
    if not is_running:
        # 回退到检查main.py
        is_running, processes = checker.is_process_running_by_cmdline(['main.py'])
    return is_running, processes

def wait_for_main_program_exit(timeout: int = 300, check_interval: int = 10) -> bool:
    """
    等待主程序退出
    
    Args:
        timeout: 超时时间（秒）
        check_interval: 检查间隔（秒）
        
    Returns:
        True: 主程序已退出或超时
        False: 被中断
    """
    checker = ProcessChecker()
    return checker.wait_for_process_exit(['main.py'], timeout, check_interval)

def check_script_running(script_name: str) -> Tuple[bool, List[Dict]]:
    """
    检查指定脚本是否正在运行
    
    Args:
        script_name: 脚本名称
        
    Returns:
        (是否运行, 进程列表)
    """
    checker = ProcessChecker()
    return checker.is_process_running_by_cmdline([script_name])

# 兼容旧版本API
def is_main_program_running():
    """
    兼容旧版本API
    检查主程序是否正在运行
    
    Returns:
        (是否运行, 进程列表)
    """
    return check_main_program_running()