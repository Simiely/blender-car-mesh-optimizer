# 车模网格减面

高面车模智能减面工具 —— 专为汽车模型优化的 Blender 插件。

[![Blender](https://img.shields.io/badge/Blender-3.6~5.x-orange.svg)](https://www.blender.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v3.3.0-blue.svg)](https://github.com/Simiely/blender-car-mesh-optimizer/releases)

## 解决的问题

车模通常面数极高（百万级以上），直接用 Blender 内置 Decimate 减面会丢失车身特征线（腰线、门缝、引擎盖边缘）。

本插件通过 **选取特征点 + 顶点组加权 Decimate + 边界保护 + 平面溶解 + 四边面转换** 策略，在减面的同时保护特征线和接缝不断开。

## 核心特性

- **选点定密度**：手动或自动选取车身密集点，转特征边，顶点组加权保护
- **自动边界保护**：检测仅邻接 1 个面的边（模型边缘 / 多部件接缝），防止减面断开
- **按密度自动选点**：根据相邻边平均长度自动识别密集区域顶点
- **一步生成**：无需预览，直接生成优化网格
- **四边面转换**：循环多轮自动将三角面合并为四边面
- **镜像对称**：支持 X / Y / Z 轴镜像，自动合并为单一对称网格
- **可选收缩包裹**：默认关闭（薄壳模型友好），需要时手动开启
- **零依赖**：纯 Blender API，无需 numpy 等任何外部包
- **全版本兼容**：Blender 3.6 到 5.x 均可用

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
① 选取特征点 → ② 调密度参数 → ③ 生成优化网格
```

### 步骤 ①：选取特征点

**手动选取：**
1. 选中车模，点击 **「选取特征点」**
2. 自动进入编辑模式（顶点选择模式）
3. 在模型上选择密集区域的关键顶点
4. 切回物体模式，点击 **「确认选取」**

**自动选取：**
1. 调整 **密集阈值**（相邻边平均长度小于此值的点会被选中）
2. 点击自动选点按钮（⚡图标）
3. 切回物体模式，点击 **「确认选取」**

### 步骤 ②：调整密度参数

| 参数 | 说明 |
|------|------|
| 特征区保留 | 特征点附近的保留比例，越高越密 |
| 非特征区保留 | 远离特征点的保留比例，越低面越少 |

预设快速切换：**默认 / 高精度 / 低面数 / 均衡**

### 步骤 ③：生成

1. 勾选 **「生成四边面」**（推荐）
2. 如需对称网格，选择 **镜像轴**（X/Y/Z）
3. 点击 **「生成优化网格」**

---

## 参数说明

### 密度参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 特征区保留 | 30% | 特征点附近的保留比例，越高面越多 |
| 非特征区保留 | 5% | 其余区域保留比例，越低减面越多 |

### 预设对比

| 预设 | 特征区 | 非特征区 | 适用场景 |
|------|--------|----------|----------|
| 默认 | 30% | 5% | 通用 |
| 高精度 | 50% | 10% | 保留最多细节 |
| 低面数 | 15% | 2% | 远景 / 移动端 |
| 均衡 | 25% | 5% | 质量与面数平衡 |

### 其他选项

| 选项 | 说明 |
|------|------|
| 生成四边面 | 自动合并三角面为四边面（默认开启） |
| 镜像轴 | 生成对称网格（无 / X / Y / Z） |
| 密集阈值 | 自动选点时相邻边平均长度的上限 |

---

## 版本更新

| 版本 | 日期 | 更新 |
|------|------|------|
| v3.3.0 | 2026-06 | 全新管线：顶点组加权 Decimate + 边界保护 + 平面溶解 |
| v3.2.0 | 2026-06 | 四边面转换 + 镜像对称 (X/Y/Z) + 安装修复 |
| v3.1.0 | 2026-06 | 选点模式 + 按密集度自动选点 |
| v3.0.0 | 2026-06 | Decimate 替代 Voxel Remesh（薄壳模型友好） |
| v2.x | 2026-06 | 密度自适应重网格化 + Voxel Remesh |
| v0.1.0 | 2026-06 | 初始 QEM 实现 |

---

## 兼容性

| | |
|---|---|
| Blender | **3.6 ~ 5.x** |
| 输入 | 任意 Mesh 对象 |
| 外部依赖 | **无**（纯 bpy + bmesh + KDTree） |
| 文件 | 单文件 ~530 行 |

---

## 技术方案

详见 [DEVELOPMENT.md](DEVELOPMENT.md)

## 许可证

MIT License
