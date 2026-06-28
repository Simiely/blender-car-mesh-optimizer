# Car Mesh Optimizer

密度自适应网格优化工具 —— 专为车模设计的 Blender 单文件插件。

[![Blender](https://img.shields.io/badge/Blender-3.6+-orange.svg)](https://www.blender.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v2.0.0-blue.svg)](https://github.com/Simiely/blender-car-mesh-optimizer/releases)

## 解决的问题

车模通常面数极高（百万级以上），直接用 Blender 内置 Decimate 减面会丢失车身特征线。

本插件通过 **选择重要特征线 + 设定密度参数 + Voxel Remesh + 自适应细分 + Shrinkwrap** 策略，自由控制不同区域的网格密度，同时精确保持外形。

## 核心特性

- **选线定密度**：手动选择重要的车身特征线，该区域保持高密度，其余区域自动稀疏
- **自适应布线**：密度从特征线向外渐变过渡，布线自然
- **实时预览**：生成预览网格，线框模式下查看布线效果和面数百分比
- **反复调整**：不满意可以取消预览，调参数后重新生成
- **零外部依赖**：纯 Blender API（bpy / bmesh / KDTree / Voxel Remesh / Shrinkwrap），无需 numpy
- **单文件**：只有一个 `.py` 文件，570 行，安装简单

---

## 安装

### 方法一：Install 单文件（推荐）

1. 下载 `blender_car_mesh_optimizer.py`
2. Blender → `Edit` → `Preferences` → `Add-ons` → `Install...`
3. 选择 `blender_car_mesh_optimizer.py` → `Install Add-on`
4. 搜索 `Car Mesh Optimizer`，勾选启用

### 方法二：手动放入 addons 目录

```bash
# Linux
cp blender_car_mesh_optimizer.py ~/.config/blender/4.0/scripts/addons/

# macOS
cp blender_car_mesh_optimizer.py ~/Library/Application\ Support/Blender/4.0/scripts/addons/

# Windows
copy blender_car_mesh_optimizer.py "%APPDATA%\Blender Foundation\Blender\4.0\scripts\addons\"
```

然后 Blender → `Edit` → `Preferences` → `Add-ons` → 搜索并启用。

### 方法三：git clone 后拷贝

```bash
git clone https://github.com/Simiely/blender-car-mesh-optimizer.git
# 将 blender_car_mesh_optimizer.py 拷贝到 Blender addons 目录即可
```

### 启用后

插件面板出现在 3D View 右侧栏：按 `N` 键 → `CarMeshOpt` 标签页。

---

## 快速上手（3 步）

```
① 选择特征线 → ② 调密度参数 → ③ 预览 → 反复调整 → 应用
```

### Step 1：选择特征线

1. 选中车模，点击面板中 **「选择特征线」**
2. 自动进入编辑模式（边选择模式）
3. 在 3D 视图选择重要的车身线条（腰线、门缝、引擎盖边缘等）
4. 切换回 Object Mode

### Step 2：调整密度参数

- **特征区密度**：选中线附近的体素大小（越小越密，默认 0.02m）
- **非特征区密度**：其余区域的体素大小（越大面越少，默认 0.08m）
- 可用预设按钮快速切换：默认 / 高精度 / 低面数 / 平衡

### Step 3：预览 & 应用

1. 点击 **「预览」**：生成临时网格，线框模式显示布线
2. 面板显示预览面数和占原始面数的百分比
3. 不满意 → 调参数 → 重新预览（可反复尝试）
4. 满意 → 点击 **「应用」**：生成最终优化网格

---

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 特征区密度 | 0.02m | 选中线附近的体素边长，越小面越多 |
| 非特征区密度 | 0.08m | 其余区域体素边长，越大面越少 |

| 预设 | 特征区 | 非特征区 | 适用 |
|------|--------|----------|------|
| 默认 | 0.020m | 0.080m | 通用 |
| 高精度 | 0.010m | 0.050m | 保留最多细节 |
| 低面数 | 0.030m | 0.150m | 远景/移动端 |
| 平衡 | 0.015m | 0.060m | 质量与面数平衡 |

---

## 兼容性

- **Blender**: 3.6 及以上版本
- **输入模型**: 任意 Mesh 对象
- **外部依赖**: 无

---

## 技术方案

详见 [DEVELOPMENT.md](DEVELOPMENT.md)

## 许可证

MIT License
