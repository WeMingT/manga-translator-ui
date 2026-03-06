def apply_reference_ui_style(self):
    """主界面局部样式：参考深色侧边栏 + 卡片化布局。"""
    self.setStyleSheet(
        """
            #main_view_root {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 #0A111C, stop:0.55 #101B2A, stop:1 #1A263A);
            }
            #main_view_root QLabel, #main_view_root QCheckBox {
                color: #D2E2F8;
            }
            #main_view_root QGroupBox {
                background: rgba(14, 23, 36, 0.88);
                border: 1px solid rgba(136, 163, 198, 0.24);
                border-radius: 10px;
                margin-top: 10px;
                padding: 10px;
                font-weight: 600;
            }
            #main_view_root QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 7px;
                margin-left: 8px;
                color: #C9DCF4;
                background: rgba(14, 23, 36, 0.88);
            }

            #main_view_splitter::handle:horizontal {
                background-color: rgba(160, 176, 196, 0.18);
                width: 2px;
            }
            #main_view_splitter::handle:horizontal:hover {
                background-color: rgba(95, 156, 255, 0.45);
            }

            #sidebar_panel {
                background: rgba(8, 14, 24, 0.92);
                border-right: 1px solid rgba(152, 171, 198, 0.2);
            }
            #sidebar_brand {
                color: #D8E7FB;
                font-size: 15px;
                font-weight: 700;
                padding: 8px 6px 10px 6px;
            }
            #sidebar_divider {
                background: rgba(170, 188, 214, 0.24);
                max-height: 1px;
                border: none;
                margin: 6px 2px;
            }
            #sidebar_group_label {
                color: #84A0C3;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 0.6px;
                padding: 8px 6px 2px 6px;
            }

            QPushButton[navButton="true"], QPushButton[navActionButton="true"] {
                background: transparent;
                color: #D9E8FD;
                border: 1px solid transparent;
                border-radius: 8px;
                text-align: left;
                padding: 10px 12px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton[navButton="true"]:hover, QPushButton[navActionButton="true"]:hover {
                background: rgba(43, 72, 111, 0.45);
                border-color: rgba(116, 154, 210, 0.42);
            }
            QPushButton[navButton="true"]:checked {
                background: rgba(57, 97, 147, 0.65);
                border-color: rgba(118, 172, 247, 0.78);
                color: #EAF4FF;
                font-weight: 600;
            }

            #content_panel {
                background: transparent;
            }
            #content_vertical_splitter::handle:vertical {
                background-color: rgba(160, 176, 196, 0.16);
                height: 2px;
            }
            #content_vertical_splitter::handle:vertical:hover {
                background-color: rgba(95, 156, 255, 0.45);
            }

            #header_card, #section_card, #log_container {
                background: rgba(17, 27, 42, 0.9);
                border: 1px solid rgba(136, 163, 198, 0.2);
                border-radius: 12px;
            }
            QGroupBox#section_card::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                margin-left: 10px;
                color: #D5E7FF;
                font-weight: 700;
                background: rgba(17, 27, 42, 0.9);
            }
            #page_title {
                color: #EAF3FF;
                font-size: 17px;
                font-weight: 700;
            }
            #page_subtitle {
                color: #9CB6D4;
                font-size: 12px;
            }
            #row_label {
                color: #C5D8F0;
                font-size: 12px;
                font-weight: 600;
            }

            #translation_file_list, #asset_list {
                background: rgba(8, 14, 24, 0.72);
                border: 1px solid rgba(133, 156, 186, 0.3);
                border-radius: 10px;
                color: #D9E8FD;
                padding: 4px;
            }
            #translation_file_list::item, #asset_list::item {
                padding: 8px 10px;
                border-radius: 6px;
            }
            #translation_file_list::item:hover, #asset_list::item:hover {
                background: rgba(64, 99, 145, 0.34);
            }
            #translation_file_list::item:selected, #asset_list::item:selected {
                background: rgba(74, 130, 200, 0.52);
                color: #EEF7FF;
            }




            QLineEdit, QComboBox {
                background: rgba(12, 20, 32, 0.85);
                border: 1px solid rgba(133, 156, 186, 0.42);
                border-radius: 8px;
                color: #D9E8FD;
                padding: 7px 10px;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: rgba(94, 160, 248, 0.9);
            }
            QComboBox QAbstractItemView {
                background: #0E1A2A;
                color: #D9E8FD;
                border: 1px solid rgba(133, 156, 186, 0.42);
                selection-background-color: rgba(74, 130, 200, 0.52);
                selection-color: #EEF7FF;
            }

            QPushButton {
                background: rgba(50, 86, 132, 0.84);
                border: 1px solid rgba(108, 154, 214, 0.62);
                border-radius: 8px;
                color: #EAF4FF;
                padding: 8px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(63, 104, 157, 0.95);
            }
            QPushButton:pressed {
                background: rgba(42, 72, 114, 0.95);
            }
            QPushButton[chipButton="true"] {
                background: rgba(34, 58, 90, 0.78);
                border: 1px solid rgba(104, 141, 192, 0.5);
                color: #D4E6FD;
                font-weight: 500;
                padding: 7px 10px;
            }
            QPushButton[chipButton="true"]:hover {
                background: rgba(50, 78, 116, 0.9);
            }
            #mode_shortcut_button {
                text-align: left;
                padding: 9px 12px;
            }
            #start_translation_button {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #2E8BFF, stop:1 #4EA0FF);
                border: 1px solid rgba(140, 198, 255, 0.9);
                color: #F5FAFF;
                font-size: 14px;
                font-weight: 700;
            }
            #start_translation_button:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #3A95FF, stop:1 #63ACFF);
            }

            QTabWidget::pane {
                border: 1px solid rgba(136, 163, 198, 0.2);
                border-radius: 10px;
                background: rgba(15, 24, 38, 0.92);
                padding: 2px;
            }
            QTabBar::tab {
                background: rgba(25, 40, 62, 0.8);
                border: 1px solid rgba(88, 120, 162, 0.36);
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                color: #AEC4DF;
                padding: 9px 16px;
                margin-right: 3px;
                font-weight: 600;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(70, 110, 165, 0.9), stop:1 rgba(54, 92, 140, 0.82));
                color: #ECF5FF;
                border-color: rgba(120, 175, 247, 0.72);
            }
            QTabBar::tab:hover:!selected {
                background: rgba(40, 68, 102, 0.9);
                color: #D5E7FF;
            }

            /* --- 设置页面专用样式 --- */
            #settings_scroll_area {
                background: transparent;
                border: none;
            }
            #settings_scroll_content {
                background: transparent;
            }

            /* 主分隔线标题 */
            #settings_divider_accent {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #5EA0F8, stop:1 #3B7CE0);
                border-radius: 2px;
                border: none;
            }
            #settings_divider_title {
                color: #C8DDFA;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1.2px;
            }
            #settings_divider_line {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 rgba(94, 160, 248, 0.4), stop:1 rgba(94, 160, 248, 0.05));
                max-height: 1px;
                border: none;
            }

            /* 子分隔线标题 */
            #settings_divider_dot {
                color: #6BA3E8;
                font-size: 8px;
            }
            #settings_divider_sub_title {
                color: #9BBCE0;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            #settings_divider_sub_line {
                background: rgba(155, 188, 224, 0.15);
                max-height: 1px;
                border: none;
            }

            /* 设置表单内的标签美化 */
            #settings_scroll_content QLabel {
                color: #BDD2EC;
                font-size: 12px;
                padding: 2px 0px;
                background: transparent;
            }

            /* 设置表单内控件微调 */
            #settings_scroll_content QLineEdit,
            #settings_scroll_content QComboBox {
                background: rgba(10, 17, 28, 0.9);
                border: 1px solid rgba(100, 135, 180, 0.35);
                border-radius: 7px;
                color: #D9E8FD;
                padding: 7px 10px;
                min-height: 20px;
            }
            #settings_scroll_content QLineEdit:focus,
            #settings_scroll_content QComboBox:focus {
                border-color: rgba(94, 160, 248, 0.85);
                background: rgba(14, 22, 36, 0.95);
            }
            #settings_scroll_content QLineEdit:hover,
            #settings_scroll_content QComboBox:hover {
                border-color: rgba(130, 170, 220, 0.55);
            }
            #settings_scroll_content QCheckBox {
                spacing: 8px;
                color: #BDD2EC;
            }
            #settings_scroll_content QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid rgba(100, 135, 180, 0.5);
                background: rgba(10, 17, 28, 0.9);
            }
            #settings_scroll_content QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 #4A8EE0, stop:1 #3672C4);
                border-color: rgba(120, 175, 247, 0.8);
            }
            #settings_scroll_content QCheckBox::indicator:hover {
                border-color: rgba(130, 170, 220, 0.65);
            }

            /* 设置表单标签 */
            #settings_form_label {
                color: #C5D8F0;
                font-size: 12px;
                font-weight: 500;
                padding: 4px 0px;
                background: transparent;
            }

            /* 设置页内按钮 */
            #settings_scroll_content QPushButton {
                background: rgba(40, 68, 105, 0.75);
                border: 1px solid rgba(104, 141, 192, 0.45);
                color: #D4E6FD;
                font-weight: 500;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 12px;
            }
            #settings_scroll_content QPushButton:hover {
                background: rgba(55, 88, 130, 0.9);
                border-color: rgba(120, 165, 220, 0.6);
            }

            /* 右侧描述面板 */
            #settings_desc_panel {
                background: rgba(12, 20, 32, 0.92);
                border: 1px solid rgba(136, 163, 198, 0.2);
                border-radius: 10px;
            }
            #settings_desc_header {
                color: #C8DDFA;
                font-size: 14px;
                font-weight: 700;
            }
            #settings_desc_divider {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 rgba(94, 160, 248, 0.5), stop:1 rgba(94, 160, 248, 0.05));
                max-height: 1px;
                border: none;
            }
            #settings_desc_name {
                color: #E8F2FF;
                font-size: 15px;
                font-weight: 700;
                padding-top: 4px;
            }
            #settings_desc_key {
                color: #6B8CB5;
                font-size: 11px;
                font-family: "Consolas", "Microsoft YaHei UI", monospace;
                padding: 2px 0px;
            }
            #settings_desc_text {
                color: #B8CBE0;
                font-size: 13px;
                line-height: 1.6;
                padding: 6px 0px;
            }

            /* settings splitter handle */
            #settings_body_splitter::handle:horizontal {
                background-color: rgba(160, 176, 196, 0.15);
                width: 2px;
            }
            #settings_body_splitter::handle:horizontal:hover {
                background-color: rgba(95, 156, 255, 0.45);
            }

            QScrollBar:vertical, QScrollBar:horizontal {
                background: rgba(11, 18, 29, 0.72);
                border: none;
                border-radius: 6px;
            }
            QScrollBar:vertical {
                width: 10px;
            }
            QScrollBar:horizontal {
                height: 10px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: rgba(125, 151, 186, 0.45);
                border-radius: 6px;
                min-height: 24px;
                min-width: 24px;
            }
            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                background: rgba(145, 176, 217, 0.65);
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                width: 0px;
                height: 0px;
            }
        """
    )
