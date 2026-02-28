@echo off
REM 自动检测并激活Python环境，然后运行AKShare数据更新脚本

SET SCRIPT_DIR=%~dp0
SET PROJECT_ROOT=%SCRIPT_DIR%..

REM 切换到项目根目录
cd /d "%PROJECT_ROOT%"

echo check MPolicy main program is running or not...

REM 检测conda环境
@REM where conda >nul 2>nul
@REM if %ERRORLEVEL% EQU 0 (
@REM     echo Conda environment detected...
@REM     REM 激活默认conda环境（可以根据需要修改环境名）
@REM     call conda activate base
@REM     if ERRORLEVEL 1 (
@REM         echo Warning: Conda environment activation failed, attempt to use system Python
@REM     ) else (
@REM         echo The Conda environment is activated
@REM     )
@REM ) else (
    echo Conda is not detected, check the virtual environment...
    REM 检查venv环境
    if exist "%PROJECT_ROOT%\.venv\Scripts\activate.bat" (
        echo Venv virtual environment detected...
        call "%PROJECT_ROOT%\.venv\Scripts\activate.bat"
    ) else if exist "%PROJECT_ROOT%\.venv\Scripts\activate.bat" (
        echo Venv virtual environment detected...
        call "%PROJECT_ROOT%\.venv\Scripts\activate.bat"
    ) else (
        echo No virtual environment detected, using system Python
    )
@REM )

REM 检查主程序是否正在运行
python scripts/check_process.py --quiet
if %ERRORLEVEL% EQU 1 (
    echo error: MPolicy is running, cannot update!

    echo please close MPolicy first!
    if /I "%1" NEQ "--force" (
        pause
        exit /b 1
    ) else (
        echo warning: force mode, continue...
    )
)

REM 运行Python脚本
echo Start performing AKShare plate data updates...
python scripts/auto_update_akshare_board_data.py %*

REM 保持窗口打开以便查看结果（可选）
if %ERRORLEVEL% NEQ 0 (
    echo The script execution is complete!
    pause
) else (
    echo The script execution is complete!
)

exit /b %ERRORLEVEL%