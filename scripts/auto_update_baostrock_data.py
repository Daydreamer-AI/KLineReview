#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import logging
from datetime import datetime
import time
import random
import argparse

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
# 添加src目录到Python路径，以便导入processor模块
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
    
from src.processor.baostock_processor import BaoStockProcessor
from src.manager.logging_manager import get_logger
from src.utils.process_checker import ProcessChecker, check_main_program_running, wait_for_main_program_exit

def setup_logging(log_level=logging.INFO):
    """设置日志配置"""
    log_dir = os.path.join(project_root, 'data/logs/scripts')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f'baostock_data_update_{datetime.now().strftime("%Y%m%d")}.log')
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return get_logger(__name__)

def check_and_wait_for_main_program(wait_if_running=True, timeout=300):
    """
    检查主程序状态并根据配置决定是否等待
    
    Args:
        wait_if_running: 如果主程序正在运行是否等待
        timeout: 等待超时时间（秒）
        
    Returns:
        True: 可以继续执行
        False: 应该终止执行
    """
    logger = get_logger(__name__)
    
    is_running, processes = check_main_program_running()
    
    if is_running:
        logger.warning("检测到主程序正在运行!")
        
        # 显示正在运行的进程信息
        for proc in processes:
            logger.info(f"主程序进程 - PID: {proc['pid']}, 命令: {proc['cmdline']}")
            
        if wait_if_running:
            logger.info("等待主程序退出...")
            return wait_for_main_program_exit(timeout=timeout)
        else:
            logger.error("主程序正在运行，无法执行更新任务")
            return False
    else:
        logger.info("未检测到主程序运行，可以安全执行更新任务")
        return True

def main():
    parser = argparse.ArgumentParser(description='AKShare板块数据自动更新脚本')
    parser.add_argument('--types', nargs='+', 
                       choices=['industry', 'concept'],
                       help='指定要更新的数据类型')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='设置日志级别')
    parser.add_argument('--force', action='store_true',
                       help='强制执行，即使主程序正在运行')
    parser.add_argument('--wait-timeout', type=int, default=300,
                       help='等待主程序退出的超时时间（秒），默认300秒')
    parser.add_argument('--check-only', action='store_true',
                       help='仅检查主程序状态，不执行更新')
    
    args = parser.parse_args()
    
    # 设置日志级别
    log_levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR
    }
    
    # 重新设置日志
    global setup_logging
    def setup_logging():
        log_dir = os.path.join(project_root, 'data/logs/scripts')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, f'akshare_board_update_{datetime.now().strftime("%Y%m%d")}.log')
        
        logging.basicConfig(
            level=log_levels[args.log_level],
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        return get_logger(__name__)
    
    logger = setup_logging()
    # 仅检查模式
    if args.check_only:
        is_running, processes = check_main_program_running()
        if is_running:
            logger.info(f"检测到 {len(processes)} 个主程序实例正在运行:")
            for i, proc in enumerate(processes, 1):
                logger.info(f"  {i}. PID: {proc['pid']}, 命令: {proc['cmdline']}")
            return 0
        else:
            logger.info("未检测到主程序运行")
            return 0
        
    if not check_and_wait_for_main_program(wait_if_running=True, timeout=300):
        logger.error("主程序仍在运行且等待超时，终止更新任务")
        return 0
        
    # 判断是否是交易日
    bao_stock_processor = BaoStockProcessor()
    logger.info("BaoStockProcessor initialize")
    bao_stock_processor.initialize()

    if not bao_stock_processor.is_trading_day_today():
        logger.info("不是交易日，跳过数据更新...")
        return 0
    
    logger.info("开始更新【沪市】主板日线、周线数据")
    bao_stock_processor.process_sh_main_stock_data()
    time.sleep(random.uniform(5, 10))

    logger.info("开始更新【深市】主板日线、周线数据")
    bao_stock_processor.process_sz_main_stock_data()
    time.sleep(random.uniform(5, 10))

    # logger.info("开始更新【沪市】、【深市】主板15、30、60分钟数据")
    # board_type = ['sh_main', 'sz_main']
    # levels = ['15', '30', '60']
    # for type in board_type:
    #     for level in levels:
    #         bao_stock_processor.process_minute_level_stock_data_with_board_type(type, level)
    #         time.sleep(random.uniform(5, 10))

    logger.info("Baostock 数据更新完成")

    success = True
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()