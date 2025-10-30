@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion

REM 激活虚拟环境
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] 虚拟环境不存在,请先运行 步骤1-首次安装.bat
    pause
    exit /b 1
)

REM 检查是否有便携版 Git
if exist "PortableGit\cmd\git.exe" (
    set "PATH=%CD%\PortableGit\cmd;%PATH%"
)

REM 切换到项目根目录(确保Python能正确找到模块)
cd /d "%~dp0"

REM 直接启动 Qt 界面
python "%CD%\desktop_qt_ui\main.py"
pause
