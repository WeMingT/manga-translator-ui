# -*- coding: utf-8 -*-
import os
import sys

# 确保当前目录正确
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Script 1
script1 = r"""@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion

echo.
echo ========================================
echo 漫画翻译器 - 一键安装程序
echo Manga Translator UI - Installer
echo ========================================
echo.
echo 本脚本将自动完成以下步骤:
echo [1] 检查 Python 3.12+
echo [2] 下载便携版 Git (如需要)
echo [3] 从 GitHub 克隆代码
echo [4] 安装 Python 依赖
echo [5] 完成安装
echo.
pause

REM ===== 步骤1: 检查Python =====
echo.
echo [1/5] 检查 Python 3.12...
echo ========================================

py -3.12 --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    set PYTHON=py -3.12
    echo [OK] 找到 Python 3.12
    goto :check_git
)

python --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    python --version | findstr "3\.12\." >nul
    if %ERRORLEVEL% == 0 (
        set PYTHON=python
        echo [OK] 找到 Python 3.12
        goto :check_git
    )
)

echo.
echo [ERROR] 错误: 未找到 Python 3.12
echo.
echo 请先安装 Python 3.12 版本:
echo https://www.python.org/downloads/
echo.
echo 安装时请勾选 "Add Python to PATH"
echo.
pause
exit /b 1

REM ===== 步骤2: 检查/下载Git =====
:check_git
echo.
echo [2/5] 检查 Git...
echo ========================================

git --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    set GIT=git
    echo [OK] 找到系统Git
    goto :clone_repo
)

echo [INFO] 未找到 Git
echo.
echo Git是代码拉取必需的,请选择:
echo [1] 下载便携版 Git (推荐, 约50MB)
echo [2] 退出,手动安装 Git
echo.
set /p git_choice="请选择 (1/2): "

if "%git_choice%"=="2" (
    echo.
    echo 下载地址: https://git-scm.com/downloads
    pause
    exit /b 0
)

if not "%git_choice%"=="1" (
    echo 无效选项
    goto :check_git
)

REM 下载Git
echo.
echo 正在下载 Git 便携版...
echo.
echo 请选择下载源:
echo [1] GitHub 官方
echo [2] 淘宝镜像 (国内快)
echo [3] 腾讯云镜像 (国内快)
echo.
set /p source="请选择 (1/2/3, 默认2): "

set GIT_VERSION=2.43.0
set GIT_ARCH=64-bit

if "%source%"=="1" (
    set GIT_URL=https://github.com/git-for-windows/git/releases/download/v%GIT_VERSION%.windows.1/PortableGit-%GIT_VERSION%-%GIT_ARCH%.7z.exe
    echo 使用: GitHub
) else if "%source%"=="3" (
    set GIT_URL=https://mirrors.cloud.tencent.com/github-release/git-for-windows/git/LatestRelease/PortableGit-%GIT_VERSION%-%GIT_ARCH%.7z.exe
    echo 使用: 腾讯云
) else (
    set GIT_URL=https://registry.npmmirror.com/-/binary/git-for-windows/v%GIT_VERSION%.windows.1/PortableGit-%GIT_VERSION%-%GIT_ARCH%.7z.exe
    echo 使用: 淘宝镜像
)

echo.
echo 下载中... (约50MB, 可能需要几分钟)
if not exist "tmp" mkdir tmp
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Write-Host '正在下载...'; try { Invoke-WebRequest -Uri '%GIT_URL%' -OutFile 'tmp\PortableGit.7z.exe' -UseBasicParsing; Write-Host '[OK] 下载完成'; exit 0 } catch { Write-Host '[ERROR] 下载失败: $_'; exit 1 }}"

if %ERRORLEVEL% neq 0 (
    echo.
    echo 下载失败,请检查网络连接后重试
    pause
    exit /b 1
)

echo.
echo 正在解压 Git...
tmp\PortableGit.7z.exe -o"PortableGit" -y >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo 解压失败
    pause
    exit /b 1
)

del tmp\PortableGit.7z.exe >nul 2>&1
set GIT=PortableGit\cmd\git.exe
set PATH=%~dp0PortableGit\cmd;%PATH%
echo [OK] Git 安装完成
PortableGit\cmd\git.exe --version

REM ===== 步骤3: 克隆仓库 =====
:clone_repo
echo.
echo [3/5] 克隆代码仓库...
echo ========================================
echo.

REM 检查是否已存在代码仓库
if exist ".git" (
    echo [警告] 当前目录已包含Git仓库!
    echo.
    echo 首次安装应在新目录中运行,或者:
    echo 1. 如果要更新代码,请使用 "步骤3-更新维护.bat"
    echo 2. 如果要重新安装,请先删除 .git 目录
    echo.
    pause
    exit /b 1
)

echo 请选择克隆源:
echo [1] GitHub 官方
echo [2] GHProxy 镜像 (国内快)
echo [3] 手动输入仓库地址
echo.
set /p repo_choice="请选择 (1/2/3, 默认1): "

if "%repo_choice%"=="2" (
    set REPO_URL=https://mirror.ghproxy.com/https://github.com/hgmzhn/manga-translator-ui.git
    echo 使用: GHProxy镜像
) else if "%repo_choice%"=="3" (
    set /p REPO_URL="请输入仓库地址: "
    echo 使用: 自定义地址
) else (
    set REPO_URL=https://github.com/hgmzhn/manga-translator-ui.git
    echo 使用: GitHub官方
)

echo.
echo 仓库地址: %REPO_URL%
echo 安装目录: %CD%
echo.

REM 使用临时目录克隆
set TEMP_DIR=manga_translator_temp_%RANDOM%
echo 正在克隆代码到临时目录... (可能需要几分钟)
echo.
%GIT% clone %REPO_URL% %TEMP_DIR%

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] 克隆失败
    echo.
    echo 可能原因:
    echo 1. 网络连接问题
    echo 2. 仓库地址错误
    echo 3. GitHub访问受限 (请选择GHProxy镜像重试)
    echo.
    if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
    set /p retry="是否重试? (y/n): "
    if /i "!retry!"=="y" goto :clone_repo
    pause
    exit /b 1
)

echo.
echo 正在复制文件到当前目录...
REM 复制所有文件和文件夹(除了bat脚本自身和PortableGit)
xcopy "%TEMP_DIR%\*" . /E /H /Y /EXCLUDE:bat_exclude.txt >nul 2>&1
if not %ERRORLEVEL%==0 (
    REM 如果exclude文件不存在,直接复制所有
    for /d %%i in ("%TEMP_DIR%\*") do (
        if /i not "%%~nxi"=="PortableGit" xcopy "%%i" "%%~nxi\" /E /H /Y >nul
    )
    for %%i in ("%TEMP_DIR%\*") do (
        if /i not "%%~nxi"=="步骤1-首次安装.bat" (
            if /i not "%%~nxi"=="步骤2-启动Qt界面.bat" (
                if /i not "%%~nxi"=="步骤3-更新维护.bat" (
                    copy "%%i" . >nul
                )
            )
        )
    )
)

echo 正在清理临时目录...
rmdir /s /q "%TEMP_DIR%"

echo.
echo [OK] 代码克隆完成

REM ===== 步骤4: 创建虚拟环境并安装依赖 =====
echo.
echo [4/5] 创建虚拟环境并安装依赖...
echo ========================================
echo.

REM 创建虚拟环境
if exist "venv" (
    echo 虚拟环境已存在
) else (
    echo 正在创建虚拟环境...
    %PYTHON% -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo [OK] 虚拟环境创建完成
)

echo.
echo 正在激活虚拟环境...
call venv\Scripts\activate.bat

echo 正在升级 pip...
python -m pip install --upgrade pip >nul 2>&1

echo 正在检测 GPU 支持...
echo.

REM 调用项目的 launch.py 进行依赖安装
python launch.py --frozen

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] 依赖安装失败
    echo.
    echo 你可以稍后手动运行:
    echo   步骤3-更新维护.bat
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] 依赖安装完成

REM ===== 步骤5: 完成 =====
echo.
echo [5/5] 安装完成!
echo ========================================
echo.
echo [OK] 所有步骤已完成!
echo.
echo 安装位置: %CD%
echo.
echo 下一步操作:
echo   双击 步骤2-启动Qt界面.bat (Qt版本)
echo.
echo 定期更新:
echo   双击 步骤3-更新维护.bat
echo.
pause

REM 询问是否立即运行
set /p run_now="是否立即运行? (y/n): "
if /i "%run_now%"=="y" (
    echo.
    echo 正在启动...
    start 步骤2-启动Qt界面.bat
)

echo.
echo 安装流程已结束
pause
"""

# Script 2
script2 = r"""@echo off
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
    set PATH=%~dp0PortableGit\cmd;%PATH%
)

REM 启动 Qt 版本
python launch.py --ui qt --frozen
pause
"""

# Script 3
script3 = r"""@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion

echo.
echo ========================================
echo 漫画翻译器 - 更新维护工具
echo Manga Translator UI - Update Tool
echo ========================================
echo.

REM 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] 虚拟环境不存在
    echo 请先运行 步骤1-首次安装.bat
    pause
    exit /b 1
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 检查是否有便携版 Git
if exist "PortableGit\cmd\git.exe" (
    set GIT=PortableGit\cmd\git.exe
    set PATH=%~dp0PortableGit\cmd;%PATH%
) else (
    git --version >nul 2>&1
    if %ERRORLEVEL% == 0 (
        set GIT=git
    ) else (
        echo [ERROR] 未找到 Git
        echo 请先安装 Git 或运行 步骤1-首次安装.bat
        pause
        exit /b 1
    )
)

REM 菜单
:menu
echo.
echo 请选择操作:
echo [1] 更新代码
echo [2] 更新/安装依赖
echo [3] 完整更新 (代码+依赖)
echo [4] 退出
echo.
set /p choice="请选择 (1/2/3/4): "

if "%choice%"=="1" goto update_code
if "%choice%"=="2" goto update_deps
if "%choice%"=="3" goto full_update
if "%choice%"=="4" goto end

echo 无效选项
goto menu

:update_code
echo.
echo ========================================
echo 更新代码
echo ========================================
echo.

echo 检查本地修改...
%GIT% diff --quiet
if %ERRORLEVEL% neq 0 (
    echo.
    echo [警告] 检测到本地文件已修改
    echo git pull 会覆盖本地修改的文件
    echo 新添加的文件不会被删除
    echo.
    set /p continue="是否继续更新? (y/n): "
    if /i not "!continue!"=="y" (
        echo 取消更新
        goto menu
    )
)

echo 正在拉取最新代码...
%GIT% pull

if %ERRORLEVEL% == 0 (
    echo [OK] 代码更新完成
) else (
    echo [ERROR] 代码更新失败
)
pause
goto menu

:update_deps
echo.
echo ========================================
echo 更新/安装依赖
echo ========================================
echo.

python launch.py --frozen

if %ERRORLEVEL% == 0 (
    echo [OK] 依赖更新完成
) else (
    echo [ERROR] 依赖更新失败
)
pause
goto menu

:full_update
echo.
echo ========================================
echo 完整更新 (代码+依赖)
echo ========================================
echo.

echo [1/2] 更新代码...
%GIT% diff --quiet
if %ERRORLEVEL% neq 0 (
    echo.
    echo [警告] 检测到本地文件已修改
    echo git pull 会覆盖本地修改的文件
    echo 新添加的文件不会被删除
    echo.
    set /p continue="是否继续更新? (y/n): "
    if /i not "!continue!"=="y" (
        echo 取消更新
        goto menu
    )
)

%GIT% pull
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 代码更新失败
    pause
    goto menu
)
echo [OK] 代码更新完成

echo.
echo [2/2] 更新依赖...
python launch.py --frozen

if %ERRORLEVEL% == 0 (
    echo.
    echo [OK] 完整更新完成
) else (
    echo [ERROR] 依赖更新失败
)
pause
goto menu

:end
echo.
echo 退出更新工具
pause
"""

# Write files with gbk encoding (Windows ANSI Chinese)
with open("步骤1-首次安装.bat", "w", encoding="gbk", errors="ignore") as f:
    f.write(script1)
print("Created: 步骤1-首次安装.bat")

with open("步骤2-启动Qt界面.bat", "w", encoding="gbk", errors="ignore") as f:
    f.write(script2)
print("Created: 步骤2-启动Qt界面.bat")

with open("步骤3-更新维护.bat", "w", encoding="gbk", errors="ignore") as f:
    f.write(script3)
print("Created: 步骤3-更新维护.bat")

print("\nAll scripts generated successfully with GBK encoding!")

