# v2.0.7 更新日志

发布日期：2026-01-10

## 🐛 修复

- 修复 OpenAI/Gemini 翻译器错误提示问题：
  - 修复 `finish_reason: stop` 但内容为空时误报"意外的结束原因"
  - 新增 `length`（token限制）和 `tool_calls`（工具调用）的专门处理
  - 完善降级机制：所有异常情况都会触发降级，下次重试不再发送图片
- 修复 PaddleOCR-VL 在打包模式下报错的问题
- 修复 PaddleOCR-VL 在 Windows 中文路径下崩溃问题

## 🔧 优化

- 升级 Gemini 翻译器到新版 SDK (`google-genai`)
- 更新项目依赖
- 新增 PaddleOCR-VL 自动修补工具，无需手动修改模型文件
- 优化 PaddleOCR-VL 日志输出，移除冗余信息
- Qt UI编辑器保存JSON时自动通过后端渲染更新原图片目录下的修复图片（inpainted）
- 优化后端渲染导出日志，避免重复输出
