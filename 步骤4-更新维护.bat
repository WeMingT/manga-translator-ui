@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion

REM 设置 PYTHONUTF8=1 避免conda编码错误
set "PYTHONUTF8=1"

REM 修复管理员模式下%CD%变成system32的问题
cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM 检查conda环境
set CONDA_ENV_NAME=manga-env
set MINICONDA_ROOT=%SCRIPT_DIR%\Miniconda3

REM 检测路径是否包含中文
powershell -Command "$path = '%SCRIPT_DIR%'; if ($path -match '[^\x00-\x7F]') { exit 1 } else { exit 0 }" >nul 2>&1
if %ERRORLEVEL% neq 0 set MINICONDA_ROOT=%~d0\Miniconda3

REM 检查系统conda
where conda >nul 2>&1
if %ERRORLEVEL% neq 0 goto :check_local_conda_s4

REM 获取系统conda路径
if defined CONDA_EXE for %%p in ("%CONDA_EXE%\..\..") do set "MINICONDA_ROOT=%%~fp"
goto :activate_env_s4

:check_local_conda_s4
if exist "%SCRIPT_DIR%\Miniconda3\Scripts\conda.exe" (
    set MINICONDA_ROOT=%SCRIPT_DIR%\Miniconda3
    call "%MINICONDA_ROOT%\Scripts\activate.bat"
    goto :activate_env_s4
)
if exist "%~d0\Miniconda3\Scripts\conda.exe" (
    set MINICONDA_ROOT=%~d0\Miniconda3
    call "%MINICONDA_ROOT%\Scripts\activate.bat"
    goto :activate_env_s4
)
echo [ERROR] 未检测到 Conda
echo 请先运行 步骤1-首次安装.bat 安装 Miniconda
pause
exit /b 1

:activate_env_s4
REM 激活conda环境
if exist "%MINICONDA_ROOT%\Scripts\activate.bat" call "%MINICONDA_ROOT%\Scripts\activate.bat"
call conda activate "%CONDA_ENV_NAME%" 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 无法激活环境 %CONDA_ENV_NAME%
    echo 请先运行 步骤1-首次安装.bat 创建环境
    pause
    exit /b 1
)

REM 添加便携版Git到PATH
if exist "%SCRIPT_DIR%\PortableGit\cmd\git.exe" set "PATH=%SCRIPT_DIR%\PortableGit\cmd;%PATH%"

REM 调用Python维护菜单
python packaging\launch.py --maintenance
pause
