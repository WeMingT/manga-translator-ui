@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion

echo.
echo ========================================
echo 漫画翻译器 - 一键安装程序
echo Manga Translator UI - Installer
echo ========================================
echo.
echo 本脚本将自动完成以下步骤:
echo [1] 下载/解压便携版 Python 3.12 (如需要)
echo [2] 下载便携版 Git (如需要)
echo [3] 从 GitHub 克隆代码
echo [4] 安装 Python 依赖
echo [5] 完成安装
echo.
pause

REM ===== 步骤1: 检查/下载/解压便携版Python =====
echo.
echo [1/5] 检查便携版 Python 3.12...
echo ========================================

REM 检查是否已经解压好
if exist "Python-3.12.12\python.exe" (
    set PYTHON=Python-3.12.12\python.exe
    set PYTHON_VERSION=3.12
    echo [OK] 找到便携版 Python 3.12
    Python-3.12.12\python.exe --version
    goto :check_git
)

echo [INFO] 未找到便携版 Python
echo.

REM 检查是否已下载压缩包
if exist "python-3.12.12-win64.7z" (
    echo [INFO] 找到已下载的压缩包
    goto :extract_python
)

echo 需要下载便携版 Python 3.12 (约25MB)
echo.
echo 请选择下载源:
echo [1] GitHub 官方
echo [2] gh-proxy.com 镜像 (国内推荐)
echo.
set /p python_source="请选择 (1/2, 默认2): "

set PYTHON_VERSION_FULL=3.12.12
set PYTHON_URL_PATH=https://github.com/hgmzhn/manga-translator-ui/releases/download/v1.8.2/python-3.12.12-win64.7z

if "%python_source%"=="1" (
    set PYTHON_URL=%PYTHON_URL_PATH%
    echo 使用: GitHub 官方源
) else (
    set PYTHON_URL=https://gh-proxy.com/%PYTHON_URL_PATH%
    echo 使用: gh-proxy.com 镜像
)

echo.
echo 下载中... (约25MB, 可能需要几分钟)
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Write-Host '正在下载...'; try { Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile 'python-3.12.12-win64.7z' -UseBasicParsing; Write-Host '[OK] 下载完成'; exit 0 } catch { Write-Host '[ERROR] 下载失败: $_'; exit 1 }}"

if %ERRORLEVEL% neq 0 (
    echo.
    echo 下载失败,请检查网络连接后重试
    pause
    exit /b 1
)

:extract_python
echo.
echo 正在解压 Python 3.12...
echo 需要使用 7-Zip 解压, 正在检查...

REM 检查系统是否已安装7z
where 7z >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo [OK] 找到 7-Zip
    7z x python-3.12.12-win64.7z -y
    move python-3.12.12-portable Python-3.12.12 >nul 2>&1
    goto :check_python_extracted
)

REM 检查常见安装路径
if exist "C:\Program Files\7-Zip\7z.exe" (
    echo [OK] 找到 7-Zip
    "C:\Program Files\7-Zip\7z.exe" x python-3.12.12-win64.7z -y
    move python-3.12.12-portable Python-3.12.12 >nul 2>&1
    goto :check_python_extracted
)

REM 检查是否已有便携版7z
if exist "Portable7z\7zr.exe" (
    echo [OK] 找到便携版 7-Zip
    Portable7z\7zr.exe x python-3.12.12-win64.7z -y
    move python-3.12.12-portable Python-3.12.12 >nul 2>&1
    goto :check_python_extracted
)

REM 下载便携版7-Zip
echo [INFO] 未找到 7-Zip
echo 正在下载便携版 7-Zip (约1MB)...
echo.

if not exist "tmp" mkdir tmp

REM 下载7-Zip Extra便携版（包含7zr.exe）
set SEVENZIP_URL=https://www.7-zip.org/a/7zr.exe
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Write-Host '正在下载 7-Zip...'; try { Invoke-WebRequest -Uri '%SEVENZIP_URL%' -OutFile 'tmp\7zr.exe' -UseBasicParsing; Write-Host '[OK] 下载完成'; exit 0 } catch { Write-Host '[ERROR] 下载失败: $_'; exit 1 }}"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] 7-Zip 下载失败
    echo.
    echo 请选择:
    echo [1] 安装 7-Zip 后重试
    echo [2] 手动解压 python-3.12.12-win64.7z 到 Python-3.12.12 文件夹
    echo [3] 退出
    echo.
    set /p extract_choice="请选择 (1/2/3): "
    
    if "!extract_choice!"=="1" (
        start https://www.7-zip.org/download.html
        pause
        exit /b 1
    ) else if "!extract_choice!"=="2" (
        echo 请手动解压后重新运行本脚本
        pause
        exit /b 1
    )
    exit /b 1
)

REM 创建便携版7z目录
if not exist "Portable7z" mkdir Portable7z
move /y tmp\7zr.exe Portable7z\7zr.exe >nul

echo [OK] 7-Zip 准备完成
echo 正在解压 Python...
Portable7z\7zr.exe x python-3.12.12-win64.7z -y
move python-3.12.12-portable Python-3.12.12 >nul 2>&1

:check_python_extracted
if not exist "Python-3.12.12\python.exe" (
    echo [ERROR] 解压后未找到 python.exe
    pause
    exit /b 1
)

echo [OK] Python 3.12 解压完成

REM 清理压缩包
if exist "python-3.12.12-win64.7z" (
    echo 正在清理安装包...
    del /f /q "python-3.12.12-win64.7z" >nul 2>&1
    echo [OK] 已删除 python-3.12.12-win64.7z
)

set PYTHON=Python-3.12.12\python.exe
set PYTHON_VERSION=3.12
Python-3.12.12\python.exe --version

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
echo [2] gh-proxy.com 镜像 (国内推荐)
echo.
set /p git_source="请选择 (1/2, 默认2): "

set GIT_VERSION=2.43.0
set GIT_ARCH=64-bit

if "%git_source%"=="1" (
    set GIT_URL=https://github.com/git-for-windows/git/releases/download/v%GIT_VERSION%.windows.1/PortableGit-%GIT_VERSION%-%GIT_ARCH%.7z.exe
    echo 使用: GitHub 官方源
) else (
    set GIT_URL=https://gh-proxy.com/https://github.com/git-for-windows/git/releases/download/v%GIT_VERSION%.windows.1/PortableGit-%GIT_VERSION%-%GIT_ARCH%.7z.exe
    echo 使用: gh-proxy.com 镜像
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
set "PATH=%CD%\PortableGit\cmd;%PATH%"
echo [OK] Git 安装完成
PortableGit\cmd\git.exe --version

REM ===== 步骤3: 克隆/更新仓库 =====
:clone_repo
echo.
echo [3/5] 检查代码仓库...
echo ========================================
echo.

REM 检查是否从压缩包解压（有代码但没有.git）
if not exist ".git" (
    if exist "manga_translator" if exist "desktop_qt_ui" if exist "packaging\VERSION" (
        echo [INFO] 检测到从压缩包解压的代码文件
        echo.
        echo 请选择:
        echo [1] 跳过Git配置,直接安装依赖（无法使用步骤4更新）
        echo [2] 初始化Git仓库并关联远程（可使用步骤4更新）
        echo [3] 退出
        echo.
        set /p zip_choice="请选择 (1/2/3, 默认2): "
        
        if "!zip_choice!"=="3" (
            exit /b 0
        ) else if "!zip_choice!"=="1" (
            echo [OK] 跳过Git配置,直接使用现有代码
            echo.
            goto :create_venv
        ) else (
            echo [INFO] 正在初始化Git仓库...
            git init
            if !ERRORLEVEL! neq 0 (
                echo [ERROR] Git初始化失败
                pause
                exit /b 1
            )
            REM 获取目标仓库地址
            call :get_repo_url
            echo.
            echo 正在添加远程仓库...
            git remote add origin !REPO_URL!
            if !ERRORLEVEL! neq 0 (
                echo [ERROR] 添加远程仓库失败
                pause
                exit /b 1
            )
            echo.
            echo 正在获取远程分支...
            git fetch origin
            if !ERRORLEVEL! neq 0 (
                echo [WARNING] 获取远程分支失败，可能是网络问题
                echo [INFO] 将跳过Git配置，直接使用现有代码
                echo.
                goto :create_venv
            )
            echo.
            echo [OK] Git仓库初始化完成
            echo [INFO] 可以使用步骤4进行更新
            echo.
            goto :create_venv
        )
    )
)

REM 先获取目标仓库地址
call :get_repo_url

REM 检查是否已存在代码仓库
if exist ".git" (
    echo [INFO] 检测到现有Git仓库
    
    REM 获取当前仓库地址
    for /f "delims=" %%i in ('%GIT% config --get remote.origin.url 2^>nul') do set CURRENT_REPO=%%i
    
    if defined CURRENT_REPO (
        echo 当前仓库: !CURRENT_REPO!
        echo 目标仓库: !REPO_URL!
        echo.
        
        REM 标准化仓库地址进行比较（去除.git后缀和所有镜像前缀）
        set CURRENT_CLEAN=!CURRENT_REPO:.git=!
        set TARGET_CLEAN=!REPO_URL:.git=!
        
        REM 移除常见镜像前缀，统一标准化为 github.com 地址
        set CURRENT_CLEAN=!CURRENT_CLEAN:https://gh-proxy.com/https://github.com/=https://github.com/!
        set CURRENT_CLEAN=!CURRENT_CLEAN:https://ghproxy.com/https://github.com/=https://github.com/!
        set CURRENT_CLEAN=!CURRENT_CLEAN:https://mirror.ghproxy.com/https://github.com/=https://github.com/!
        set CURRENT_CLEAN=!CURRENT_CLEAN:https://ghfast.top/https://github.com/=https://github.com/!
        set CURRENT_CLEAN=!CURRENT_CLEAN:https://gitproxy.click/https://github.com/=https://github.com/!
        
        set TARGET_CLEAN=!TARGET_CLEAN:https://gh-proxy.com/https://github.com/=https://github.com/!
        set TARGET_CLEAN=!TARGET_CLEAN:https://ghproxy.com/https://github.com/=https://github.com/!
        set TARGET_CLEAN=!TARGET_CLEAN:https://mirror.ghproxy.com/https://github.com/=https://github.com/!
        set TARGET_CLEAN=!TARGET_CLEAN:https://ghfast.top/https://github.com/=https://github.com/!
        set TARGET_CLEAN=!TARGET_CLEAN:https://gitproxy.click/https://github.com/=https://github.com/!
        
        if "!CURRENT_CLEAN!"=="!TARGET_CLEAN!" (
            echo [OK] 仓库地址匹配,正在强制同步到最新版本...
            echo.
            
            echo 获取远程更新...
            %GIT% fetch origin
            if !ERRORLEVEL! neq 0 (
                echo [WARNING] 获取更新失败,可能是网络问题
            ) else (
                echo 强制同步到远程主分支...
                %GIT% reset --hard origin/main
                if !ERRORLEVEL! == 0 (
                    echo [OK] 代码已更新到最新版本
                    echo.
                    goto :create_venv
                ) else (
                    echo [WARNING] 同步失败,尝试使用 main 分支...
                    %GIT% checkout -f main
                    %GIT% reset --hard origin/main
                    if !ERRORLEVEL! == 0 (
                        echo [OK] 代码已更新到最新版本
                        echo.
                        goto :create_venv
                    )
                )
            )
            
            echo [WARNING] 自动更新失败,将删除并重新克隆
            echo.
        ) else (
            echo [警告] 仓库地址不匹配
            echo.
            echo 请选择:
            echo [1] 删除现有仓库并克隆新仓库
            echo [2] 保留现有仓库,跳过克隆
            echo [3] 退出安装
            echo.
            set /p mismatch_choice="请选择 (1/2/3): "
            
            if "!mismatch_choice!"=="2" (
                echo [INFO] 保留现有仓库
                goto :create_venv
            ) else if "!mismatch_choice!"=="3" (
                exit /b 0
            )
            
            echo 正在删除现有仓库...
        )
    ) else (
        echo [WARNING] 无法读取仓库信息,将重新克隆
    )
    
    REM 删除现有文件和目录(保留venv、PortableGit、Python-3.12.12、Portable7z)
    echo 正在清理旧文件...
    
    REM 删除目录(保留venv、PortableGit、Python-3.12.12、Portable7z)
    for /d %%d in (*) do (
        if /i not "%%d"=="venv" if /i not "%%d"=="PortableGit" if /i not "%%d"=="Python-3.12.12" if /i not "%%d"=="Portable7z" (
            echo 删除目录: %%d
            rmdir /s /q "%%d" 2>nul
        )
    )
    
    REM 删除文件(保留当前运行的脚本)
    for %%f in (*) do (
        if /i not "%%~nxf"=="步骤1-首次安装.bat" (
            echo 删除文件: %%~nxf
            del /f /q "%%f" 2>nul
        )
    )
    
    REM 删除隐藏的.git目录
    if exist ".git" (
        echo 删除 .git 目录...
        rmdir /s /q ".git" 2>nul
        if exist ".git" (
            echo [ERROR] 无法删除 .git 目录,可能被占用
            echo 请关闭所有相关程序后重试
            pause
            exit /b 1
        )
    )
    
    echo [OK] 已清理旧数据
    echo.
)

echo 仓库地址: !REPO_URL!
echo 安装目录: %CD%
echo.
goto :do_clone

:get_repo_url
echo 请选择克隆源:
echo [1] GitHub 官方 (国外推荐)
echo [2] gh-proxy.com 镜像 (国内推荐)
echo [3] 手动输入仓库地址
echo.
set /p repo_choice="请选择 (1/2/3, 默认2): "

if "%repo_choice%"=="1" (
    set REPO_URL=https://github.com/hgmzhn/manga-translator-ui.git
    echo 使用: GitHub官方
) else if "%repo_choice%"=="3" (
    set /p REPO_URL="请输入仓库地址: "
    echo 使用: 自定义地址
) else (
    set REPO_URL=https://gh-proxy.com/https://github.com/hgmzhn/manga-translator-ui.git
    echo 使用: gh-proxy.com镜像
)
echo.
goto :eof

:do_clone

REM 使用临时目录克隆
set TEMP_DIR=manga_translator_temp_%RANDOM%
echo 正在克隆代码到临时目录... (可能需要几分钟)
echo.
%GIT% clone !REPO_URL! %TEMP_DIR%

echo.
echo [DEBUG] 检查克隆结果...
echo [DEBUG] 临时目录: %TEMP_DIR%
echo [DEBUG] 完整路径: %CD%\%TEMP_DIR%
if exist "%TEMP_DIR%" (
    echo [DEBUG] 临时目录存在
    if exist "%TEMP_DIR%\.git" (
        echo [DEBUG] .git 目录存在 - 克隆成功!
        goto :copy_files
    ) else (
        echo [DEBUG] .git 目录不存在 - 克隆失败!
    )
) else (
    echo [DEBUG] 临时目录不存在 - 克隆失败!
)

REM 如果到这里说明克隆失败
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

:copy_files

echo.
echo [DEBUG] 开始复制文件...
echo [DEBUG] 临时目录: %TEMP_DIR%
echo [DEBUG] 当前目录: %CD%
echo.

echo 正在复制目录...
for /d %%i in ("%TEMP_DIR%\*") do (
    if /i not "%%~nxi"=="PortableGit" (
        echo [DEBUG] 复制目录: %%~nxi
        xcopy "%%i" "%CD%\%%~nxi\" /E /H /Y /I /Q
        if !ERRORLEVEL! neq 0 echo [ERROR] 复制目录失败: %%~nxi (错误码: !ERRORLEVEL!)
    )
)

echo.
echo 正在复制文件...
for %%i in ("%TEMP_DIR%\*") do (
    if /i not "%%~nxi"=="步骤1-首次安装.bat" (
        echo [DEBUG] 复制文件: %%~nxi
        copy /Y "%%i" "%CD%\"
        if !ERRORLEVEL! neq 0 echo [ERROR] 复制文件失败: %%~nxi (错误码: !ERRORLEVEL!)
    )
)

echo.
echo 正在复制隐藏文件...
if exist "%TEMP_DIR%\.git\" (
    echo [DEBUG] 复制 .git 目录...
    xcopy "%TEMP_DIR%\.git" ".git\" /E /H /Y /I /Q
    if !ERRORLEVEL! neq 0 echo [ERROR] 复制.git失败 (错误码: !ERRORLEVEL!)
) else (
    echo [DEBUG] .git 目录不存在
)

if exist "%TEMP_DIR%\.gitignore" (
    echo [DEBUG] 复制 .gitignore 文件...
    copy /Y "%TEMP_DIR%\.gitignore" .
    if !ERRORLEVEL! neq 0 echo [ERROR] 复制.gitignore失败 (错误码: !ERRORLEVEL!)
) else (
    echo [DEBUG] .gitignore 文件不存在
)

echo.
echo [DEBUG] 复制完成，准备清理临时目录...
echo 正在清理临时目录...
rmdir /s /q "%TEMP_DIR%"
if !ERRORLEVEL! neq 0 (
    echo [ERROR] 清理临时目录失败 (错误码: !ERRORLEVEL!)
) else (
    echo [DEBUG] 临时目录已清理
)

echo.
echo [OK] 代码克隆完成

:create_venv

REM ===== 步骤4: 创建虚拟环境并安装依赖 =====
echo.
echo [4/5] 创建虚拟环境并安装依赖...
echo ========================================
echo.

REM 检测虚拟环境有效性
set VENV_VALID=0
if exist "venv\Scripts\python.exe" (
    echo 检测到现有虚拟环境,正在验证...
    venv\Scripts\python.exe -c "import sys; sys.exit(0)" >nul 2>&1
    if !ERRORLEVEL! == 0 (
        set VENV_VALID=1
        echo [OK] 虚拟环境有效
    ) else (
        echo [警告] 虚拟环境已损坏或失效
    )
)

REM 创建或重建虚拟环境
if !VENV_VALID! == 0 (
    if exist "venv" (
        echo 正在删除无效的虚拟环境...
        rmdir /s /q "venv" 2>nul
        if exist "venv" (
            echo [ERROR] 无法删除旧的虚拟环境
            echo 请手动删除 venv 文件夹后重试
            pause
            exit /b 1
        )
    )
    
    echo 正在创建虚拟环境...
    Python-3.12.12\python.exe -m venv venv
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

echo 正在安装基础依赖...
python -m pip install packaging setuptools wheel >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARNING] 基础依赖安装失败,继续尝试...
)

echo 正在检测 GPU 支持...
echo.

REM 调用项目的 launch.py 进行依赖安装
python packaging\launch.py --install-deps-only

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] 依赖安装失败
    echo.
    echo 你可以稍后手动运行:
    echo   步骤4-更新维护.bat
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
echo   或 步骤3-检查更新并启动.bat (自动检查更新)
echo.
echo 定期更新:
echo   双击 步骤4-更新维护.bat
echo.
pause

REM 询问是否清理pip缓存
echo.
echo ========================================
echo 磁盘空间优化
echo ========================================
echo.
echo pip 缓存文件可能占用较大空间
echo 清理缓存不会影响已安装的包
echo.
set /p clean_cache="是否清理 pip 缓存? (y/n, 默认n): "
if /i "%clean_cache%"=="y" (
    echo.
    echo 正在清理 pip 缓存...
    call venv\Scripts\activate.bat
    python -m pip cache purge >nul 2>&1
    echo [OK] 缓存已清理
) else (
    echo [INFO] 跳过缓存清理
)

REM 询问是否立即运行
echo.
set /p run_now="是否立即运行? (y/n): "
if /i "%run_now%"=="y" (
    echo.
    echo 正在启动...
    start 步骤2-启动Qt界面.bat
)

echo.
echo 安装流程已结束
pause
