# 架构方向结论（CLI-first）

## 1. 总结

- 先做 **headless core/app**，不再让 GUI 持有通用能力。
- CLI 是第一个正式 **adapter**，不是临时脚本层。
- GUI / Web 后续只作为外壳接入，不允许反向影响 core。
- 近期主栈继续用 **Python**；**Rust** 只用于高收益、边界稳定的模块。

## 2. 目标

- 先把 CLI 做稳，作为主入口。
- 支持多 worker 批处理。
- 支持模型缓存生命周期管理。
- 支持任务取消 / 恢复。
- 支持长驻服务。
- 后续可平滑接入 GUI / Web。

## 3. 非目标

- 近期不围绕 Qt UI 继续做架构设计。
- 近期不做全栈 Rust 重写。
- 不允许 `core -> CLI/GUI/Web` 的反向依赖。
- 不允许 CLI 继续依赖 GUI service 层。

## 4. 分层

### core
纯领域层，只放：
- Config / Request / Result
- Artifact / Event / Error
- PipelineState / TextBlock 等基础模型

### app
用例与编排层，只放：
- `translate_one`
- `translate_batch`
- `export_artifacts`
- workspace / batch / job usecase

### runtime
运行时层，只放：
- daemon / scheduler
- job queue / worker pool
- model cache manager
- cancellation / recovery
- health / metrics / resource control

### workers / infra
执行层：
- detect / ocr / translate / inpaint / render executor
- 近期先保留 Python 实现

### interfaces
接口层：
- CLI
- future Web API / Web UI
- future GUI

## 5. 依赖方向

允许：
- `interfaces -> app/runtime/core`
- `runtime -> app/core`
- `workers/infra -> app/core`

禁止：
- `core -> runtime/interfaces`
- `CLI <-> GUI <-> Web` 互相复用业务逻辑
- GUI 持有共享导出、配置、文件发现等核心能力

## 6. 技术栈建议

### 近期主栈
- Python 3.12
- `pydantic`：配置 / 请求 / 结果 / 事件模型
- `typer`：CLI
- `FastAPI`：后续 API / Web
- `asyncio`：任务与并发编排

### Rust 定位
- 不是近期主战场
- 作为中后期 runtime / renderer / image postprocess 的增强手段

## 7. 演进顺序

1. 先剥离 headless core/app，切断 GUI 反向依赖。
2. 把 CLI 重写成第一个正式 adapter。
3. 建立 runtime：job queue / worker / cache / cancel / recover / daemon。
4. 用 CLI 把 runtime 跑稳。
5. 再接 GUI / Web。
6. 最后按收益局部 Rust 化。

## 8. Rust 采用策略

### 优先 Rust 化
- runtime / supervisor
- model cache manager
- task cancellation / recovery state machine
- renderer
- image postprocess
- export / PSD

### 暂不优先 Rust 化
- 整个 pipeline orchestration
- 模型接入主体
- CLI / Web 接口层
- 快速迭代中的 app/usecase 层

## 9. 当前仓库优先改造点

- 从 core 中移除对 `desktop_qt_ui` 的反向 import。
- 把模板导出逻辑移到共享的 `app/export` 层。
- 把 CLI 的 config/file discovery 从 GUI service 中挪出。
- 取消 `sys.path` 注入式依赖。
- 为 runtime 统一定义：
  - `Request`
  - `ProgressEvent`
  - `JobState`
  - `ArtifactManifest`

## 10. 结论

当前正确路线不是“先做 CLI，再全局 Rust 化”，而是：

**先抽离 core/app，用 CLI 验证架构，再按收益把 runtime 和热点模块局部 Rust 化。**
