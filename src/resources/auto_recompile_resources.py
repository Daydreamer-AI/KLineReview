#!/usr/bin/env python3
"""
自动编译 Qt 资源文件 (.qrc) 的脚本
默认输入: ./src/resources/resources.qrc
默认输出: ./src/resources/resources_rc.py

每次修改完qrc资源动修改后，请运行此脚本以重新编译资源文件。
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# 定义默认路径
DEFAULT_QRC_FILE = "./src/resources/resources.qrc"
DEFAULT_OUTPUT_FILE = "./src/resources/resources_rc.py"

def compile_qrc_file(qrc_file_path=DEFAULT_QRC_FILE, output_file_path=DEFAULT_OUTPUT_FILE, compiler_type="pyqt5"):
    """
    手动编译指定的 .qrc 文件
    
    :param qrc_file_path: .qrc 文件的路径，默认为 ./src/resources/resources.qrc
    :param output_file_path: 输出的 _rc.py 文件路径，默认为 ./src/resources/resources_rc.py
    :param compiler_type: 编译器类型，'auto'（自动检测）, 'pyqt5', 'pyside6'
    :return: 布尔值，表示编译是否成功
    """
    # 检查 .qrc 文件是否存在
    if not os.path.exists(qrc_file_path):
        print(f"错误：未找到文件 {qrc_file_path}")
        print(f"请确保文件存在，或使用 -i 参数指定其他路径")
        return False
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")
    
    # 确定编译器
    compiler = None
    if compiler_type == "auto":
        # 尝试自动检测可用的编译器
        for candidate in ["pyrcc5", "pyside6-rcc"]:
            try:
                subprocess.run([candidate, "--version"], capture_output=True, check=True)
                compiler = candidate
                print(f"检测到并使用编译器: {compiler}")
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        if compiler is None:
            print("错误：未找到可用的资源编译器。请确保已安装 PyQt5 或 PySide6。")
            print("您可以尝试使用 -c 参数明确指定编译器类型")
            return False
    else:
        compiler_map = {
            "pyqt5": "pyrcc5",
            "pyside6": "pyside6-rcc"
        }
        compiler = compiler_map.get(compiler_type)
    
    # 执行编译命令
    compile_command = [compiler, qrc_file_path, "-o", output_file_path]
    
    try:
        print(f"正在编译: {qrc_file_path} -> {output_file_path}")
        print(f"执行命令: {' '.join(compile_command)}")
        
        result = subprocess.run(compile_command, check=True, capture_output=True, text=True)
        
        print("✅ 编译成功！")
        if result.stderr:
            print(f"编译器输出: {result.stderr}")
        
        # 验证输出文件是否已创建
        if os.path.exists(output_file_path):
            print(f"输出文件已创建: {output_file_path}")
        else:
            print("⚠️  警告：编译命令执行成功，但未找到输出文件")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 编译失败！退出码: {e.returncode}")
        if e.stderr:
            print(f"错误信息: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ 编译过程中发生未知错误: {e}")
        return False

def main():
    """命令行入口点"""
    parser = argparse.ArgumentParser(
        description="手动编译 Qt 资源文件 (.qrc)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
示例:
  %(prog)s                       # 使用默认路径编译
  %(prog)s -i other.qrc         # 指定不同的输入文件
  %(prog)s -o ui/resources.py   # 指定不同的输出文件
  %(prog)s -c pyqt5             # 明确使用 PyQt5 编译器
  %(prog)s -i other.qrc -o other_rc.py -c pyside6  # 组合使用
        """
    )
    
    parser.add_argument("-i", "--input", default=DEFAULT_QRC_FILE,
                       help=f"输入的 .qrc 文件路径 (默认: {DEFAULT_QRC_FILE})")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_FILE,
                       help=f"输出的 _rc.py 文件路径 (默认: {DEFAULT_OUTPUT_FILE})")
    parser.add_argument("-c", "--compiler", choices=["auto", "pyqt5", "pyside6"], 
                       default="pyqt5", help="编译器类型 (默认: pyqt5)")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Qt 资源文件编译工具")
    print("=" * 50)
    
    success = compile_qrc_file(args.input, args.output, args.compiler)
    
    print("=" * 50)
    if success:
        print("操作完成 ✅")
    else:
        print("操作失败 ❌")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()