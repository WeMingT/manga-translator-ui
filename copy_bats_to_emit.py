#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copy the generated .bat files to E:\mit
"""

import os
import shutil
import glob

# Source: current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Destination
target_dir = r"E:\mit"

# Find all .bat files with Chinese names
bat_files = [f for f in os.listdir(current_dir) if f.endswith('.bat') and '步骤' in f]

if not bat_files:
    print("[ERROR] No .bat files found in current directory!")
    exit(1)

print(f"[INFO] Found {len(bat_files)} .bat files:")
for f in bat_files:
    print(f"  - {f}")

if not os.path.exists(target_dir):
    print(f"[ERROR] Target directory does not exist: {target_dir}")
    exit(1)

print(f"\n[INFO] Copying to: {target_dir}")
for bat_file in bat_files:
    src = os.path.join(current_dir, bat_file)
    dst = os.path.join(target_dir, bat_file)
    try:
        shutil.copy2(src, dst)
        print(f"[OK] Copied: {bat_file}")
    except Exception as e:
        print(f"[ERROR] Failed to copy {bat_file}: {e}")

print("\n[DONE] All .bat files copied to E:\\mit")
print("\nNow run the following in E:\\mit:")
print("  步骤2-启动Qt界面.bat")

