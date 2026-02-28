#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import argparse

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.utils.process_checker import check_main_program_running

def main():
    parser = argparse.ArgumentParser(description='检查MPolicy主程序是否正在运行')
    parser.add_argument('--quiet', '-q', action='store_true', 
                       help='静默模式，仅返回退出码')
    parser.add_argument('--detail', '-d', action='store_true',
                       help='显示详细进程信息')
    
    args = parser.parse_args()
    
    is_running, processes = check_main_program_running()
    
    if is_running:
        if not args.quiet:
            print(f"检测到 {len(processes)} 个MPolicy主程序实例正在运行:")
            for i, proc in enumerate(processes, 1):
                print(f"  {i}. PID: {proc['pid']}")
                if args.detail:
                    print(f"     命令: {proc['cmdline']}")
        return 1  # 主程序正在运行
    else:
        if not args.quiet:
            print("未检测到MPolicy主程序运行")
        return 0  # 主程序未运行

if __name__ == "__main__":
    sys.exit(main())