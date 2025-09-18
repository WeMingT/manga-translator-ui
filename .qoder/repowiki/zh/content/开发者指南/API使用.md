# API使用

<cite>
**Referenced Files in This Document**   
- [manga_translator.py](file://manga_translator\manga_translator.py)
- [config.py](file://manga_translator\config.py)
- [args.py](file://manga_translator\args.py)
- [app_logic.py](file://desktop-ui\app_logic.py)
</cite>

## 目录
1. [API使用](#api使用)
2. [MangaTranslator类初始化](#mangatranslator类初始化)
3. [核心接口详解](#核心接口详解)
4. [配置管理](#配置管理)
5. [异步调用模式](#异步调用模式)
6. [错误处理机制](#错误处理机制)
7. [性能优化建议](#性能优化建议)
8. [参考案例](#参考案例)

## MangaTranslator类初始化

`MangaTranslator` 类是整个翻译引擎的核心，其初始化方法 `__init__` 接收一个字典参数 `params` 来配置翻译器的行为。该方法负责设置各种运行时参数和内部状态。

```python
def __init__(self, params: dict = {}):
    # 从params字典中提取配置
    self.pre_dict = params.get('pre_dict', None)  # 预翻译字典路径
    self.post_dict = params.get('post_dict', None)  # 后翻译字典路径
    self.font_path = None
    self.use_mtpe = False
    self.kernel_size = None
    self.device = None
    self.text_output_file = params.get('save_text_file', None)  # 指定翻译文本保存文件
    self._gpu_limited_memory = False
    self.ignore_errors = False
    self.verbose = False
    self.models_ttl = 0
    self.batch_size = 1  # 默认不进行批量处理

    self._progress_hooks = []
    self._add_logger_hook()

    params = params or {}
    
    # 批量处理相关属性
    self._batch_contexts = []  # 存储批量处理的上下文
    self._batch_configs = []   # 存储批量处理的配置
    self.disable_memory_optimization = params.get('disable_memory_optimization', False)
    self.batch_concurrent = params.get('batch_concurrent', False)  # 并发批量处理标志
        
    # 解析并应用初始化参数
    self.parse_init_params(params)
    self.result_sub_folder = ''

    # 启用PyTorch的TF32计算以提升性能
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    # 内部状态管理
    self._model_usage_timestamps = {}
    self._detector_cleanup_task = None
    self.prep_manual = params.get('prep_manual', None)
    self.context_size = params.get('context_size', 0)
    self.all_page_translations = []
    self._original_page_texts = []

    # 调试图片管理
    self._current_image_context = None
    self._saved_image_contexts = {}

    # 设置日志文件
    self._setup_log_file()
```

**Section sources**
- [manga_translator.py](file://manga_translator\manga_translator.py#L99-L175)

## 核心接口详解

`MangaTranslator` 类提供了多个主要接口来执行翻译任务，其中最核心的是 `translate` 和 `translate_batch` 方法。

### translate 方法

`translate` 方法用于翻译单张图片，是异步函数，返回一个 `Context` 对象。

```python
async def translate(self, image: Image.Image, config: Config, image_name: str = None, skip_context_save: bool = False) -> Context:
    """
    翻译单张图片。

    :param image: 输入图片。
    :param config: 翻译配置。
    :param image_name: 已弃用的参数，为兼容性保留。
    :return: 包含翻译结果的上下文对象。
    """
    ctx = Context()
    ctx.input = image
    ctx.image_name = image_name
    ctx.result = None
    ctx.verbose = self.verbose

    # 设置图片上下文以生成调试子文件夹
    self._set_image_context(config, image)
    ctx.debug_folder = self._get_image_subfolder()

    # 如果启用了加载文本模式，则跳过检测、OCR和翻译步骤
    if self.load_text:
        loaded_regions, loaded_mask, mask_is_refined = self._load_text_and_regions_from_file(ctx.image_name, config)
        if loaded_regions:
            # ... (加载逻辑)
            return await self._revert_upscale(config, ctx)
        else:
            raise FileNotFoundError(f"Load text mode failed: Translation file not found or invalid")

    # 保存原始输入图片用于调试
    if self.verbose:
        # ... (保存逻辑)

    # 预加载模型
    if self.models_ttl == 0:
        # ... (模型加载逻辑)

    # 执行完整的翻译流程
    ctx = await self._translate(config, ctx)

    # 在流程最后保存翻译结果，确保是最终结果（包括重试后的结果）
    if not skip_context_save and ctx.text_regions:
        page_translations = {r.text_raw if hasattr(r, "text_raw") else r.text: r.translation for r in ctx.text_regions}
        self.all_page_translations.append(page_translations)

        page_original_texts = {i: (r.text_raw if hasattr(r, "text_raw") else r.text) for i, r in enumerate(ctx.text_regions)}
        self._original_page_texts.append(page_original_texts)

    return ctx
```

**Section sources**
- [manga_translator.py](file://manga_translator\manga_translator.py#L177-L3170)

### translate_batch 方法

`translate_batch` 方法用于批量翻译多张图片，支持批量处理和并发模式，以提高效率。

```python
async def translate_batch(self, images_with_configs: List[tuple], batch_size: int = None, image_names: List[str] = None) -> List[Context]:
    """
    批量翻译多张图片，在翻译阶段进行批量处理以提高效率。

    :param images_with_configs: 图片和配置的元组列表。
    :param batch_size: 批量大小，如果为None则使用实例的batch_size。
    :param image_names: 已弃用的参数，为兼容性保留。
    :return: 包含翻译结果的上下文对象列表。
    """
    batch_size = batch_size or self.batch_size
    
    # 如果批量大小为1或处于“仅生成模板”模式，则逐个处理
    if batch_size <= 1 or (self.template and self.save_text):
        results = []
        for i, (image, config) in enumerate(images_with_configs):
            image_name_to_pass = image.name if hasattr(image, 'name') else None
            ctx = await self.translate(image, config, image_name=image_name_to_pass)
            results.append(ctx)
        return results

    # 处理所有图片到翻译之前的步骤（预处理）
    pre_translation_contexts = []
    for i, (image, config) in enumerate(images_with_configs):
        # ... (预处理逻辑，包括彩色化、上采样、检测、OCR等)
        ctx = await self._translate_until_translation(image, config)
        pre_translation_contexts.append((ctx, config))

    # 批量翻译处理
    try:
        if self.batch_concurrent:
            # 并发模式：为每张图片单独发送翻译请求
            translated_contexts = await self._concurrent_translate_contexts(pre_translation_contexts)
        else:
            # 标准批量模式：合并批次进行翻译
            translated_contexts = await self._batch_translate_contexts(pre_translation_contexts, batch_size)
    except MemoryError as e:
        # 内存不足时降级为逐个翻译
        # ... (降级处理逻辑)

    # 完成翻译后的处理（后处理）
    results = []
    for i, (ctx, config) in enumerate(translated_contexts):
        if ctx.text_regions:
            # 恢复图片上下文
            from .utils.generic import get_image_md5
            image = ctx.input
            image_md5 = get_image_md5(image)
            self._restore_image_context(image_md5)
            # 执行掩码细化、修复、渲染等步骤
            ctx = await self._complete_translation_pipeline(ctx, config)
        results.append(ctx)

    # 清理缓存
    self._saved_image_contexts.clear()
    return results
```

**Section sources**
- [manga_translator.py](file://manga_translator\manga_translator.py#L2797-L3170)

## 配置管理

`MangaTranslator` 通过 `Config` 类和字典来管理配置。`Config` 类定义了翻译流程中各个组件的配置选项。

### Config 类结构

`Config` 类是一个 Pydantic 模型，包含了所有子模块的配置。

```python
class Config(BaseModel):
    # 通用设置
    filter_text: Optional[str] = None
    render: RenderConfig = RenderConfig()
    upscale: UpscaleConfig = UpscaleConfig()
    translator: TranslatorConfig = TranslatorConfig()
    detector: DetectorConfig = DetectorConfig()
    colorizer: ColorizerConfig = ColorizerConfig()
    inpainter: InpainterConfig = InpainterConfig()
    ocr: OcrConfig = OcrConfig()
    force_simple_sort: bool = False
    kernel_size: int = 3
    mask_dilation_offset: int = 20
    _filter_text = None

    @property
    def re_filter_text(self):
        if self._filter_text is None:
            self._filter_text = re.compile(self.filter_text)
        return self._filter_text
```

### 通过字典传递配置

可以在初始化 `MangaTranslator` 时，直接通过字典传递配置参数。

```python
# 示例：通过字典创建配置
config_dict = {
    'verbose': True,
    'use_gpu': True,
    'pre_dict': 'path/to/pre_dict.txt',
    'post_dict': 'path/to/post_dict.txt',
    'batch_size': 4,
    'batch_concurrent': True,
    'config': {
        'translator': {
            'translator': 'sakura',
            'target_lang': 'ENG'
        },
        'detector': {
            'detection_size': 1024
        }
    }
}

# 初始化翻译器
translator = MangaTranslator(config_dict)
```

### 通过JSON文件传递配置

也可以将配置保存为JSON文件，然后在代码中读取。

```python
import json

# 从JSON文件读取配置
with open('config.json', 'r', encoding='utf-8') as f:
    config_data = json.load(f)

# 初始化翻译器
translator = MangaTranslator(config_data)
```

**Section sources**
- [config.py](file://manga_translator\config.py#L200-L363)
- [manga_translator.py](file://manga_translator\manga_translator.py#L177-L175)

## 异步调用模式

`MangaTranslator` 的核心方法都是异步的，需要在异步环境中调用。最佳实践是使用 `aiohttp` 和事件循环。

### 使用aiohttp和事件循环

```python
import asyncio
import aiohttp
from PIL import Image
from manga_translator.manga_translator import MangaTranslator
from manga_translator.config import Config

async def main():
    # 创建翻译器实例
    translator = MangaTranslator({
        'use_gpu': True,
        'verbose': True
    })

    # 创建配置对象
    config = Config()
    config.translator.target_lang = 'ENG'
    config.detector.detection_size = 1024

    # 加载图片
    image = Image.open('path/to/your/manga.jpg')

    # 调用异步翻译方法
    try:
        result_ctx = await translator.translate(image, config)
        # 获取结果图片
        result_image = result_ctx.result
        result_image.save('translated_manga.jpg')
        print("翻译完成！")
    except Exception as e:
        print(f"翻译过程中发生错误: {e}")

# 创建事件循环并运行
if __name__ == "__main__":
    asyncio.run(main())
```

### 在独立脚本中使用

```python
# standalone_script.py
import asyncio
from PIL import Image
from manga_translator.manga_translator import MangaTranslator
from manga_translator.config import Config

async def translate_single_image(image_path, output_path):
    # 初始化翻译器
    translator = MangaTranslator({
        'use_gpu': True,
        'batch_size': 2,
        'batch_concurrent': True
    })

    # 创建配置
    config = Config()
    config.translator.translator = 'sakura'
    config.translator.target_lang = 'ENG'
    config.render.font_size_offset = 2

    # 加载图片
    image = Image.open(image_path)

    # 执行翻译
    ctx = await translator.translate(image, config)

    # 保存结果
    if ctx.result:
        ctx.result.save(output_path)
        print(f"翻译完成，结果已保存至: {output_path}")
    else:
        print("翻译失败，未生成结果。")

# 运行异步任务
if __name__ == "__main__":
    asyncio.run(translate_single_image('input.jpg', 'output.jpg'))
```

**Section sources**
- [manga_translator.py](file://manga_translator\manga_translator.py#L177-L3170)

## 错误处理机制

`MangaTranslator` 提供了完善的错误处理机制，主要通过 `ignore_errors` 参数和异常捕获来实现。

### 捕获TranslationError异常

虽然代码中没有显式定义 `TranslationError`，但可以通过捕获通用异常来处理错误。

```python
from manga_translator.manga_translator import MangaTranslator
from manga_translator.config import Config
from PIL import Image

async def safe_translate(image, config):
    translator = MangaTranslator({
        'ignore_errors': True,  # 设置为True时，错误不会中断流程
        'verbose': True
    })

    try:
        result_ctx = await translator.translate(image, config)
        return result_ctx
    except Exception as e:
        print(f"发生未预期的错误: {e}")
        # 可以选择返回None或一个默认的Context
        return None

# 使用示例
async def main():
    image = Image.open('manga.jpg')
    config = Config()
    config.translator.target_lang = 'ENG'

    result = await safe_translate(image, config)
    if result and result.result:
        result.result.save('output.jpg')
```

**Section sources**
- [manga_translator.py](file://manga_translator\manga_translator.py#L177-L3170)

## 性能优化建议

为了获得最佳性能，可以采取以下优化措施：

### 批量处理

使用 `batch_size` 参数进行批量处理，可以显著提高处理速度。

```python
# 初始化翻译器时设置批量大小
translator = MangaTranslator({
    'batch_size': 4,  # 一次处理4张图片
    'batch_concurrent': True  # 使用并发模式
})
```

### 资源释放

在长时间运行的应用中，应定期释放未使用的模型以节省内存。

```python
# 设置模型的生存时间（TTL），单位为秒
translator = MangaTranslator({
    'models_ttl': 300  # 5分钟后自动卸载未使用的模型
})
```

### 内存优化

在内存受限的环境中，可以禁用内存优化或使用GPU有限内存模式。

```python
translator = MangaTranslator({
    'use_gpu_limited': True,  # 使用GPU但排除离线翻译器
    'disable_memory_optimization': False  # 启用内存优化
})
```

**Section sources**
- [manga_translator.py](file://manga_translator\manga_translator.py#L99-L3170)
- [args.py](file://manga_translator\args.py#L50-L80)

## 参考案例

`desktop-ui` 中的 `AppLogic` 类是 `MangaTranslator` 的一个实际调用参考案例。

### AppLogic 对 MangaTranslator 的调用

```python
class AppLogic:
    def start_backend_task(self) -> bool:
        """开始执行后端任务（翻译或修图）"""
        try:
            files = self.state_manager.get_current_files()
            if not files:
                return False

            # 获取JSON配置
            translator_json_config = self.config_service.get_config()
            if not translator_json_config:
                return False

            # 构建工作流参数
            workflow_args_context = self._build_backend_args()
            if workflow_args_context is None:
                return False

            # 初始化翻译器服务
            if not self.translation_service.is_translator_ready():
                if not self.translation_service.initialize_translator():
                    return False
            
            # 启动后台线程执行异步任务
            def progress_callback(progress: TranslationProgress):
                self.progress_manager.update_task(task_id, progress.current_step, progress.message)
                self.state_manager.set_translation_progress(progress.percentage)
            
            threading.Thread(
                target=self._run_backend_task_async,
                args=(files, task_id, progress_callback, translator_json_config, workflow_args_context),
                daemon=True
            ).start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"开始任务时发生异常: {e}")
            return False

    def _run_backend_task_async(self, files: List[str], task_id: str, progress_callback: Callable, config: Any, args: Any):
        """异步执行后端任务"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 调用翻译服务的异步批量翻译方法
            results = loop.run_until_complete(
                self.translation_service.translate_batch_async(
                    files,
                    progress_callback,
                    config=config,
                    args=args
                )
            )
            
            self._handle_task_results(results, task_id)
            
        except Exception as e:
            self.logger.error(f"后端任务执行异常: {e}")
        finally:
            try:
                loop.close()
            except:
                pass
```

此案例展示了如何在桌面应用中集成 `MangaTranslator`，通过创建独立的事件循环来调用其异步方法，并通过进度回调和结果处理来管理任务生命周期。

**Section sources**
- [app_logic.py](file://desktop-ui\app_logic.py#L100-L317)