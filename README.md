# Car Mesh Optimizer

高面车模智能减面工具 —— 专为汽车模型优化的 Blender 插件。

[![Blender](https://img.shields.io/badge/Blender-3.6+-orange.svg)](https://www.blender.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v0.1.0-blue.svg)](https://github.com/user/blender-car-mesh-optimizer/releases)

## 解决的问题

车模通常面数极高（百万级以上），直接用 Blender 内置 Decimate 减面会导致：
- 车身特征线丢失
- 曲面出现折痕
- 玻璃/内饰/底盘的材质边界错乱

本插件通过 **外饰/内饰/底盘分区 + 多约束加权 QEM 边塌缩** 两阶段策略，在保持视觉质量的前提下，将高面车模精确减面到 10-30 万面。

## 核心特性

- **自动分区**：按材质名称和遮挡关系，自动识别外饰、内饰、底盘
- **多特征检测**：曲率分析 + 特征边检测 + 轮廓检测 + 法线偏差 + 材质/UV 边界
- **两阶段减面**：Phase 1 粗减（Blender 原生） + Phase 2 精减（加权 QEM 边塌缩）
- **预算分配**：外饰、内饰、底盘独立设置面数预算
- **5 套预设**：默认 / 轿车 / SUV / 跑车 / 激进减面，一键切换
- **向导式操作**：5 步完成，无需深入学习

---

## 安装

### 方法一：从 Release 安装（推荐）

1. 前往 [Releases](https://github.com/user/blender-car-mesh-optimizer/releases) 页面
2. 下载最新的 `blender_car_mesh_optimizer-vX.Y.Z.zip`
3. 打开 Blender → `Edit` → `Preferences` → `Add-ons`
4. 点击右上角 `Install...` 按钮
5. 选择下载的 zip 文件，点击 `Install Add-on`
6. 在插件列表中搜索 `Car Mesh Optimizer`，勾选启用

### 方法二：手动安装

```bash
# 克隆仓库到 Blender addons 目录
# Linux
git clone https://github.com/user/blender-car-mesh-optimizer.git \
  ~/.config/blender/4.0/scripts/addons/blender_car_mesh_optimizer

# macOS
git clone https://github.com/user/blender-car-mesh-optimizer.git \
  ~/Library/Application\ Support/Blender/4.0/scripts/addons/blender_car_mesh_optimizer

# Windows (PowerShell)
git clone https://github.com/user/blender-car-mesh-optimizer.git `
  $env:APPDATA\Blender Foundation\Blender\4.0\scripts\addons\blender_car_mesh_optimizer
```

然后打开 Blender → `Edit` → `Preferences` → `Add-ons`，搜索 `Car Mesh Optimizer` 并启用。

### 方法三：下载 ZIP 手动解压

1. 下载仓库 ZIP
2. 解压到 Blender 的 addons 目录：
   - **Windows**: `%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\`
   - **macOS**: `~/Library/Application Support/Blender/<version>/scripts/addons/`
   - **Linux**: `~/.config/blender/<version>/scripts/addons/`
3. 确保文件夹名为 `blender_car_mesh_optimizer`
4. 打开 Blender → `Edit` → `Preferences` → `Add-ons`，搜索并启用

### 启用后

插件面板会出现在 3D View 右侧栏：`View3D` → 右侧边栏（按 `N` 键）→ `CarMeshOpt` 标签页。

---

## 快速上手

### 5 步完成减面

```
选中模型 → 选预设 → 分析 → 分类 → 特征检测 → 减面 → 检查 & 导出
```

### 详细操作

#### Step 1：分析模型

1. 在 Blender 中打开或导入高面车模
2. 选中模型，右侧 `CarMeshOpt` 面板
3. 点击 **「开始分析」**
4. 插件自动统计顶点数、面数、材质数

#### Step 2：自动分类

1. 点击 **「自动分类」**
2. 插件根据材质名和遮挡关系，将模型分为三类：
   - **外饰（蓝）**：车身面板、玻璃、灯组、格栅
   - **内饰（绿）**：座椅、仪表盘、方向盘
   - **底盘（黄）**：发动机、悬挂、轮胎
3. 可在顶点组面板中查看分类结果
4. 调整预算占比滑块（外饰/内饰/底盘）

#### Step 3：特征检测

1. 点击 **「检测特征」**
2. 插件自动计算 5 种特征：
   - 曲率分析（曲面弯曲程度）
   - 特征边检测（折痕、门缝、腰线）
   - 轮廓检测（多视角采样）
   - 法线偏差（细微折痕）
   - 材质/UV 边界
3. 可调整各特征的 λ 权重系数
4. 点击 **「显示特征热力图」** 在模型上查看权重分布

#### Step 4：执行减面

1. 设置 **「目标总面数」**（默认 20 万）
2. 选择预设（轿车 / SUV / 跑车），或手动调整参数
3. 点击 **「开始减面」**
4. 等待两阶段完成：
   - Phase 1 粗减：Blender 原生 Decimate，快速减少冗余面
   - Phase 2 精减：加权 QEM 边塌缩，精确保护特征
5. 完成后显示减面比例

#### Step 5：检查结果

1. 查看最终面数和减面比例
2. 与原模型对比视觉效果
3. 点击 **「导出模型」** 保存为 OBJ/FBX

---

## 参数说明

### 面数预算

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 目标总面数 | 200,000 | 最终期望的总面数 |
| 外饰占比 | 75% | 外饰在总预算中的面数占比 |
| 内饰占比 | 17% | 内饰在总预算中的面数占比 |
| 底盘占比 | 8% | 底盘在总预算中的面数占比 |

### 特征权重（λ 参数）

越高的值意味着该特征越不容易被减面。

| 参数 | 默认值 | 说明 |
|------|--------|------|
| λ₁ 曲率 | 2.0 | 曲面保护权重 |
| λ₂ 特征边 | 20.0 | 特征线保护权重（极高值，保护腰线/门缝） |
| λ₃ 轮廓 | 5.0 | 轮廓保护权重 |
| λ₄ 法线偏差 | 3.0 | 折痕保护权重 |
| λ₅ 边界 | 20.0 | 材质/UV 边界保护权重 |
| λ₆ 用户权重 | 1.0 | 用户手动绘制的权重倍乘系数 |

### 粗减参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 外饰粗减比 | 50% | Phase 1 外饰减面比例 |
| 内饰粗减比 | 90% | Phase 1 内饰减面比例 |
| 底盘粗减比 | 90% | Phase 1 底盘减面比例 |

### 预设对比

| 预设 | 目标面数 | 外饰占比 | 特点 |
|------|----------|----------|------|
| 默认 | 20 万 | 75% | 通用平衡 |
| 轿车 | 20 万 | 78% | 侧重外饰曲面 |
| SUV | 20 万 | 75% | 加强轮廓保护 |
| 跑车 | 25 万 | 82% | 特征线保护最强 |
| 激进 | 10 万 | 70% | 极限减面 |

---

## 兼容性

- **Blender**: 3.6 及以上版本
- **输入模型**: 任意面数的三角/四边网格
- **推荐**: 模型有规范的材质命名，可获得更好的分类效果

---

## 技术方案

详见 [DEVELOPMENT.md](DEVELOPMENT.md)

## 许可证

MIT License