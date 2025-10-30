#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试导入问题"""

import sys
import os

# 添加desktop_qt_ui到sys.path
desktop_qt_ui_dir = os.path.abspath("desktop_qt_ui")
sys.path.insert(0, desktop_qt_ui_dir)

print(f"desktop_qt_ui_dir: {desktop_qt_ui_dir}")
print(f"sys.path[0]: {sys.path[0]}")
print(f"当前目录: {os.getcwd()}")
print()

try:
    from utils.resource_helper import resource_path
    print("✓ 导入成功: from utils.resource_helper import resource_path")
except ModuleNotFoundError as e:
    print(f"✗ 导入失败: {e}")


