import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from utils.resource_helper import resource_path
from utils.wheel_filter import NoWheelComboBox as QComboBox
from widgets.file_list_view import FileListView


_SETTINGS_TAB_LAYOUT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "locales", "settings_tab_layout.json"
)


def _load_reclassify_settings_layout():
    """从 locales/settings_tab_layout.json 加载设置页分类排序布局。"""
    try:
        with open(_SETTINGS_TAB_LAYOUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("tabs", [])
    except Exception:
        return []


def create_left_sidebar(self) -> QWidget:
    sidebar = QWidget()
    sidebar.setObjectName("sidebar_panel")
    sidebar.setMinimumWidth(210)
    sidebar.setMaximumWidth(260)
    sidebar_layout = QVBoxLayout(sidebar)
    sidebar_layout.setContentsMargins(12, 14, 12, 14)
    sidebar_layout.setSpacing(6)

    self.sidebar_brand_label = QLabel("Manga Translator")
    self.sidebar_brand_label.setObjectName("sidebar_brand")
    sidebar_layout.addWidget(self.sidebar_brand_label)

    self.sidebar_divider_top = QFrame()
    self.sidebar_divider_top.setFrameShape(QFrame.Shape.HLine)
    self.sidebar_divider_top.setObjectName("sidebar_divider")
    sidebar_layout.addWidget(self.sidebar_divider_top)

    self.sidebar_start_label = QLabel(self._t("Start Translation"))
    self.sidebar_start_label.setObjectName("sidebar_group_label")
    sidebar_layout.addWidget(self.sidebar_start_label)

    self.nav_translation_button = QPushButton(self._t("Translation Interface"))
    self.nav_translation_button.setProperty("navButton", True)
    self.nav_translation_button.setCheckable(True)
    sidebar_layout.addWidget(self.nav_translation_button)

    self.sidebar_divider_middle = QFrame()
    self.sidebar_divider_middle.setFrameShape(QFrame.Shape.HLine)
    self.sidebar_divider_middle.setObjectName("sidebar_divider")
    sidebar_layout.addWidget(self.sidebar_divider_middle)

    self.sidebar_settings_label = QLabel(self._t("Settings"))
    self.sidebar_settings_label.setObjectName("sidebar_group_label")
    sidebar_layout.addWidget(self.sidebar_settings_label)

    self.nav_settings_button = QPushButton(self._t("Settings"))
    self.nav_settings_button.setProperty("navButton", True)
    self.nav_settings_button.setCheckable(True)
    sidebar_layout.addWidget(self.nav_settings_button)

    self.nav_env_button = QPushButton(self._t("API Management"))
    self.nav_env_button.setProperty("navButton", True)
    self.nav_env_button.setCheckable(True)
    sidebar_layout.addWidget(self.nav_env_button)

    self.sidebar_tools_label = QLabel(self._t("Data Management"))
    self.sidebar_tools_label.setObjectName("sidebar_group_label")
    sidebar_layout.addWidget(self.sidebar_tools_label)

    self.nav_prompt_button = QPushButton(self._t("Prompt Management"))
    self.nav_prompt_button.setProperty("navButton", True)
    self.nav_prompt_button.setCheckable(True)
    sidebar_layout.addWidget(self.nav_prompt_button)

    self.nav_font_button = QPushButton(self._t("Font Management"))
    self.nav_font_button.setProperty("navButton", True)
    self.nav_font_button.setCheckable(True)
    sidebar_layout.addWidget(self.nav_font_button)

    sidebar_layout.addStretch()

    self.sidebar_divider_bottom = QFrame()
    self.sidebar_divider_bottom.setFrameShape(QFrame.Shape.HLine)
    self.sidebar_divider_bottom.setObjectName("sidebar_divider")
    sidebar_layout.addWidget(self.sidebar_divider_bottom)

    self.sidebar_editor_label = QLabel(self._t("Editor"))
    self.sidebar_editor_label.setObjectName("sidebar_group_label")
    sidebar_layout.addWidget(self.sidebar_editor_label)

    self.nav_editor_button = QPushButton(self._t("Editor View"))
    self.nav_editor_button.setProperty("navActionButton", True)
    sidebar_layout.addWidget(self.nav_editor_button)

    self.nav_button_group = QButtonGroup(self)
    self.nav_button_group.setExclusive(True)
    for button in [
        self.nav_translation_button,
        self.nav_settings_button,
        self.nav_env_button,
        self.nav_prompt_button,
        self.nav_font_button,
    ]:
        self.nav_button_group.addButton(button)

    self.page_nav_buttons = {
        "translation": self.nav_translation_button,
        "settings": self.nav_settings_button,
        "env": self.nav_env_button,
        "prompts": self.nav_prompt_button,
        "fonts": self.nav_font_button,
    }

    self.nav_translation_button.clicked.connect(lambda: self._switch_content_page("translation"))
    self.nav_editor_button.clicked.connect(self._on_nav_editor_clicked)
    self.nav_settings_button.clicked.connect(lambda: self._switch_content_page("settings"))
    self.nav_env_button.clicked.connect(lambda: self._switch_content_page("env"))
    self.nav_prompt_button.clicked.connect(self._on_nav_prompt_clicked)
    self.nav_font_button.clicked.connect(self._on_nav_font_clicked)

    self.nav_translation_button.setChecked(True)
    return sidebar


def create_translation_page(self) -> QWidget:
    page = QWidget()
    page.setObjectName("content_page_translation")
    page_layout = QVBoxLayout(page)
    page_layout.setContentsMargins(18, 16, 18, 14)
    page_layout.setSpacing(12)

    header_card = QWidget()
    header_card.setObjectName("header_card")
    header_layout = QVBoxLayout(header_card)
    header_layout.setContentsMargins(16, 14, 16, 14)
    header_layout.setSpacing(4)
    self.translation_page_title = QLabel(self._t("Normal Translation"))
    self.translation_page_title.setObjectName("page_title")
    self.translation_page_subtitle = QLabel(
        self._t("Tip: Standard translation pipeline with detection, OCR, translation and rendering")
    )
    self.translation_page_subtitle.setObjectName("page_subtitle")
    self.translation_page_subtitle.setWordWrap(True)
    header_layout.addWidget(self.translation_page_title)
    header_layout.addWidget(self.translation_page_subtitle)
    page_layout.addWidget(header_card)

    self.translation_input_card = QGroupBox(self._t("Input Files"))
    self.translation_input_card.setObjectName("section_card")
    input_layout = QVBoxLayout(self.translation_input_card)
    input_layout.setContentsMargins(12, 14, 12, 12)
    input_layout.setSpacing(10)

    file_button_widget = QWidget()
    file_button_widget.setObjectName("inline_toolbar")
    file_buttons_layout = QHBoxLayout(file_button_widget)
    file_buttons_layout.setContentsMargins(0, 0, 0, 0)
    file_buttons_layout.setSpacing(8)
    self.add_files_button = QPushButton(self._t("Add Files"))
    self.add_folder_button = QPushButton(self._t("Add Folder"))
    self.clear_list_button = QPushButton(self._t("Clear List"))
    self.add_files_button.setProperty("chipButton", True)
    self.add_folder_button.setProperty("chipButton", True)
    self.clear_list_button.setProperty("chipButton", True)
    file_buttons_layout.addWidget(self.add_files_button)
    file_buttons_layout.addWidget(self.add_folder_button)
    file_buttons_layout.addWidget(self.clear_list_button)
    file_buttons_layout.addStretch()
    input_layout.addWidget(file_button_widget)

    self.file_list = FileListView(None, self)
    self.file_list.setObjectName("translation_file_list")
    input_layout.addWidget(self.file_list, 1)
    page_layout.addWidget(self.translation_input_card, 1)

    self.translation_task_card = QGroupBox(self._t("Translation Task"))
    self.translation_task_card.setObjectName("section_card")
    task_layout = QVBoxLayout(self.translation_task_card)
    task_layout.setContentsMargins(12, 14, 12, 12)
    task_layout.setSpacing(10)

    self.output_folder_label = QLabel(self._t("Output Directory:"))
    self.output_folder_label.setObjectName("row_label")
    task_layout.addWidget(self.output_folder_label)

    output_folder_widget = QWidget()
    output_folder_widget.setObjectName("inline_toolbar")
    output_folder_layout = QHBoxLayout(output_folder_widget)
    output_folder_layout.setContentsMargins(0, 0, 0, 0)
    output_folder_layout.setSpacing(8)
    self.output_folder_input = QLineEdit()
    self.output_folder_input.setPlaceholderText(self._t("Select or drag output folder..."))
    self.browse_button = QPushButton(self._t("Browse..."))
    self.open_button = QPushButton(self._t("Open"))
    self.browse_button.setProperty("chipButton", True)
    self.open_button.setProperty("chipButton", True)
    output_folder_layout.addWidget(self.output_folder_input)
    output_folder_layout.addWidget(self.browse_button)
    output_folder_layout.addWidget(self.open_button)
    task_layout.addWidget(output_folder_widget)

    self.workflow_mode_hint_label = QLabel(
        self._t("Choose translation workflow mode before starting the task.")
    )
    self.workflow_mode_hint_label.setObjectName("page_subtitle")
    self.workflow_mode_hint_label.setWordWrap(True)
    task_layout.addWidget(self.workflow_mode_hint_label)

    self.workflow_mode_label = QLabel(self._t("Translation Workflow Mode:"))
    self.workflow_mode_label.setObjectName("row_label")
    task_layout.addWidget(self.workflow_mode_label)

    self.workflow_mode_combo = QComboBox()
    self.workflow_mode_combo.addItems([
        self._t("Normal Translation"),
        self._t("Export Translation"),
        self._t("Export Original Text"),
        self._t("Import Translation and Render"),
        self._t("Colorize Only"),
        self._t("Upscale Only"),
        self._t("Inpaint Only"),
        self._t("Replace Translation")
    ])
    self.workflow_mode_combo.currentIndexChanged.connect(self._on_workflow_mode_changed)
    task_layout.addWidget(self.workflow_mode_combo)

    self.start_button = QPushButton(self._t("Start Translation"))
    self.start_button.setObjectName("start_translation_button")
    self.start_button.setFixedHeight(44)
    task_layout.addWidget(self.start_button)
    page_layout.addWidget(self.translation_task_card)

    self.add_files_button.clicked.connect(self._trigger_add_files)
    self.add_folder_button.clicked.connect(self.controller.add_folder)
    self.clear_list_button.clicked.connect(self.controller.clear_file_list)
    self.file_list.file_remove_requested.connect(self.controller.remove_file)
    self.browse_button.clicked.connect(self.controller.select_output_folder)
    self.open_button.clicked.connect(self.controller.open_output_folder)
    self.start_button.clicked.connect(self.controller.start_backend_task)

    return page


def create_settings_page(self) -> QWidget:
    page = QWidget()
    page.setObjectName("content_page_settings")
    page_layout = QVBoxLayout(page)
    page_layout.setContentsMargins(18, 16, 18, 14)
    page_layout.setSpacing(12)

    # Header card with title + config IO buttons
    header_card = QWidget()
    header_card.setObjectName("header_card")
    header_layout = QHBoxLayout(header_card)
    header_layout.setContentsMargins(16, 12, 16, 12)
    header_layout.setSpacing(8)

    title_col = QVBoxLayout()
    title_col.setSpacing(2)
    self.settings_page_title = QLabel(self._t("Settings Page Title"))
    self.settings_page_title.setObjectName("page_title")
    self.settings_page_subtitle = QLabel(
        self._t("Settings Page Subtitle")
    )
    self.settings_page_subtitle.setObjectName("page_subtitle")
    self.settings_page_subtitle.setWordWrap(True)
    title_col.addWidget(self.settings_page_title)
    title_col.addWidget(self.settings_page_subtitle)
    header_layout.addLayout(title_col, 1)

    self.export_config_button = QPushButton(self._t("Export Config"))
    self.import_config_button = QPushButton(self._t("Import Config"))
    self.export_config_button.setProperty("chipButton", True)
    self.import_config_button.setProperty("chipButton", True)
    header_layout.addWidget(self.export_config_button)
    header_layout.addWidget(self.import_config_button)
    page_layout.addWidget(header_card)

    self.export_config_button.clicked.connect(self.controller.export_config)
    self.import_config_button.clicked.connect(self.controller.import_config)

    # --- 主体区域：左侧 tabs + 右侧描述面板 ---
    settings_body_splitter = QSplitter(Qt.Orientation.Horizontal)
    settings_body_splitter.setObjectName("settings_body_splitter")
    page_layout.addWidget(settings_body_splitter, 1)

    self.settings_tabs = QTabWidget()
    self.settings_tabs.setObjectName("settings_tabs")
    settings_body_splitter.addWidget(self.settings_tabs)

    # 右侧描述面板
    desc_panel = QWidget()
    desc_panel.setObjectName("settings_desc_panel")
    desc_panel_layout = QVBoxLayout(desc_panel)
    desc_panel_layout.setContentsMargins(16, 16, 16, 16)
    desc_panel_layout.setSpacing(12)

    desc_header_label = QLabel(self._t("Settings Desc Header"))
    desc_header_label.setObjectName("settings_desc_header")
    desc_panel_layout.addWidget(desc_header_label)

    desc_divider = QFrame()
    desc_divider.setFrameShape(QFrame.Shape.HLine)
    desc_divider.setObjectName("settings_desc_divider")
    desc_panel_layout.addWidget(desc_divider)

    self.settings_desc_name = QLabel("")
    self.settings_desc_name.setObjectName("settings_desc_name")
    self.settings_desc_name.setWordWrap(True)
    desc_panel_layout.addWidget(self.settings_desc_name)

    self.settings_desc_key = QLabel("")
    self.settings_desc_key.setObjectName("settings_desc_key")
    self.settings_desc_key.setWordWrap(True)
    self.settings_desc_key.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    desc_panel_layout.addWidget(self.settings_desc_key)

    self.settings_desc_text = QLabel(self._t("Settings Desc Placeholder"))
    self.settings_desc_text.setObjectName("settings_desc_text")
    self.settings_desc_text.setWordWrap(True)
    self.settings_desc_text.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    desc_panel_layout.addWidget(self.settings_desc_text, 1)

    settings_body_splitter.addWidget(desc_panel)

    settings_body_splitter.setStretchFactor(0, 3)
    settings_body_splitter.setStretchFactor(1, 1)
    settings_body_splitter.setSizes([700, 280])
    settings_body_splitter.setCollapsible(0, False)
    settings_body_splitter.setCollapsible(1, True)

    self.tab_frames = {}
    self.settings_tab_layout = _load_reclassify_settings_layout()
    self._settings_tabs_use_reclassify = bool(self.settings_tab_layout)
    self.settings_tab_title_keys = []

    if self._settings_tabs_use_reclassify:
        for tab in self.settings_tab_layout:
            tab_id = tab["id"]
            tab_title = tab["title"]

            tab_content_widget = QWidget()
            tab_layout = QVBoxLayout(tab_content_widget)
            tab_layout.setContentsMargins(0, 0, 0, 0)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setObjectName("settings_scroll_area")
            scroll_content = QWidget()
            scroll_content.setObjectName("settings_scroll_content")
            scroll.setWidget(scroll_content)

            form = QFormLayout(scroll_content)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
            form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            form.setHorizontalSpacing(16)
            form.setVerticalSpacing(12)
            form.setContentsMargins(16, 14, 16, 14)

            tab_layout.addWidget(scroll)
            self.settings_tabs.addTab(tab_content_widget, tab_title)
            self.settings_tab_title_keys.append(tab_title)
            self.tab_frames[tab_id] = scroll_content
    else:
        tabs_config = [
            ("Application Settings", self._t("Application Settings")),
            ("Basic Settings", self._t("Basic Settings")),
            ("Advanced Settings", self._t("Advanced Settings")),
            ("Options", self._t("Options")),
        ]
        for tab_key, tab_display_name in tabs_config:
            tab_content_widget = QWidget()
            tab_layout = QVBoxLayout(tab_content_widget)
            tab_layout.setContentsMargins(0, 0, 0, 0)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_content = QWidget()
            scroll.setWidget(scroll_content)

            form = QFormLayout(scroll_content)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
            form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            form.setHorizontalSpacing(10)
            form.setVerticalSpacing(8)

            tab_layout.addWidget(scroll)
            self.settings_tabs.addTab(tab_content_widget, tab_display_name)
            self.settings_tab_title_keys.append(tab_key)
            self.tab_frames[tab_key] = scroll_content

    self._populate_theme_combo()
    self._populate_language_combo()
    return page


def create_env_page(self) -> QWidget:
    page = QWidget()
    page.setObjectName("content_page_env")
    page_layout = QVBoxLayout(page)
    page_layout.setContentsMargins(18, 16, 18, 14)
    page_layout.setSpacing(12)

    # --- Header Card ---
    header_card = QWidget()
    header_card.setObjectName("header_card")
    header_layout = QVBoxLayout(header_card)
    header_layout.setContentsMargins(16, 12, 16, 12)
    header_layout.setSpacing(8)

    title_col = QVBoxLayout()
    title_col.setSpacing(2)
    self.env_page_title_label = QLabel(self._t("API Management"))
    self.env_page_title_label.setObjectName("page_title")
    self.env_page_subtitle_label = QLabel(
        self._t("Manage API keys and environment variables for each translator")
    )
    self.env_page_subtitle_label.setObjectName("page_subtitle")
    self.env_page_subtitle_label.setWordWrap(True)
    title_col.addWidget(self.env_page_title_label)
    title_col.addWidget(self.env_page_subtitle_label)
    header_layout.addLayout(title_col)

    self.env_preset_layout = QHBoxLayout()
    self.env_preset_layout.setSpacing(8)
    header_layout.addLayout(self.env_preset_layout)

    page_layout.addWidget(header_card)

    # --- Native QTabWidget Setup ---
    self.env_tab_widget = QTabWidget()
    self.env_tab_widget.setObjectName("settings_tab_widget")
    
    # 1. Translation Tab Content
    self.env_translation_page = QWidget()
    self.env_translation_layout = QVBoxLayout(self.env_translation_page)
    self.env_translation_layout.setContentsMargins(0, 0, 0, 0)
    
    env_scroll = QScrollArea()
    env_scroll.setWidgetResizable(True)
    env_scroll.setObjectName("settings_scroll_area")
    
    self.env_group_container = QWidget()
    self.env_group_container.setObjectName("settings_scroll_content")
    self.env_group_container_layout = QVBoxLayout(self.env_group_container)
    self.env_group_container_layout.setContentsMargins(0, 0, 0, 0)
    self.env_group_container_layout.setSpacing(12)
    env_scroll.setWidget(self.env_group_container)
    self.env_translation_layout.addWidget(env_scroll)
    
    # 2. OCR Tab Content
    self.env_ocr_page = QWidget()
    self.env_ocr_layout = QVBoxLayout(self.env_ocr_page)
    self.env_ocr_layout.setContentsMargins(0, 0, 0, 0)
    
    ocr_scroll = QScrollArea()
    ocr_scroll.setWidgetResizable(True)
    ocr_scroll.setObjectName("settings_scroll_area")
    self.ocr_container = QWidget()
    self.ocr_container.setObjectName("settings_scroll_content")
    self.ocr_container_layout = QVBoxLayout(self.ocr_container)
    self.ocr_container_layout.setContentsMargins(0, 0, 0, 0)
    self.ocr_container_layout.setSpacing(12)
    ocr_scroll.setWidget(self.ocr_container)
    self.env_ocr_layout.addWidget(ocr_scroll)
    
    # 3. Colorization Tab Content
    self.env_color_page = QWidget()
    self.env_color_layout = QVBoxLayout(self.env_color_page)
    self.env_color_layout.setContentsMargins(0, 0, 0, 0)
    
    color_scroll = QScrollArea()
    color_scroll.setWidgetResizable(True)
    color_scroll.setObjectName("settings_scroll_area")
    self.color_container = QWidget()
    self.color_container.setObjectName("settings_scroll_content")
    self.color_container_layout = QVBoxLayout(self.color_container)
    self.color_container_layout.setContentsMargins(0, 0, 0, 0)
    self.color_container_layout.setSpacing(12)
    color_scroll.setWidget(self.color_container)
    self.env_color_layout.addWidget(color_scroll)
    
    # 4. Render Tab Content
    self.env_render_page = QWidget()
    self.env_render_layout = QVBoxLayout(self.env_render_page)
    self.env_render_layout.setContentsMargins(0, 0, 0, 0)
    
    render_scroll = QScrollArea()
    render_scroll.setWidgetResizable(True)
    render_scroll.setObjectName("settings_scroll_area")
    self.render_container = QWidget()
    self.render_container.setObjectName("settings_scroll_content")
    self.render_container_layout = QVBoxLayout(self.render_container)
    self.render_container_layout.setContentsMargins(0, 0, 0, 0)
    self.render_container_layout.setSpacing(12)
    render_scroll.setWidget(self.render_container)
    self.env_render_layout.addWidget(render_scroll)
    
    self.env_tab_widget.addTab(self.env_translation_page, self._t("Translation"))
    self.env_tab_widget.addTab(self.env_ocr_page, self._t("OCR"))
    self.env_tab_widget.addTab(self.env_color_page, self._t("Colorization"))
    self.env_tab_widget.addTab(self.env_render_page, self._t("Render"))
    
    page_layout.addWidget(self.env_tab_widget, 1)
    return page


def create_prompt_page(self) -> QWidget:
    page = QWidget()
    page.setObjectName("content_page_prompts")
    page_layout = QVBoxLayout(page)
    page_layout.setContentsMargins(18, 16, 18, 14)
    page_layout.setSpacing(12)

    self.prompt_card = QGroupBox(self._t("Prompt Management"))
    self.prompt_card.setObjectName("section_card")
    prompt_card_layout = QVBoxLayout(self.prompt_card)
    prompt_card_layout.setContentsMargins(12, 14, 12, 12)
    prompt_card_layout.setSpacing(10)

    self.prompt_page_title_label = QLabel(self._t("Prompt Management"))
    self.prompt_page_title_label.setObjectName("page_title")
    prompt_card_layout.addWidget(self.prompt_page_title_label)

    self.prompt_list_widget = QListWidget()
    self.prompt_list_widget.setObjectName("asset_list")
    prompt_card_layout.addWidget(self.prompt_list_widget)

    button_row = QWidget()
    button_row.setObjectName("inline_toolbar")
    button_row_layout = QHBoxLayout(button_row)
    button_row_layout.setContentsMargins(0, 0, 0, 0)
    button_row_layout.setSpacing(8)
    self.prompt_refresh_button = QPushButton(self._t("Refresh"))
    self.prompt_open_dir_button = QPushButton(self._t("Open Directory"))
    self.prompt_apply_button = QPushButton(self._t("Apply Selected Prompt"))
    self.prompt_refresh_button.setProperty("chipButton", True)
    self.prompt_open_dir_button.setProperty("chipButton", True)
    self.prompt_apply_button.setProperty("chipButton", True)
    button_row_layout.addWidget(self.prompt_refresh_button)
    button_row_layout.addWidget(self.prompt_open_dir_button)
    button_row_layout.addWidget(self.prompt_apply_button)
    button_row_layout.addStretch()
    prompt_card_layout.addWidget(button_row)

    self.prompt_status_label = QLabel("")
    self.prompt_status_label.setObjectName("page_subtitle")
    self.prompt_status_label.setWordWrap(True)
    prompt_card_layout.addWidget(self.prompt_status_label)
    page_layout.addWidget(self.prompt_card)
    page_layout.addStretch()

    self.prompt_refresh_button.clicked.connect(self._refresh_prompt_manager)
    self.prompt_open_dir_button.clicked.connect(self.controller.open_dict_directory)
    self.prompt_apply_button.clicked.connect(self._apply_selected_prompt)
    self.prompt_list_widget.itemDoubleClicked.connect(lambda _: self._apply_selected_prompt())
    return page


def create_font_page(self) -> QWidget:
    page = QWidget()
    page.setObjectName("content_page_fonts")
    page_layout = QVBoxLayout(page)
    page_layout.setContentsMargins(18, 16, 18, 14)
    page_layout.setSpacing(12)

    self.font_card = QGroupBox(self._t("Font Management"))
    self.font_card.setObjectName("section_card")
    font_card_layout = QVBoxLayout(self.font_card)
    font_card_layout.setContentsMargins(12, 14, 12, 12)
    font_card_layout.setSpacing(10)

    self.font_page_title_label = QLabel(self._t("Font Management"))
    self.font_page_title_label.setObjectName("page_title")
    font_card_layout.addWidget(self.font_page_title_label)

    self.font_list_widget = QListWidget()
    self.font_list_widget.setObjectName("asset_list")
    font_card_layout.addWidget(self.font_list_widget)

    button_row = QWidget()
    button_row.setObjectName("inline_toolbar")
    button_row_layout = QHBoxLayout(button_row)
    button_row_layout.setContentsMargins(0, 0, 0, 0)
    button_row_layout.setSpacing(8)
    self.font_refresh_button = QPushButton(self._t("Refresh"))
    self.font_open_dir_button = QPushButton(self._t("Open Directory"))
    self.font_apply_button = QPushButton(self._t("Apply Selected Font"))
    self.font_refresh_button.setProperty("chipButton", True)
    self.font_open_dir_button.setProperty("chipButton", True)
    self.font_apply_button.setProperty("chipButton", True)
    button_row_layout.addWidget(self.font_refresh_button)
    button_row_layout.addWidget(self.font_open_dir_button)
    button_row_layout.addWidget(self.font_apply_button)
    button_row_layout.addStretch()
    font_card_layout.addWidget(button_row)

    self.font_status_label = QLabel("")
    self.font_status_label.setObjectName("page_subtitle")
    self.font_status_label.setWordWrap(True)
    font_card_layout.addWidget(self.font_status_label)
    page_layout.addWidget(self.font_card)
    page_layout.addStretch()

    self.font_refresh_button.clicked.connect(self._refresh_font_manager)
    self.font_open_dir_button.clicked.connect(self.controller.open_font_directory)
    self.font_apply_button.clicked.connect(self._apply_selected_font)
    self.font_list_widget.itemDoubleClicked.connect(lambda _: self._apply_selected_font())
    return page


def create_right_panel(self) -> QWidget:
    right_panel = QWidget()
    right_panel.setObjectName("content_panel")
    right_layout = QVBoxLayout(right_panel)
    right_layout.setContentsMargins(0, 0, 0, 0)

    right_splitter = QSplitter(Qt.Orientation.Vertical)
    right_splitter.setObjectName("content_vertical_splitter")
    right_layout.addWidget(right_splitter)

    self.content_stack = QStackedWidget()
    self.page_indexes = {}
    self.page_indexes["translation"] = self.content_stack.addWidget(self._create_translation_page())
    self.page_indexes["settings"] = self.content_stack.addWidget(self._create_settings_page())
    self.page_indexes["env"] = self.content_stack.addWidget(self._create_env_page())
    self.page_indexes["prompts"] = self.content_stack.addWidget(self._create_prompt_page())
    self.page_indexes["fonts"] = self.content_stack.addWidget(self._create_font_page())
    right_splitter.addWidget(self.content_stack)

    progress_container = QWidget()
    progress_container.setObjectName("log_container")
    progress_layout = QVBoxLayout(progress_container)
    progress_layout.setContentsMargins(12, 10, 12, 10)
    progress_layout.setSpacing(6)

    from PyQt6.QtWidgets import QProgressBar
    self.progress_bar = QProgressBar()
    self.progress_bar.setMinimum(0)
    self.progress_bar.setMaximum(100)
    self.progress_bar.setValue(0)
    self.progress_bar.setTextVisible(True)
    self.progress_bar.setFormat("0/0 (0%)")
    self.progress_bar.setFixedHeight(25)
    self.progress_bar.setStyleSheet("""
        QProgressBar {
            border: 1px solid rgba(140, 164, 192, 0.28);
            border-radius: 6px;
            text-align: center;
            background-color: rgba(12, 19, 30, 0.8);
            color: #B8CBE0;
        }
        QProgressBar::chunk {
            background-color: rgba(137, 157, 182, 0.55);
            border-radius: 6px;
        }
    """)
    progress_layout.addWidget(self.progress_bar)
    right_splitter.addWidget(progress_container)




    right_splitter.setStretchFactor(0, 3)
    right_splitter.setStretchFactor(1, 0)
    right_splitter.setSizes([760, 60])

    self._switch_content_page("translation")
    return right_panel


def switch_content_page(self, page_key: str):
    if not hasattr(self, "content_stack") or not hasattr(self, "page_indexes"):
        return
    target_index = self.page_indexes.get(page_key)
    if target_index is None:
        return
    self.content_stack.setCurrentIndex(target_index)

    if hasattr(self, "page_nav_buttons"):
        nav_button = self.page_nav_buttons.get(page_key)
        if nav_button and not nav_button.isChecked():
            nav_button.setChecked(True)


def on_nav_add_folder_clicked(self):
    self.controller.add_folder()
    self._switch_content_page("translation")


def on_nav_mode_clicked(self):
    self._switch_content_page("translation")
    if hasattr(self, "workflow_mode_combo"):
        self.workflow_mode_combo.setFocus()
        self.workflow_mode_combo.showPopup()


def on_nav_prompt_clicked(self):
    self._switch_content_page("prompts")
    self._refresh_prompt_manager()


def on_nav_editor_clicked(self):
    if hasattr(self, "editor_view_requested"):
        self.editor_view_requested.emit()


def on_nav_font_clicked(self):
    self._switch_content_page("fonts")
    self._refresh_font_manager()


def on_env_translator_combo_changed(self, display_name: str):
    if not display_name:
        return
    translator_combo = self.findChild(QComboBox, "translator.translator")
    if translator_combo and translator_combo.currentText() != display_name:
        translator_combo.setCurrentText(display_name)


def populate_theme_combo(self):
    if not hasattr(self, "theme_combo"):
        return
    config = self.config_service.get_config()
    theme_options = [
        ("light", self._t("Light")),
        ("dark", self._t("Dark")),
        ("gray", self._t("Gray")),
        ("system", self._t("Follow System")),
    ]
    self.theme_combo.blockSignals(True)
    self.theme_combo.clear()
    selected_index = 0
    for idx, (theme_key, theme_label) in enumerate(theme_options):
        self.theme_combo.addItem(theme_label, theme_key)
        if config.app.theme == theme_key:
            selected_index = idx
    self.theme_combo.setCurrentIndex(selected_index)
    self.theme_combo.blockSignals(False)


def populate_language_combo(self):
    if not hasattr(self, "language_combo"):
        return
    current_language = self.config_service.get_config().app.ui_language
    self.language_combo.blockSignals(True)
    self.language_combo.clear()
    if self.i18n:
        available_locales = self.i18n.get_available_locales()
        selected_index = 0
        for idx, (locale_code, locale_info) in enumerate(available_locales.items()):
            self.language_combo.addItem(locale_info.name, locale_code)
            if current_language == locale_code:
                selected_index = idx
        if self.language_combo.count() > 0:
            self.language_combo.setCurrentIndex(selected_index)
    self.language_combo.blockSignals(False)


def on_theme_combo_changed(self, index: int):
    if index < 0 or not hasattr(self, "theme_combo"):
        return
    theme_key = self.theme_combo.itemData(index)
    if theme_key:
        self.theme_change_requested.emit(theme_key)


def on_language_combo_changed(self, index: int):
    if index < 0 or not hasattr(self, "language_combo"):
        return
    locale_code = self.language_combo.itemData(index)
    if locale_code:
        self.language_change_requested.emit(locale_code)


def sync_env_translator_combo_selection(self, display_name: str):
    if not hasattr(self, "env_translator_combo"):
        return
    self.env_translator_combo.blockSignals(True)
    self.env_translator_combo.setCurrentText(display_name)
    self.env_translator_combo.blockSignals(False)


def refresh_prompt_manager(self):
    if not hasattr(self, "prompt_list_widget"):
        return
    prompt_files = self.controller.get_hq_prompt_options()
    selected_prompt_path = self.config_service.get_config().translator.high_quality_prompt_path
    selected_filename = os.path.basename(selected_prompt_path) if selected_prompt_path else ""

    self.prompt_list_widget.blockSignals(True)
    self.prompt_list_widget.clear()
    for prompt in prompt_files:
        self.prompt_list_widget.addItem(QListWidgetItem(prompt))
    self.prompt_list_widget.blockSignals(False)

    if selected_filename:
        matching_items = self.prompt_list_widget.findItems(selected_filename, Qt.MatchFlag.MatchExactly)
        if matching_items:
            self.prompt_list_widget.setCurrentItem(matching_items[0])
    self.prompt_status_label.setText(f"Found {len(prompt_files)} prompt files.")


def apply_selected_prompt(self):
    current_item = self.prompt_list_widget.currentItem() if hasattr(self, "prompt_list_widget") else None
    if not current_item:
        return
    filename = current_item.text().strip()
    if not filename:
        return
    selected_path = os.path.join("dict", filename).replace("\\", "/")
    self.setting_changed.emit("translator.high_quality_prompt_path", selected_path)
    self.prompt_status_label.setText(f"Current prompt: {filename}")


def refresh_font_manager(self):
    if not hasattr(self, "font_list_widget"):
        return
    font_files = []
    try:
        fonts_dir = resource_path("fonts")
        if os.path.isdir(fonts_dir):
            font_files = sorted([
                f for f in os.listdir(fonts_dir)
                if f.lower().endswith((".ttf", ".otf", ".ttc"))
            ])
    except Exception as e:
        print(f"Error scanning fonts directory: {e}")

    selected_font = self.config_service.get_config().render.font_path or ""
    self.font_list_widget.blockSignals(True)
    self.font_list_widget.clear()
    for font_name in font_files:
        self.font_list_widget.addItem(QListWidgetItem(font_name))
    self.font_list_widget.blockSignals(False)

    if selected_font:
        matching_items = self.font_list_widget.findItems(selected_font, Qt.MatchFlag.MatchExactly)
        if matching_items:
            self.font_list_widget.setCurrentItem(matching_items[0])
    self.font_status_label.setText(f"Found {len(font_files)} fonts.")


def apply_selected_font(self):
    current_item = self.font_list_widget.currentItem() if hasattr(self, "font_list_widget") else None
    if not current_item:
        return
    font_name = current_item.text().strip()
    if not font_name:
        return
    self.setting_changed.emit("render.font_path", font_name)
    self.font_status_label.setText(f"Current font: {font_name}")
