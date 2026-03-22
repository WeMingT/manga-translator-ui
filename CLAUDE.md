# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## 常用命令

### 环境与依赖

- 本仓库以 **Python 3.12** 为基线。
- 按运行目标只安装一套依赖：

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

- 仓库现在也提供可选的 uv 工作流，入口在 `pyproject.toml` 与 `uv.lock`：

```bash
uv venv --python 3.12

# CPU
uv sync --extra cpu

# NVIDIA GPU（CUDA 12.x）
uv sync --extra gpu

# AMD GPU（实验性，仅同步非 torch / 非 ROCm 特殊安装部分）
uv sync --extra amd

# Apple Silicon / Metal
uv sync --extra metal

# 打包相关
uv sync --extra build
```

- 注意：AMD 的 ROCm PyTorch 当前仍依赖现有安装脚本 / `packaging/launch.py` 的特殊处理，`uv sync --extra amd` 目前主要覆盖非 torch 依赖。
- PyInstaller 打包前还需要：

```bash
pip install pyinstaller
```

### 启动桌面端 / Web / CLI

```bash
# Qt 桌面端
python -m desktop_qt_ui.main

# Web 服务
python -m manga_translator web --host 127.0.0.1 --port 8000

# Web 服务（详细日志）
python -m manga_translator web --host 127.0.0.1 --port 8000 -v

# 本地命令行翻译
python -m manga_translator local -i path/to/image.png -o path/to/output

# 查看 CLI 帮助
python -m manga_translator --help
```

补充：[README.md](README.md) 中还记录了 macOS Apple Silicon 启动脚本 `macOS_2_启动Qt界面.sh`。

### Lint

仓库里当前已跟踪的 Ruff 配置在 `desktop_qt_ui/ruff.toml`：

```bash
ruff check desktop_qt_ui manga_translator --config desktop_qt_ui/ruff.toml
```

注意：当前 GitHub Actions 没有显式执行 lint。

### 打包 / 发布

```bash
# 本地 PyInstaller 构建
python packaging/build_packages.py <version> --build cpu
python packaging/build_packages.py <version> --build gpu
python packaging/build_packages.py <version> --build both
```

发布相关 CI：
- `.github/workflows/build-and-release.yml`：Windows 构建 CPU/GPU PyInstaller 包，并在 Ubuntu 上整理 `_internal` 资源后发布 Release
- `.github/workflows/docker-build-push.yml`：基于 `packaging/Dockerfile` 构建 CPU/GPU Docker 镜像

### Docker 运行

[README.md](README.md) 中给出的已发布镜像运行方式：

```bash
docker run -d --name manga-translator -p 8000:8000 hgmzhn/manga-translator:latest-cpu
```

默认访问：
- 用户界面：`http://localhost:8000`
- 管理界面：`http://localhost:8000/admin.html`

### 测试现状

- `pyproject.toml` 与 `uv.lock` 已纳入版本控制；其中 `dev` extra 包含 `pytest` 与 `pytest-anyio`。
- 仓库里现已存在已跟踪测试文件 `tests/model_sources/test_model_sources.py`，重点覆盖模型下载源路径优先级、fallback、稳定文件名与 archive/hash 失败回退。
- 当前仍没有 `pytest.ini`、`tox.ini`、`setup.cfg`，也没有看到 `pyproject.toml` 中的 pytest 配置段。
- 当前 GitHub Actions 也没有执行测试。
- 仓库里仍存在少量散落在源码文件中的 `def test_*` 函数，但它们不是一个明确、统一的测试套件。
- 因此：**不要假设存在稳定的仓库级测试矩阵。** 如需自动化验证，先确认目标测试是否真的能被 pytest 收集；模型下载源相关改动优先检查 `tests/model_sources/test_model_sources.py`。

## 高层架构

## 整体形态

这是一个“**同一核心引擎，多入口形态**”的仓库：

- `desktop_qt_ui/`：PyQt6 桌面应用
- `manga_translator/`：核心翻译引擎、CLI、Web 服务端
- `manga_translator/server/`：FastAPI 服务、静态页面、管理后台
- `packaging/`：启动器、更新逻辑、PyInstaller、Docker

核心翻译能力不在 UI 层，而是在 `manga_translator/`；桌面端和 Web 端本质上都是对同一套处理链的不同外壳。

## 入口与调用链

### Qt 桌面端

桌面端入口是 `desktop_qt_ui/main.py`，主路径大致是：

1. 初始化日志、资源路径、异常处理
2. 调用 `desktop_qt_ui/services/__init__.py` 中的 `init_services(root_dir)`
3. 创建 `MainWindow`
4. 再由 `desktop_qt_ui/main_view.py`、`desktop_qt_ui/main_view_parts/`、`desktop_qt_ui/editor/` 组装主界面和编辑器

`desktop_qt_ui/main.py` 同时兼容开发态与 PyInstaller：开发态把项目根目录当作 `root_dir`，打包态使用 `sys._MEIPASS` / `_internal` 资源目录。

### CLI / 模式分发

统一入口是 `manga_translator/__main__.py`，参数定义在 `manga_translator/args.py`。

支持的模式：
- `web`：启动 FastAPI 服务与 Web UI
- `local`：命令行本地翻译
- `ws`：WebSocket 模式
- `shared`：共享 API 实例模式

`parse_args()` 还有一个仓库特有行为：如果第一个参数不是模式，但命令里包含 `-i/--input`，它会自动插入 `local` 模式。

### Web 服务端

`manga_translator/__main__.py` 的 `web` 模式会分发到 `manga_translator/server/main.py`。

服务端职责包括：
- 创建 `FastAPI()` 应用
- 初始化账户、会话、权限、审计、历史、资源、配额等服务
- 挂载 `manga_translator/server/static/` 静态资源
- 共享 `desktop_qt_ui/locales/` 作为 i18n 资源
- 启动后台清理任务

## 桌面 UI 如何复用核心翻译引擎

桌面端正常工作时**不是通过 shell 调 CLI 子进程来驱动主流程**，而是通过服务层直接复用后端 Python 模块：

- `desktop_qt_ui/services/__init__.py` 初始化服务容器，注册 `ConfigService`、`TranslationService`、`OcrService`、`AsyncService`、`HistoryService`、`RenderParameterService`、`ResourceManager` 等服务。
- `desktop_qt_ui/services/translation_service.py` 直接导入并调用 `manga_translator.translators.dispatch`。
- `desktop_qt_ui/services/ocr_service.py` 直接导入并调用 `manga_translator.ocr.prepare` / `manga_translator.ocr.dispatch`。
- `desktop_qt_ui/app_logic.py` 负责批量任务编排、线程/worker 生命周期、进度与结果回调。

也就是说：
- `desktop_qt_ui/` 负责 UI、任务编排、交互状态
- `manga_translator/` 负责 detection / OCR / translation / inpainting / rendering / upscaling / colorization 等核心流水线

## 编辑器模块职责

编辑器相关代码主要在 `desktop_qt_ui/editor/`，可按下面理解：

- `desktop_qt_ui/editor/editor_controller.py`：编辑器业务控制器，响应视图事件并调用 OCR / translation / async / history / file / config / resource 服务
- `desktop_qt_ui/editor/editor_model.py`：编辑器状态模型
- `desktop_qt_ui/editor/editor_logic.py`：编辑器逻辑编排
- `desktop_qt_ui/editor/graphics_view.py` / `desktop_qt_ui/editor/graphics_items.py`：画布与图元交互
- `desktop_qt_ui/editor/commands.py`：命令对象，配合历史服务实现撤销/重做
- `desktop_qt_ui/editor/selection_manager.py`：区域选择管理

编辑器的 OCR、翻译、修复、导出同样是通过服务层复用核心引擎，不是另一套独立实现。

## 核心处理链

`manga_translator/` 下的关键职责分布：

- `detection/`：文本区域检测
- `ocr/`：OCR 模型与适配
- `translators/`：翻译器实现
- `inpainting/`：去字与背景修复
- `rendering/`：译文排版回写
- `upscaling/`：超分
- `colorization/`：上色
- `utils/`：通用工具与中间结构

## 配置、资源与跨文件改动点

### 配置加载与 `.env`

`desktop_qt_ui/services/config_service.py` 负责桌面端配置加载：
- 开发态从项目根目录读取 `.env`
- 打包态从可执行文件所在目录读取 `.env`
- 翻译器注册表来自 `examples/config/translators.json`
- 环境变量模板在 `.env.example`
- 模型下载源策略不在 `config.json` / `AppSettings` 中，而是独立放在 `examples/model_sources.toml`；如果需要改外部文件入口，通过 `.env` 中的 `MODEL_SOURCES_PATH` 指向。解析入口在 `manga_translator/model_sources.py`，实际下载时由 `manga_translator/utils/inference.py` 中的 `ModelWrapper` 调用 `resolve_candidate_urls()` 生效。

### 新增设置项时的真实落点

这个仓库里“新增一个设置项”通常不是只改一处。通常至少要检查：

- `desktop_qt_ui/core/config_models.py`
- `manga_translator/config.py`
- `examples/config-example.json`
- `desktop_qt_ui/locales/settings_tab_layout.json`
- `desktop_qt_ui/locales/*.json`
- `desktop_qt_ui/main_view_parts/dynamic_settings.py`
- 实际消费该设置的服务或核心模块

如果一个设置要同时影响桌面端、CLI、Web 或核心流水线，只改桌面 UI 配置模型通常是不够的。

### 打包资源约定

这个仓库同时支持开发态和 PyInstaller 打包态。新增模板、配置或资源目录时，不要只改 Python 代码，还要检查打包链。

当前 release workflow 会把这些目录复制进发布包 `_internal`：
- `examples/`
- `fonts/`
- `dict/`
- `doc/`
- `desktop_qt_ui/locales/`
- `packaging/VERSION`

如果新增的已跟踪资源需要在发布版运行时可见，需要同步检查：
- `packaging/*.spec`
- `.github/workflows/build-and-release.yml`

另外，模型目录 `models/` 是 gitignored 的，不随仓库提交；Release 流程会额外下载模型资产并注入发布包。不要假设模型文件已经在仓库里。

### 启动脚本外壳

仓库根目录的 `步骤1-首次安装.bat`、`步骤2-启动Qt界面.bat`、`步骤3-检查更新并启动.bat`、`步骤4-更新维护.bat`，以及 `macOS_1_首次安装.sh`、`macOS_2_启动Qt界面.sh`、`macOS_3_检查更新并启动.sh`、`macOS_4_更新维护.sh` 是最终用户入口，但安装/更新/启动的核心逻辑集中在 `packaging/launch.py`、`packaging/git_update.py` 等文件。修改安装或启动行为时，不要只改外层脚本。

## 运行时数据与输出目录

### 桌面端日志

- 根目录 `logs/`：桌面端日志由服务容器初始化时创建

### 每张图片的工作目录

编辑器与部分工作流会在源图片旁边使用 `manga_translator_work/` 目录，路径规则集中在 `manga_translator/utils/path_manager.py`。

常见子目录：
- `manga_translator_work/json/`：翻译数据 JSON
- `manga_translator_work/editor_base/`：编辑器专用底图（上色/超分后的底图）
- `manga_translator_work/originals/`：导出的原文 TXT
- `manga_translator_work/translations/`：翻译 TXT
- `manga_translator_work/inpainted/`：修复图
- `manga_translator_work/result/`：最终翻译结果图
- `manga_translator_work/psd/`：PSD 或 Photoshop 脚本
- `manga_translator_work/translated_images/`：替换翻译模式下的已翻译图片

在“输出到原图目录”模式下，批量翻译结果也会落到同级的 `manga_translator_work/result/`。

### Web 服务端数据

服务端运行时数据主要在：
- `manga_translator/server/data/`：账户、会话、权限、历史、结果等 JSON / 日志文件
- `manga_translator/server/user_resources/`：用户上传的字体、提示词等资源

这些目录偏运行时数据，不要把它们当成稳定源码区。

## 附录：修改设置项 / 翻译器时的检查清单

### 修改设置项时

新增或修改设置项时，通常至少同步检查下面这些层次：

1. `desktop_qt_ui/core/config_models.py`
   - 定义字段、默认值、类型、校验与兼容迁移。
2. `manga_translator/config.py`
   - 如果该设置会进入核心翻译流水线、CLI 或 Web 服务，需要同步核心配置模型；否则桌面端可能“能保存但后端不生效”。
3. `examples/config-example.json`
   - 更新默认配置模板，保证首次启动、导出配置和导入配置时字段完整。
4. `desktop_qt_ui/locales/settings_tab_layout.json`
   - 如果设置要出现在设置页，需要把对应 `section.key` 放进合适的 tab/items。
5. `desktop_qt_ui/locales/*.json`
   - 至少补 `label_xxx`、`desc_section_key`；如果是枚举值或选项列表，还要补对应选项文案。
6. `desktop_qt_ui/app_logic.py`
   - 如果设置需要选项映射、友好显示或立即触发副作用，检查 `get_options_for_key()`、`get_display_mapping()`、`update_single_config()` 等逻辑。
7. `desktop_qt_ui/main_view_parts/dynamic_settings.py`
   - 如果默认通用控件不够用，或这个设置需要特殊编辑器、隐藏/分组/按钮/占位符逻辑，需要在这里补 UI 特例。
8. 实际消费该设置的模块
   - 常见落点包括 `desktop_qt_ui/services/`、`manga_translator/ocr/`、`manga_translator/rendering/`、`manga_translator/translators/`、`manga_translator/server/`。

补充判断：
- 如果设置也要影响 CLI，继续检查 `manga_translator/args.py`。
- 如果设置也要影响 Web，可继续检查 `manga_translator/server/routes/`、`manga_translator/server/static/` 和相关服务层。
- 如果设置涉及 API Key / 环境变量，继续检查 `examples/config/translators.json`、`desktop_qt_ui/services/config_service.py` 和 `.env.example`。
- 如果设置涉及模型下载源策略或外部下载源入口，继续检查 `examples/model_sources.toml`、`manga_translator/model_sources.py` 与 `manga_translator/utils/inference.py`。

### 新增翻译器 / OCR / 渲染器时

通常需要沿着“实现 → 配置 → UI → 文案 → 资源”这条链路检查：

1. 在对应模块中补实现：
   - 翻译器：`manga_translator/translators/`
   - OCR：`manga_translator/ocr/`
   - 渲染：`manga_translator/rendering/`
2. 在 `manga_translator/config.py` 中补枚举、配置模型或默认值。
3. 确认现有 prepare / dispatch / 主流程能走到新实现；核心调用链通常会经过 `manga_translator/manga_translator.py` 和对应模块的调度逻辑。
4. 如果是需要 API 配置的翻译器或模型，更新 `examples/config/translators.json` 与 `desktop_qt_ui/services/config_service.py` 的环境变量校验逻辑。
5. 如果桌面端要让用户可选，继续检查：
   - `desktop_qt_ui/app_logic.py`
   - `desktop_qt_ui/locales/`
   - `desktop_qt_ui/main_view_parts/dynamic_settings.py`
6. 如果是基于提示词的 AI 能力，检查 `dict/` 下的提示词文件约定；当前仓库已存在翻译、OCR、上色、渲染等 prompt 文件路径说明。
7. 如果新增了运行时必须资源，别忘了同步检查打包链：`packaging/*.spec` 和 `.github/workflows/build-and-release.yml`。

## 附录：中文支持与国际化

- 仓库当前文档与用户界面是**简体中文优先**；新增用户可见说明时，至少保证中文文案完整。
- 桌面端国际化默认回退语言是 `zh_CN`，入口在 `desktop_qt_ui/services/i18n_service.py`。
- Web 端复用桌面端 locale 文件：`manga_translator/server/static/js/i18n.js` 会从 `/locales/{locale}.json` 加载翻译，因此 `desktop_qt_ui/locales/` 是 Qt / Web 共享文案源。
- 新增用户可见文本时，优先复用现有 i18n key；如果必须新增 key，保持 Qt / Web 共用的 key 体系，不要只在某一端硬编码文案。
- 新增带参数的文案时，保留占位符格式（如 `{param}`），避免破坏现有替换逻辑。
- 新增设置项如果需要出现在界面上，不仅要补 locale 文案，还要补 `desktop_qt_ui/locales/settings_tab_layout.json` 的布局映射。

## 附录：Markdown 文档链接规范

- 编写或更新 Markdown 文档时，如果引用本地 Markdown 文档，使用 `[]()` 链接。
- 链接文本使用目标 Markdown 文档的一级标题；如果目标文档没有一级标题，则使用文件名（例如 `README.md`）。
- 这条规则只适用于 Markdown 文档之间的本地引用；非 Markdown 本地文件保持普通路径或代码样式，不强制写成链接。

## 附录：Git 提交约定

这是当前仓库的工作约定，也是未来 Claude Code 在这里提交代码时应遵守的规则：

- **提交按语义分批次进行**：不要把无关改动混在同一个 commit 里。
  - 例如：文档更新、设置项接线、打包调整、纯重构，应该拆成不同提交。
- **提交信息使用语义化前缀**。仓库现有历史已经出现 `docs:`、`release:`、`fix:`，后续继续沿用这一风格；常用前缀可包括：
  - `feat:` 新功能
  - `fix:` 缺陷修复
  - `docs:` 文档更新
  - `refactor:` 重构
  - `chore:` 杂项维护
  - `release:` 发布相关改动
- **每个 commit 聚焦一个明确目的**，标题简洁说明本次改动的意图，不要把“顺手修复”混入无关提交。
- 如果用户明确要求提交代码，优先先整理出可独立理解的改动批次，再分别提交。
