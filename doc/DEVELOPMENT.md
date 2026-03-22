# 开发者指南

本文档面向需要修改源码、调试流程、扩展功能或参与打包发布的开发者。下面只列 Git 已跟踪、会随仓库一起维护的目录和文件，不展开本地缓存、运行产物或未提交目录。

## 1. 开发前提

### Python 与环境

- 当前仓库以 **Python 3.12** 为基线。
- `packaging/launch.py` 和 GitHub Actions 也都按 Python 3.12 运行。
- 当前默认安装路径仍是 Conda / Miniforge + `requirements_*.txt`。
- 手动开发时也可以使用 `venv`、Conda 或项目安装脚本创建环境，不强制要求环境名必须叫 `manga-env`。
- 如果你想测试 uv，仓库根目录也提供了 `pyproject.toml` / `uv.lock`。

### 依赖安装

当前仓库的**默认依赖安装方式**仍然是 `requirements_*.txt`。`uv` 目前只是一个**可选的开发工作流**，用于测试标准化依赖定义，不替代现有安装脚本、CI 和 Docker。

#### 默认方式：沿用 requirements

按你的运行目标只安装一套依赖即可：

```bash
# CPU
pip install -r requirements_cpu.txt

# NVIDIA GPU（CUDA 12.x）
pip install -r requirements_gpu.txt

# AMD GPU（实验性）
pip install -r requirements_amd.txt

# Apple Silicon / Metal
pip install -r requirements_metal.txt
```

如果你要做 PyInstaller 打包，还需要：

```bash
pip install pyinstaller
```

#### 可选方式：使用 uv

仓库根目录已提供 `pyproject.toml` / `uv.lock`，供开发者测试 uv 依赖管理流程。

安装 uv：

**Windows PowerShell**：
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux / macOS**：
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

创建虚拟环境：

```bash
uv venv --python 3.12
```

激活环境：

**Windows PowerShell**：
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows CMD**：
```cmd
.\.venv\Scripts\activate.bat
```

**Linux / macOS**：
```bash
source .venv/bin/activate
```

同步依赖：

```bash
# CPU
uv sync --extra cpu

# NVIDIA GPU（CUDA 12.x）
uv sync --extra gpu

# AMD GPU（实验性，仅同步非 torch / 非 ROCm 特殊安装部分）
uv sync --extra amd

# Apple Silicon / Metal
uv sync --extra metal
```

如果你要做打包相关工作，还可以：

```bash
uv sync --extra build
```

> 注意：AMD 的 ROCm PyTorch 当前仍依赖现有安装脚本 / `packaging/launch.py` 的特殊处理，`uv sync --extra amd` 目前主要覆盖非 torch 依赖。

## 2. 仓库结构

实际开发时优先关注下面这些已纳入版本控制的区域。

### 核心源码区

```text
manga-translator-ui-package/
├─ desktop_qt_ui/              # Qt 桌面应用
│  ├─ main.py                  # 桌面端入口
│  ├─ main_window.py           # 主窗口与主生命周期
│  ├─ services/                # 服务容器、配置、翻译、OCR、日志等
│  ├─ editor/                  # 可视化编辑器核心
│  ├─ widgets/                 # 通用 UI 组件
│  ├─ main_view_parts/         # 主界面分区与布局生成
│  └─ locales/                 # 多语言文本与布局配置
├─ manga_translator/           # 核心翻译引擎与服务端
│  ├─ __main__.py              # CLI / web / ws / shared 统一入口
│  ├─ detection/               # 文本检测
│  ├─ ocr/                     # OCR 模型与适配
│  ├─ translators/             # 翻译器实现
│  ├─ inpainting/              # 修复与去字
│  ├─ rendering/               # 嵌字与排版
│  ├─ upscaling/               # 超分
│  ├─ colorization/            # 上色
│  ├─ utils/                   # 通用工具与中间格式
│  └─ server/                  # FastAPI 服务端、静态页面、管理后台
├─ packaging/                  # 启动脚本、更新脚本、PyInstaller、Docker
├─ examples/                   # 默认配置、模板、翻译器注册表
├─ .github/                    # CI/CD、Issue 模板
├─ doc/                        # 用户文档与 changelog
├─ fonts/                      # 默认字体资源
├─ dict/                       # Prompt、词典、模板资源
└─ README.md                   # 项目入口文档
```

## 3. 代码分层与入口

### 3.1 Qt 桌面端

桌面端主入口是：

```bash
python -m desktop_qt_ui.main
```

主路径大致是：

1. `desktop_qt_ui/main.py`
2. 初始化日志、资源路径、全局异常处理
3. 调用 `desktop_qt_ui.services.init_services(root_dir)`
4. 创建 `MainWindow`
5. 再由 `main_view.py`、`main_view_parts/`、`editor/` 组装主界面和编辑器

桌面端改动时通常按下面的落点找文件：

- 改设置读写：`desktop_qt_ui/services/config_service.py`、`desktop_qt_ui/core/config_models.py`
- 改主界面布局：`desktop_qt_ui/main_view.py`、`desktop_qt_ui/main_view_parts/`
- 改编辑器行为：`desktop_qt_ui/editor/`
- 改通用弹窗/控件：`desktop_qt_ui/widgets/`
- 改服务装配：`desktop_qt_ui/services/__init__.py`

### 3.2 核心引擎与命令行

统一入口是：

```bash
python -m manga_translator <mode>
```

已实现模式：

- `web`：启动 FastAPI 服务与 Web UI
- `local`：命令行本地翻译
- `ws`：WebSocket 模式
- `shared`：共享 API 实例模式

常用示例：

```bash
# Web 服务
python -m manga_translator web --host 127.0.0.1 --port 8000

# 本地翻译
python -m manga_translator local -i path/to/image.png -o path/to/output
```

核心处理链主要分散在 `manga_translator/` 下：

- `detection/`：文本区域检测
- `ocr/`：文字识别
- `translators/`：文本翻译
- `inpainting/`：清除原文与补全背景
- `rendering/`：译文排版回写
- `utils/textblock.py` 等：中间结构与序列化

### 3.3 服务端

服务端入口由 `manga_translator/__main__.py` 的 `web` 模式分发到 `manga_translator/server/main.py`。

服务端目录建议这样理解：

- `server/routes/`：HTTP 路由层
- `server/core/`：账户、权限、配额、清理任务、配置管理等服务逻辑
- `server/repositories/`：JSON/文件存储封装
- `server/models/`：Pydantic 或数据模型
- `server/static/`：前端静态页面与管理后台资源
- `server/data/`：服务端运行时数据文件

## 4. 配置与资源打包约定

这个项目同时支持开发环境和 PyInstaller 打包环境。改资源路径相关逻辑前，重点确认哪些已跟踪资源需要被一起打进发布包。

### 开发环境常用的已跟踪资源

- 默认配置模板：`examples/config-example.json`
- 模型下载源策略：`examples/model_sources.toml`
- 环境变量示例：`.env.example`
- 翻译器注册表：`examples/config/translators.json`
- 资源目录：`fonts/`、`dict/`、`doc/`、`desktop_qt_ui/locales/`

### 打包时需要关注的已跟踪资源

- `examples/`
- `fonts/`
- `dict/`
- `doc/`
- `desktop_qt_ui/locales/`

如果你新增了资源目录、模板文件或配置文件，需要同时检查：

1. 开发态是否按项目根目录能加载到。
2. PyInstaller spec 和 GitHub workflow 是否把它一起打进发布包。

## 5. 配置文件约定

开发态与打包态都遵循“主配置 / 环境变量 / 独立资源文件分离”的原则：

- `examples/config-example.json`
  - 主配置模板
  - 用于翻译流程主配置与 UI 默认配置
- `.env.example`
  - 环境变量示例
  - 只放路径、API 地址、密钥等入口型变量
- `examples/model_sources.toml`
  - 模型下载源策略配置
  - 不并入 `config.json` / `AppSettings`
  - 不把策略内容写进 `.env`

### 模型下载源配置

模型下载统一由 `manga_translator/utils/inference.py` 中的 `ModelWrapper` 驱动。
下载源策略通过独立文件 `examples/model_sources.toml` 控制。

支持三种策略：

- `official_first`
  - 内置标准源 -> 内置镜像源
- `mirror_first`
  - 内置镜像源 -> 内置标准源
- `custom`
  - `custom.urls[key] -> builtin official -> builtin mirror`

其中：
- `builtin.official` / `builtin.mirror` 在示例文件中仅作只读参考
- 运行时真正使用的 builtin URL 仍来自各模型类的 `_MODEL_MAPPING`
- 可修改区只有 `[custom.urls]`

### .env 与 MODEL_SOURCES_PATH

如果不设置环境变量，程序默认读取：

- 开发环境：`examples/model_sources.toml`
- 打包环境：`_MEIPASS/examples/model_sources.toml`

如需切换到外部配置文件，可在 `.env` 中设置：

```env
MODEL_SOURCES_PATH=/abs/path/to/model_sources.toml
```

推荐做法：
- `.env` 只负责指向哪份 TOML
- 具体下载源策略写在 `model_sources.toml`

### 相关校验建议

修改模型下载源相关逻辑后，至少检查：

1. `tests/model_sources/test_model_sources.py`
   - 路径优先级
   - fallback
   - 稳定文件名
   - archive / hash 失败回退
2. 开发环境默认路径是否正确读取 `examples/model_sources.toml`
3. `.env` 中 `MODEL_SOURCES_PATH` 是否能覆盖默认路径
4. 打包环境是否仍能从 `_MEIPASS/examples/` 读取默认 TOML

## 6. 推荐启动顺序

```bash
# 1. 创建并激活环境
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# 2. 安装依赖（示例：CPU）
pip install -r requirements_cpu.txt

# 3. 启动桌面端
python -m desktop_qt_ui.main
```

如果你主要开发服务端：

```bash
python -m manga_translator web --host 127.0.0.1 --port 8000 -v
```

### 6.1 常见改动落点

#### 新增一个设置项

至少按下面这条链路检查，很多设置不是只改 5 个地方就够：

1. `desktop_qt_ui/core/config_models.py`
   定义字段、默认值、类型、校验和兼容迁移。
2. `manga_translator/config.py`
   如果这个设置会进入核心翻译流水线、CLI、Web 服务或底层模块配置，还要同步这里的核心配置模型和相关枚举；否则桌面端存下来了，后端实际运行时可能根本读不到。
3. `examples/config-example.json`
   同步默认配置模板，保证新字段能写入导出配置和首次启动配置。
4. `desktop_qt_ui/locales/settings_tab_layout.json`
   如果这个设置要出现在设置页，需要把 `section.key` 放进对应 tab 的 `items`。
5. `desktop_qt_ui/app_logic.py`
   如果设置是下拉选项或需要友好显示，补 `get_options_for_key()`、`get_display_mapping()`，必要时补 `labels` 映射。
6. `desktop_qt_ui/locales/*.json`
   至少补 `label_xxx` 和 `desc_section_key`；如果是枚举值，还要补对应选项文案 key。
7. `desktop_qt_ui/main_view_parts/dynamic_settings.py`
   如果默认的通用控件不够用，或者这个字段要隐藏、分组、加按钮、加占位符、走特殊编辑器，就在这里补特殊逻辑。
8. `desktop_qt_ui/app_logic.py`
   如果设置变化后要立刻触发副作用，比如切换翻译器、刷新渲染、联动其他字段，就补 `update_single_config()` 里的即时处理。
9. 实际消费该设置的模块
   例如 `desktop_qt_ui/services/`、`manga_translator/ocr/`、`manga_translator/rendering/`、`manga_translator/translators/` 等，否则设置只会“存起来但不起作用”。

按设置类型，再额外检查这些位置：

- 如果是“新枚举值”而不是“新字段”：
  同时检查 `manga_translator/config.py` 里的 Enum / 配置类型、`desktop_qt_ui/app_logic.py` 里的选项列表和显示映射，以及相关 locale 文案。
- 如果设置也要影响命令行或 Web 运行：
  检查 `manga_translator/config.py`、`manga_translator/args.py`、相关 mode/service 的参数合并逻辑，以及后端实际消费点。
- 如果设置引入新的 API 依赖或环境变量：
  检查 `examples/config/translators.json` 和 `desktop_qt_ui/services/config_service.py` 里的校验逻辑。
- 如果设置属于导入导出时应排除的临时状态：
  检查 `desktop_qt_ui/app_logic.py` 的 `export_config()` / `import_config()`。
- 如果设置会影响编辑器侧展示或编辑行为：
  继续检查 `desktop_qt_ui/editor/` 和 `desktop_qt_ui/widgets/property_panel.py`。

#### 新增或接入一个翻译器 / OCR / 渲染器

通常需要同步：

1. 在 `manga_translator/<对应模块>/` 新增实现
2. 更新配置/枚举入口
3. 如果涉及 API 环境变量，更新 `examples/config/translators.json`
4. 必要时补 UI 选项、文档说明和测试

#### 修改编辑器行为

优先从 `desktop_qt_ui/editor/` 下找：

- `editor_controller.py`
- `editor_logic.py`
- `graphics_view.py`
- `graphics_items.py`
- `commands.py`
- `selection_manager.py`

## 7. 校验与调试

### 代码风格

仓库里目前能看到的唯一已跟踪静态检查配置文件是 `desktop_qt_ui/ruff.toml`。

如果本地已经安装 `ruff`，可以用下面这条命令做一次基础检查：

```bash
ruff check desktop_qt_ui manga_translator --config desktop_qt_ui/ruff.toml
```

这个结论的边界是：

- 仓库中没有其他已跟踪的 `pyproject.toml`、`setup.cfg`、`tox.ini`、`.flake8`、第二份 `ruff.toml` 等配置文件。
- 当前 GitHub Actions 里也没有显式执行 lint 步骤。
- 所以上面的命令更适合作为本地自检入口，不表示仓库 CI 当前已经把它当成必过步骤。

这份 `ruff.toml` 当前规则以 `E`、`F`、`I` 为主，忽略 `E501`、`E701`、`E402`。

### 调试文档

- 详细排障流程请看 [调试指南](DEBUGGING.md)

## 8. 打包与发布

### 本地 PyInstaller 构建

构建脚本入口：

```bash
python packaging/build_packages.py <version> --build cpu
python packaging/build_packages.py <version> --build gpu
python packaging/build_packages.py <version> --build both
```

相关文件：

- `packaging/build_packages.py`
- `packaging/manga-translator-cpu.spec`
- `packaging/manga-translator-gpu.spec`
- `packaging/create-manga-pdfs.spec`
- `packaging/manga-chapter-splitter.spec`

### 启动与安装脚本

面向最终用户的脚本主要在仓库根目录：

- `步骤1-首次安装.bat`
- `步骤2-启动Qt界面.bat`
- `步骤3-检查更新并启动.bat`
- `步骤4-更新维护.bat`
- `macOS_*.sh`

这些脚本的实际逻辑集中在 `packaging/launch.py`、`packaging/git_update.py` 等文件里。修改安装/更新行为时，不要只改 `.bat` 或 `.sh` 外壳。

### CI/CD

- `.github/workflows/build-and-release.yml`
  - Windows 上构建 CPU/GPU PyInstaller 包
  - Ubuntu 上整理 `_internal` 资源并发布 Release
- `.github/workflows/docker-build-push.yml`
  - 基于 `packaging/Dockerfile` 构建 CPU/GPU Docker 镜像

如果你新增了打包必须资源，请同步更新 workflow 中复制 `_internal` 的步骤。

## 9. 开发建议

- 涉及配置、模板、字体、词典时，始终同时验证开发态和打包态路径。
- 修改桌面端设置项时，至少检查默认配置、UI 文案、多语言文件和序列化兼容。
- 修改发布流程时，别只看本地 `packaging/`，还要一起检查 GitHub Actions。

## 10. 相关文档

- [安装指南](INSTALLATION.md)
- [使用教程](USAGE.md)
- [命令行模式使用指南](CLI_USAGE.md)
- [调试指南](DEBUGGING.md)
- [设置说明](SETTINGS.md)

