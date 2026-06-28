#!/usr/bin/env python3
"""Release 打包脚本

生成符合 Blender 安装标准的 zip 包：
  blender_car_mesh_optimizer-vX.Y.Z.zip

用法:
  python3 scripts/release.py          # 在当前目录生成 release zip
  python3 scripts/release.py --dry-run  # 预览，不生成文件
"""

import os
import sys
import re
import shutil
import zipfile
from pathlib import Path


ADDON_NAME = "blender_car_mesh_optimizer"


def get_version(addon_dir):
    """从 __init__.py 的 bl_info 中读取版本号"""
    init_path = addon_dir / "__init__.py"
    if not init_path.exists():
        raise FileNotFoundError(f"找不到 {init_path}")

    content = init_path.read_text(encoding="utf-8")
    # 匹配 version: (0, 1, 0)
    match = re.search(r'"version":\s*\((\d+),\s*(\d+),\s*(\d+)\)', content)
    if not match:
        raise ValueError("无法从 bl_info 中解析 version")

    major, minor, patch = match.groups()
    return f"{major}.{minor}.{patch}"


def should_include(path):
    """判断文件是否应该打包"""
    name = path.name

    # 排除列表
    exclude = {
        "__pycache__",
        ".git",
        ".gitignore",
        ".DS_Store",
        "*.pyc",
        "*.pyo",
        "*.blend1",
        "scripts",
        "dist",
    }

    if name.startswith("."):
        return False
    if name in exclude:
        return False
    if name.endswith((".pyc", ".pyo", ".blend1")):
        return False

    return True


def create_release(addon_dir, output_dir, dry_run=False):
    """创建 release zip"""
    addon_dir = Path(addon_dir).resolve()
    output_dir = Path(output_dir).resolve()

    version = get_version(addon_dir)
    zip_name = f"{ADDON_NAME}-v{version}.zip"
    zip_path = output_dir / zip_name

    print(f"=" * 60)
    print(f"  Car Mesh Optimizer - Release 打包")
    print(f"=" * 60)
    print(f"  版本:     v{version}")
    print(f"  源目录:   {addon_dir}")
    print(f"  输出文件: {zip_path}")
    print(f"  模式:     {'预览 (dry-run)' if dry_run else '正式打包'}")
    print(f"-" * 60)

    if dry_run:
        print("\n将打包以下文件:")
        for root, dirs, files in os.walk(addon_dir):
            # 过滤目录
            dirs[:] = [d for d in dirs if should_include(Path(d))]
            for f in files:
                fp = Path(f)
                if should_include(fp):
                    rel = Path(root).relative_to(addon_dir) / f
                    print(f"  + {rel}")
        print(f"\n输出文件名: {zip_name}")
        return

    # 创建 zip
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(addon_dir):
            # 过滤目录
            dirs[:] = [d for d in dirs if should_include(Path(d))]

            for f in files:
                fp = Path(f)
                if not should_include(fp):
                    continue

                file_path = Path(root) / f
                # zip 内的路径：blender_car_mesh_optimizer/xxx
                arcname = ADDON_NAME / file_path.relative_to(addon_dir)
                zf.write(file_path, arcname)
                print(f"  + {arcname}")

    zip_size = zip_path.stat().st_size
    print(f"\n  Release 打包完成!")
    print(f"  文件: {zip_path}")
    print(f"  大小: {zip_size / 1024:.1f} KB")
    print(f"\n  安装方法:")
    print(f"    Blender → Edit → Preferences → Add-ons → Install...")
    print(f"    选择 {zip_name}")
    print(f"    搜索 'Car Mesh Optimizer' 并启用")


def main():
    dry_run = "--dry-run" in sys.argv

    # 脚本所在目录的父目录 = 插件根目录
    script_dir = Path(__file__).resolve().parent
    addon_dir = script_dir.parent

    # 输出到 dist/ 目录
    output_dir = addon_dir / "dist"

    create_release(addon_dir, output_dir, dry_run=dry_run)


if __name__ == "__main__":
    main()