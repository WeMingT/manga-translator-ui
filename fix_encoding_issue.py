#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复E:\mit目录中的编码问题
Fix encoding issues in E:\mit directory
"""

import os

# 修复 utils/package_checker.py
package_checker_path = r"E:\mit\utils\package_checker.py"
if os.path.exists(package_checker_path):
    with open(package_checker_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换第66行
    old_line = "    with pathlib.Path(requirements_file).open() as reqfile:"
    new_line = "    with pathlib.Path(requirements_file).open(encoding='utf-8') as reqfile:"
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        with open(package_checker_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] Fixed: {package_checker_path}")
    else:
        print(f"[INFO] Already up-to-date: {package_checker_path}")
else:
    print(f"[ERROR] File not found: {package_checker_path}")

# 修复 requirements_gpu.txt
requirements_gpu_path = r"E:\mit\requirements_gpu.txt"
if os.path.exists(requirements_gpu_path):
    with open(requirements_gpu_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_url = "git+https://github.com/lucasb-eyer/pydensecrf.git"
    new_url = "git+https://gh-proxy.com/https://github.com/lucasb-eyer/pydensecrf.git"
    
    if old_url in content:
        content = content.replace(old_url, new_url)
        with open(requirements_gpu_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] Fixed: {requirements_gpu_path}")
    else:
        print(f"[INFO] Already up-to-date: {requirements_gpu_path}")
else:
    print(f"[ERROR] File not found: {requirements_gpu_path}")

# 修复 requirements_cpu.txt
requirements_cpu_path = r"E:\mit\requirements_cpu.txt"
if os.path.exists(requirements_cpu_path):
    with open(requirements_cpu_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_url = "git+https://github.com/lucasb-eyer/pydensecrf.git"
    new_url = "git+https://gh-proxy.com/https://github.com/lucasb-eyer/pydensecrf.git"
    
    if old_url in content:
        content = content.replace(old_url, new_url)
        with open(requirements_cpu_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] Fixed: {requirements_cpu_path}")
    else:
        print(f"[INFO] Already up-to-date: {requirements_cpu_path}")
else:
    print(f"[ERROR] File not found: {requirements_cpu_path}")

print("\nAll fixes completed!")

