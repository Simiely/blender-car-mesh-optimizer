# 车模网格减面

高面车模智能减面工具 —— 专为汽车模型优化的 Blender 插件。

[![Blender](https://img.shields.io/badge/Blender-3.6~5.x-orange.svg)](https://www.blender.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v2.0.1-blue.svg)](https://github.com/Simiely/blender-car-mesh-optimizer/releases)

## 解决的问题

车模通常面数极高（百万级以上），直接用 Blender 内置 Decimate 减面会丢失车身特征线（腰线、门缝、引擎盖边缘）。

本插件通过 **选取特征线 + 设定密度参数 + 自适应 Voxel Remesh + 渐变细分 + 收缩包裹** 策略，自由控制不同区域的网格密度，同时精确保持外形。

## 核心特性

- **选线定密度**：手动选取车身重要特征线，线条附近保持高密度，其余区域自适应稀疏
- **渐变布线**：密度从特征线向外平滑过渡，无突变
- **实时预览**：线框模式预览布线效果，同时显示面数和占比百分比
- **反复调整**：可取消预览、改参数、重新生成，直到满意
- **零依赖**：纯 Blender API，无需 numpy 等任何外部包
- **全版本兼容**：Blender 3.6 到 5.x 均可用（三重 Voxel Remesh 回退策略）

---

## 安装

### 方法一：Install 单文件（推荐）

1. 下载 [最新 Release](https://github.com/Simiely/blender-car-mesh-optimizer/releases) 中的 `blender_car_mesh_optimizer.py`
2. Blender → `Edit` → `Preferences` → `Add-ons` → `Install...`
3. 选中下载的文件 → `Install Add-on`
4. 搜索 `Car Mesh Optimizer`，勾选启用
5. **重启 Blender**

### 方法二：手动放入 addons 目录

```bash
# Linux
cp blender_car_mesh_optimizer.py ~/.config/blender/*/scripts/addons/

# macOS
cp blender_car_mesh_optimizer.py ~/Library/Application\ Support/Blender/*/scripts/addons/

# Windows (PowerShell)
copy blender_car_mesh_optimizer.py "$env:APPDATA\Blender Foundation\Blender\*\scripts\addons\"
```

### 启用后

按 `N` 键打开 3D 视图右侧栏 → `车模减面` 标签页。

---

## 快速上手

```
① 选取特征线 → ② 确认 + 调密度 → ③ 预览 → 反复调整 → 应用
```

### 步骤 ①：选取特征线

1. 选中车模，点击 **「选取特征线」**
2. 自动进入编辑模式（边选择模式）
3. 在模型上选择车身重要线条（腰线、门缝、引擎盖边缘等）
4. 切回物体模式，点击 **「确认选取」**

### 步骤 ②：调整密度参数

| 参数 | 说明 |
|------|------|
| 特征区体素 | 选中线附近的体素边长（越小越密） |
| 非特征区体素 | 其余区域体素边长（越大面越少） |

预设快速切换：**默认 / 高精度 / 低面数 / 均衡**

### 步骤 ③：预览 & 应用

1. 点击 **「生成预览」** → 线框模式查看布线
2. 面板显示预览面数和占比百分比
3. 不满意 → 改参数 → 重新预览（可反复）
4. 满意 → 点击 **「应用结果」** → 生成最终网格

---

## 参数说明

### 密度参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 特征区体素 | 0.020m | 特征线附近的边长，越小细节越多 |
| 非特征区体素 | 0.080m | 远离特征线的边长，越大面越少 |

### 预设对比

| 预设 | 特征区 | 非特征区 | 适用场景 |
|------|--------|----------|----------|
| 默认 | 0.020m | 0.080m | 通用 |
| 高精度 | 0.010m | 0.050m | 保留最多细节 |
| 低面数 | 0.030m | 0.150m | 远景 / 移动端 |
| 均衡 | 0.015m | 0.060m | 质量与面数平衡 |

---

## 兼容性

| | |
|---|---|
| Blender | **3.6 ~ 5.x**（三重 Voxel Remesh 回退策略） |
| 输入 | 任意 Mesh 对象 |
| 外部依赖 | **无**（纯 bpy + bmesh + KDTree） |
| 文件 | 单文件 ~600 行 |

---

## 技术方案

详见 [DEVELOPMENT.md](DEVELOPMENT.md)

## 许可证

MIT License
