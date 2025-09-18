# UI组件库

<cite>
**本文档中引用的文件**   
- [file_list_frame.py](file://desktop-ui/components/file_list_frame.py)
- [property_panel.py](file://desktop-ui/components/property_panel.py)
- [progress_dialog.py](file://desktop-ui/components/progress_dialog.py)
- [canvas_renderer_new.py](file://desktop-ui/components/canvas_renderer_new.py)
- [context_menu.py](file://desktop-ui/components/context_menu.py)
- [config_service.py](file://desktop-ui/services/config_service.py)
</cite>

## 目录
1. [项目结构](#项目结构)
2. [核心组件](#核心组件)
3. [架构概述](#架构概述)
4. [详细组件分析](#详细组件分析)
5. [依赖关系分析](#依赖关系分析)

## 项目结构

该桌面UI项目采用模块化设计，主要分为`components`（UI组件）、`services`（服务层）和`utils`（工具类）三大模块。UI组件基于`customtkinter`构建，实现了现代化的视觉风格和交互逻辑。服务层通过依赖注入模式为UI组件提供配置管理、进度控制、文件操作等核心功能。整体结构清晰，职责分离明确，便于维护和扩展。

```mermaid
graph TD
subgraph "UI组件层"
FileListFrame[文件列表组件]
PropertyPanel[属性面板组件]
ProgressDialog[进度对话框组件]
CanvasRenderer[画布渲染器]
ContextMenu[上下文菜单]
end
subgraph "服务层"
ConfigService[配置服务]
ProgressManager[进度管理器]
TransformService[变换服务]
OCRService[OCR服务]
TranslationService[翻译服务]
end
FileListFrame --> ConfigService
PropertyPanel --> ConfigService
PropertyPanel --> OCRService
PropertyPanel --> TranslationService
ProgressDialog --> ProgressManager
CanvasRenderer --> TransformService
ContextMenu --> OCRService
ContextMenu --> TranslationService
```

**图示来源**
- [file_list_frame.py](file://desktop-ui/components/file_list_frame.py#L1-L115)
- [property_panel.py](file://desktop-ui/components/property_panel.py#L1-L641)
- [progress_dialog.py](file://desktop-ui/components/progress_dialog.py#L1-L317)
- [canvas_renderer_new.py](file://desktop-ui/components/canvas_renderer_new.py#L1-L350)
- [context_menu.py](file://desktop-ui/components/context_menu.py#L1-L87)
- [config_service.py](file://desktop-ui/services/config_service.py#L1-L303)

## 核心组件

本文档详细分析了桌面UI中的五个核心可视化组件：`FileListFrame`实现可扩展的文件树结构与拖放支持，`PropertyPanel`动态渲染配置属性并绑定到`ConfigService`，`ProgressDialog`与`ProgressManager`服务集成以显示实时任务进度，`CanvasRenderer`采用双缓冲机制进行图像渲染，`ContextMenu`实现基于选中状态的条件显示策略。

**组件来源**
- [file_list_frame.py](file://desktop-ui/components/file_list_frame.py#L1-L115)
- [property_panel.py](file://desktop-ui/components/property_panel.py#L1-L641)
- [progress_dialog.py](file://desktop-ui/components/progress_dialog.py#L1-L317)
- [canvas_renderer_new.py](file://desktop-ui/components/canvas_renderer_new.py#L1-L350)
- [context_menu.py](file://desktop-ui/components/context_menu.py#L1-L87)

## 架构概述

系统采用分层架构，UI组件层负责用户交互和视觉呈现，服务层提供业务逻辑和数据管理。组件间通过回调函数和事件机制进行通信，实现了松耦合的设计。配置服务`ConfigService`作为中心枢纽，管理应用的全局设置和环境变量，确保了配置的一致性和可维护性。

```mermaid
graph TB
subgraph "表现层"
A[文件列表]
B[属性面板]
C[进度对话框]
D[画布渲染]
E[上下文菜单]
end
subgraph "控制层"
F[配置服务]
G[进度管理]
H[变换服务]
I[OCR服务]
J[翻译服务]
end
subgraph "模型层"
K[配置文件]
L[环境变量]
end
A --> F
B --> F
B --> I
B --> J
C --> G
D --> H
E --> I
E --> J
F --> K
F --> L
```

**图示来源**
- [config_service.py](file://desktop-ui/services/config_service.py#L1-L303)
- [property_panel.py](file://desktop-ui/components/property_panel.py#L1-L641)

## 详细组件分析

### 文件列表组件分析

`FileListFrame`组件实现了可扩展的文件树结构，支持添加单个文件、整个文件夹以及清空列表等操作。通过`customtkinter.CTkScrollableFrame`实现滚动功能，每个文件条目包含缩略图、文件名和卸载按钮。组件采用回调机制与主应用通信，实现了关注点分离。

```mermaid
classDiagram
class FileListFrame {
+on_file_select : Callable[[str], None]
+on_load_files : Callable
+on_load_folder : Callable
+file_paths : List[str]
+current_selection : CTkFrame
+__init__(parent, on_file_select, on_load_files, on_load_folder)
+add_files(file_paths : List[str])
+_add_file_entry(file_path : str)
+_on_entry_click(file_path : str, frame : CTkFrame)
+remove_file(file_path : str)
+clear_files()
}
FileListFrame --> CTkFrame : "继承"
FileListFrame --> CTkScrollableFrame : "包含"
FileListFrame --> Image : "使用"
FileListFrame --> ImageTk : "使用"
```

**图示来源**
- [file_list_frame.py](file://desktop-ui/components/file_list_frame.py#L1-L115)

**组件来源**
- [file_list_frame.py](file://desktop-ui/components/file_list_frame.py#L1-L115)

### 属性面板组件分析

`PropertyPanel`组件动态渲染文本区域的配置属性，并与`ConfigService`服务绑定。面板分为区域信息、文本内容、样式设置、蒙版编辑和操作按钮五个部分。通过`register_callback`方法注册事件回调，实现与主应用的双向数据绑定。组件支持实时更新文本统计信息，并提供颜色选择器等高级交互功能。

```mermaid
classDiagram
class PropertyPanel {
+canvas_frame : CanvasFrame
+current_region_data : Dict
+region_index : int
+callbacks : Dict[str, Callable]
+widgets : Dict[str, Any]
+__init__(parent, shortcut_manager)
+set_canvas_frame(canvas_frame)
+_create_widgets()
+load_region_data(region_data : Dict, region_index : int)
+clear_panel()
+register_callback(event_name : str, callback : Callable)
+_execute_callback(event_name : str, *args)
}
PropertyPanel --> CTkScrollableFrame : "继承"
PropertyPanel --> CollapsibleFrame : "使用"
PropertyPanel --> ConfigService : "依赖"
PropertyPanel --> OCRService : "依赖"
PropertyPanel --> TranslationService : "依赖"
```

**图示来源**
- [property_panel.py](file://desktop-ui/components/property_panel.py#L1-L641)

**组件来源**
- [property_panel.py](file://desktop-ui/components/property_panel.py#L1-L641)

### 进度对话框组件分析

`ProgressDialog`组件与`ProgressManager`服务集成，用于显示OCR识别和翻译等耗时任务的实时进度。对话框采用模态设计，包含进度条、状态标签和取消按钮。`OperationManager`类封装了异步操作的执行逻辑，通过工作线程避免阻塞UI主线程，确保了应用的响应性。

```mermaid
sequenceDiagram
participant UI as "UI组件"
participant OM as "OperationManager"
participant PD as "ProgressDialog"
participant Worker as "工作线程"
UI->>OM : execute_ocr_operation()
OM->>PD : 创建ProgressDialog
OM->>Worker : 启动线程
Worker->>Worker : 执行OCR操作
Worker->>PD : set_progress(0.5)
Worker->>PD : set_progress(0.9)
Worker->>UI : success_callback(result)
Worker->>PD : close_dialog()
```

**图示来源**
- [progress_dialog.py](file://desktop-ui/components/progress_dialog.py#L1-L317)

**组件来源**
- [progress_dialog.py](file://desktop-ui/components/progress_dialog.py#L1-L317)

### 画布渲染器组件分析

`CanvasRenderer`组件实现了图像渲染的双缓冲机制与缩放适配逻辑。通过`_resized_image_cache`缓存不同尺寸的图像，避免重复的缩放计算，显著提升了性能。`fit_to_window`方法自动计算最佳缩放比例，使图像适应窗口大小。渲染过程采用防抖技术，防止频繁重绘导致的性能问题。

```mermaid
flowchart TD
Start([开始重绘]) --> CheckImage{"图像存在?"}
CheckImage --> |否| End([结束])
CheckImage --> |是| CalculateZoom["计算缩放比例和偏移"]
CalculateZoom --> CheckCache{"缓存命中?"}
CheckCache --> |是| UseCache["使用缓存图像"]
CheckCache --> |否| ResizeImage["调整图像大小"]
ResizeImage --> UpdateCache["更新缓存"]
UpdateCache --> UseCache
UseCache --> DrawImage["在画布上绘制图像"]
DrawImage --> DrawInpainted["绘制修复图像(如果可用)"]
DrawInpainted --> DrawRegions["绘制文本区域"]
DrawRegions --> UpdateScroll["更新滚动区域"]
UpdateScroll --> End
```

**图示来源**
- [canvas_renderer_new.py](file://desktop-ui/components/canvas_renderer_new.py#L1-L350)

**组件来源**
- [canvas_renderer_new.py](file://desktop-ui/components/canvas_renderer_new.py#L1-L350)

### 上下文菜单组件分析

`ContextMenu`组件实现了右键菜单的条件显示策略。`EditorContextMenu`子类根据选中区域的数量动态调整菜单项：当未选中任何区域时，显示"新建文本框"等通用操作；当选中一个区域时，额外显示"编辑属性"、"复制样式"等操作；当选中多个区域时，则显示"删除选中的N个项目"等批量操作。这种基于上下文的动态菜单提升了用户体验。

```mermaid
flowchart TD
ShowMenu["显示菜单(event)"] --> GetSelection["获取选中数量"]
GetSelection --> CheckSelection{"选中数量 > 0?"}
CheckSelection --> |否| AddGeneral["添加通用菜单项"]
CheckSelection --> |是| AddRegion["添加区域菜单项"]
AddGeneral --> AddOCR["添加OCR识别"]
AddGeneral --> AddTranslate["添加翻译"]
AddGeneral --> AddSeparator["添加分隔符"]
AddGeneral --> AddRefresh["添加刷新视图"]
AddRegion --> AddOCR
AddRegion --> AddTranslate
AddRegion --> AddSeparator
AddRegion --> CheckCount{"数量 == 1?"}
CheckCount --> |是| AddEdit["添加编辑属性"]
CheckCount --> |是| AddCopyStyle["添加复制样式"]
CheckCount --> |是| AddPasteStyle["添加粘贴样式"]
CheckCount --> |是| AddSeparator2["添加分隔符"]
CheckCount --> AddDelete["添加删除项"]
AddDelete --> End["弹出菜单"]
```

**图示来源**
- [context_menu.py](file://desktop-ui/components/context_menu.py#L1-L87)

**组件来源**
- [context_menu.py](file://desktop-ui/components/context_menu.py#L1-L87)

## 依赖关系分析

各组件之间通过明确的接口进行交互，形成了清晰的依赖关系网络。`PropertyPanel`和`ContextMenu`等UI组件依赖`ConfigService`、`OCRService`等服务层组件获取配置和执行业务逻辑。服务层组件又依赖底层的数据模型（如配置文件、环境变量）。这种分层依赖结构确保了系统的可维护性和可测试性。

```mermaid
graph TD
A[FileListFrame] --> B[ConfigService]
C[PropertyPanel] --> B
C --> D[OCRService]
C --> E[TranslationService]
F[ProgressDialog] --> G[ProgressManager]
H[CanvasRenderer] --> I[TransformService]
J[ContextMenu] --> D
J --> E
B --> K[配置文件]
B --> L[环境变量]
D --> M[OCR模型]
E --> N[翻译API]
```

**图示来源**
- [config_service.py](file://desktop-ui/services/config_service.py#L1-L303)
- [property_panel.py](file://desktop-ui/components/property_panel.py#L1-L641)
- [context_menu.py](file://desktop-ui/components/context_menu.py#L1-L87)

**组件来源**
- [config_service.py](file://desktop-ui/services/config_service.py#L1-L303)
- [property_panel.py](file://desktop-ui/components/property_panel.py#L1-L641)
- [context_menu.py](file://desktop-ui/components/context_menu.py#L1-L87)