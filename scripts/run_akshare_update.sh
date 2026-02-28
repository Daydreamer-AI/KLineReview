#!/bin/bash

# 自动检测并激活Python环境，然后运行AKShare数据更新脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 函数：检查主程序是否正在运行
check_main_program() {
    echo "检查MPolicy主程序是否正在运行..."
    
    # 使用专门的检查脚本
    if python scripts/check_process.py --quiet; then
        echo "✓ 未检测到主程序运行，可以安全执行更新任务"
        return 0
    else
        echo "✗ 检测到主程序正在运行"
        return 1
    fi
}

# 函数：激活conda环境
activate_conda() {
    # 检查conda命令是否存在
    if command -v conda &> /dev/null; then
        echo "检测到Conda环境..."
        
        # 初始化conda（如果需要）
        if [[ -z "$CONDA_DEFAULT_ENV" ]]; then
            # 尝试source conda
            if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
                source "$HOME/miniconda3/etc/profile.d/conda.sh"
            elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
                source "$HOME/anaconda3/etc/profile.d/conda.sh"
            elif [ -f "/opt/miniconda3/etc/profile.d/conda.sh" ]; then
                source "/opt/miniconda3/etc/profile.d/conda.sh"
            elif [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
                source "/opt/anaconda3/etc/profile.d/conda.sh"
            fi
        fi
        
        # 激活base环境（可根据需要修改）
        conda activate base 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "Conda环境已激活"
            return 0
        else
            echo "警告: Conda环境激活失败"
            return 1
        fi
    fi
    return 1
}

# 函数：激活virtualenv环境
activate_venv() {
    # 检查常见的虚拟环境位置
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        echo "检测到venv虚拟环境..."
        source "$PROJECT_ROOT/venv/bin/activate"
        return 0
    elif [ -f "$PROJECT_ROOT/env/bin/activate" ]; then
        echo "检测到env虚拟环境..."
        source "$PROJECT_ROOT/env/bin/activate"
        return 0
    fi
    return 1
}

# 检查强制执行标志
FORCE_RUN=false
for arg in "$@"; do
    if [ "$arg" = "--force" ]; then
        FORCE_RUN=true
        break
    fi
done

# 检查主程序状态（除非强制执行）
if [ "$FORCE_RUN" = false ]; then
    if ! check_main_program; then
        echo "请先关闭主程序再运行此脚本，或使用 --force 参数强制执行"
        exit 1
    fi
else
    echo "警告: 强制模式下执行，跳过主程序检查"
fi

# 尝试激活环境
if ! activate_conda; then
    if ! activate_venv; then
        echo "未检测到虚拟环境，使用系统Python"
    fi
fi

# 检查Python版本
echo "Python版本: $(python --version 2>&1)"

# 运行Python脚本
echo "开始执行AKShare板块数据更新..."
python scripts/auto_update_akshare_board_data.py "$@"

# 检查执行结果
if [ $? -eq 0 ]; then
    echo "脚本执行完成!"
else
    echo "脚本执行出现错误!"
    exit 1
fi