# v2.0.9 更新日志

发布日期：2026-02-14

## ✨ 新功能

- **增强的输出格式支持**：
  - Qt 编辑器和翻译后端现在支持更多输出格式
  - 新增支持：AVIF、BMP、TIFF、HEIC/HEIF 格式
  - 完整支持列表：PNG、JPEG、WebP、AVIF、BMP、TIFF、HEIC/HEIF
  - HEIC/HEIF 格式需要安装 `pillow-heif` 库，未安装时自动降级为 PNG

- **curl_cffi TLS 指纹伪装**：
  - Gemini 翻译器支持 curl_cffi 绕过 TLS 指纹检测
  - 支持自定义 Gemini API Base 使用 Google 原生认证方式（x-goog-api-key）
  - 支持包含 "/" 的模型名（如 z-ai/glm4.7）自动 URL 编码

- **MangaLens 气泡检测与长图支持**：
  - 新增 `mangalens.onnx` 气泡检测模块（纯 `onnxruntime`，移除 `ultralytics` 依赖）
  - 支持 CUDA/CPU 自动回退，模型下载地址统一到模型仓库
  - 新增长图切割检测（对齐 YOLO 辅助检测长图逻辑），分片推理后回映射并全局去重

- **OCR 气泡过滤配置**：
  - 新增 `use_model_bubble_filter` 开关
  - 新增 `model_bubble_overlap_threshold` 阈值配置
  - 补齐多语言 i18n（`zh_CN`、`zh_TW`、`en_US`、`ja_JP`、`ko_KR`、`es_ES`）

- **蒙版优化策略扩展**：
  - 新增“扩大气泡修复范围”配置（`use_model_bubble_repair_intersection`）
  - 仅保留与优化蒙版有交集的气泡连通域，并与优化蒙版合并

## 🐛 修复

- 修复 Qt 编辑器翻译图查看模式下图片不显示的问题（翻译后的图片现在正确加载到 inpainted 层）
- 修复并行模式下 PSD 导出图层缺少修复图的问题（修复图现在在 PSD 导出前保存）
- 修复并行模式下停止翻译响应不及时的问题（增加更多取消检查点，优化线程停止逻辑）
- 修复 Qt 编辑器中手动添加换行符后文本仍被强制换行的问题（检测到换行符时自动开启 AI 断句）
- 修复 Qt 编辑器蒙版编辑工具光标在整个应用程序显示的问题（光标现在仅在画布上显示）
- 修复 Qt 编辑器导出时拖动白框后文本位置不更新的问题（导出前会将白框中心同步到 `center`）
- 修复 `generate_and_export` 在高质量翻译分支未执行蒙版优化的问题（现在会先做 mask refinement 再写入 JSON）
- 修复导入翻译并渲染（`load_text`）后 JSON 不回写的问题（渲染后会回写最新 `regions`，包括 `translation`/`font_size`）
- 修复 `AsyncGeminiCurlCffi` 响应解析时 `NoneType` 不可迭代错误
- 修复 Gemini API 安全设置格式错误（去掉枚举类名前缀）
- 修复 Gemini API 请求缺少 `role` 字段导致 400 错误
- 修复多模态不支持错误检测（新增 `image_url`、`expected \`text\``、`unknown variant` 关键词）
- 修复 API 连接测试使用 GPT-5.2 等新模型时 `max_tokens` 参数不支持的问题（移除该参数以兼容所有模型）
- 修复 Gemini 翻译器在 `max_tokens` 为 None 时仍传递 `max_output_tokens` 参数的问题（现在只在非 None 时传递）

## 🔧 优化

- curl_cffi 客户端仅在出错时打印日志
- 更新模型推荐为最新版本（gpt-5.2、gemini-3-pro、grok-4.2）
- 友好错误提示使用 UI 显示名称（OpenAI高质量翻译、Google Gemini 等）
- 重构 Qt 编辑器：支持彩色描边，并优化编辑交互体验
- 导出模式（导出原文/导出翻译）写入 `skip_font_scaling=false`，导入渲染时按 JSON 标志决定是否跳过字体缩放
- 移除导出原文/导出翻译阶段的字体缩放预计算，避免导出流程隐式改写文本布局
- 统一 `generate_and_export` 执行路径（单图/标准批量/高质量批量共用同一处理逻辑）
- 统一 `template + save_text` 执行路径（共用导出原文处理逻辑）
