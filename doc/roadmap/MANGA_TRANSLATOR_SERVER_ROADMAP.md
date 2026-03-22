# manga-translator-server 路线图

## 目标

将当前分支逐步收敛为 `manga-translator-server` 形态：

- 以 **server / CLI-first** 为主
- 以 **直出翻译效果最优** 为核心目标
- **不负责后续编辑闭环**，只保留必要的后处理空间
- 主产物为 **结果图 + JSON 中间产物**

## 非重点

以下能力暂时降级，不再作为主设计中心：

- Qt 桌面 UI
- 可视化编辑器
- PSD / Photoshop 导向工作流
- 多用户管理后台
- 账户、权限、审计、配额等平台化能力
- 为后续人工编辑设计的复杂交互

## 原则

1. **CLI-first**：新增能力先在 CLI / server 落地。
2. **效果优先**：优先投入 detection / OCR / translation / inpainting / rendering 质量。
3. **输出清晰**：固定主产物为结果图与 JSON。
4. **核心解耦**：逐步去除 CLI / server 对 `desktop_qt_ui` 的直接依赖。
5. **先降权，再删除**：非主路径能力先退出设计中心，再决定是否移除。

## 分阶段

### 阶段 1：收束主路径

- 将文档叙事调整为 server / CLI-first
- 明确主工作流：输入图片 → 翻译 → 输出结果图 + JSON
- 将导入翻译、replace translation、编辑器专属流程降为兼容路径

### 阶段 2：去 UI 依赖

- 迁出 `manga_translator/mode/local.py` 对 `desktop_qt_ui.services.*` 的依赖
- 将配置加载、文件发现、输出路径等能力下沉到 `manga_translator/` 核心层
- 让 UI 依赖核心，而不是核心反向借用 UI

### 阶段 3：稳定输出协议

固定输出：

- 最终结果图
- JSON 翻译数据
- 可选中间产物：mask / inpainted / original text / translated text

要求：

- JSON 结构稳定
- 输出目录规则稳定
- CLI 与 server 输出保持一致

### 阶段 4：最小化服务化

优先保留：

- 提交任务
- 查询状态
- 获取结果
- 下载 JSON / 图片产物

优先避免：

- 重型后台管理
- 多用户权限体系
- 复杂审计与配额系统

## 当前优先事项

1. 重写 README / INSTALLATION / CLI_USAGE 的叙事顺序
2. 切断 `local` 对 `desktop_qt_ui.services.*` 的依赖
3. 明确结果图 + JSON 的输出协议
4. 将非目标工作流标记为兼容路径
