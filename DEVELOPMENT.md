# 开发文档

## 技术架构

### 整体方案：多约束加权 QEM 边塌缩

在标准 QEM（Quadric Error Metric）边塌缩算法基础上，叠加多层惩罚项：

```
Cost(u, v) = QEM_error(u→v)        ← 几何误差（基础）
           + λ₁ × Curvature(u,v)    ← 曲率惩罚
           + λ₂ × Feature(u,v)      ← 特征边惩罚（极高权重）
           + λ₃ × Silhouette(u,v)   ← 轮廓惩罚
           + λ₄ × NormalDev(u,v)    ← 法线偏差惩罚
           + λ₅ × Boundary(u,v)     ← 材质/UV边界惩罚
           + λ₆ × UserWeight(u,v)   ← 用户手动权重
```

### 两阶段减面

```
Phase 1: 粗减（Coarse Pass）
  输入: 百万面
  策略: Blender 原生 Decimate Modifier（C++ 实现，极快）
    外饰: 50% 减面率（保守）
    内饰: 90% 减面率（激进）
    底盘: 90% 减面率（激进）
  输出: ~50 万面

Phase 2: 精减（Fine Pass）
  输入: ~50 万面
  策略: 自定义加权 QEM 边塌缩
    外饰: 全特征保护（曲率 + 特征边 + 轮廓 + 法线）
    内饰: 仅轮廓 + 法线偏差
    底盘: 几乎无保护
  输出: 10-30 万面（精确达标）
```

### 自动分类策略

1. **材质名匹配**：根据材质名中的关键词（body/paint/glass/interior/chassis 等）分类
2. **遮挡检测**：从球面多方向发射射线，统计每个顶点的可见性
   - 高可见 → 外饰
   - 中可见 → 内饰
   - 低可见 → 底盘

### 特征检测

| 特征 | 方法 | 说明 |
|------|------|------|
| 曲率 | 离散拉普拉斯-贝尔特拉米算子 + 高斯曲率 | 检测曲面弯曲程度 |
| 特征边 | 二面角阈值 | 检测折痕、门缝、腰线 |
| 轮廓 | 多视角外积法 | 8 个均匀分布视角采样 |
| 法线偏差 | 邻域法线角度差 | 检测细微折痕 |
| 边界 | 材质 ID + UV 接缝 | 保护贴图边界 |

## 项目结构

```
blender_car_mesh_optimizer/
├── __init__.py                   # 插件入口 (bl_info)
├── properties.py                 # 全局属性定义
├── operators/
│   ├── analyze.py                # Step 1: 模型分析
│   ├── classify.py               # Step 2: 自动分类
│   ├── detect_features.py        # Step 3: 特征检测
│   ├── decimate.py               # Step 4: 两阶段减面
│   └── export.py                 # 导出
├── panels/
│   └── main_panel.py             # 主面板 UI
├── presets/
│   └── defaults.py               # 预设参数
└── utils/
    ├── mesh_utils.py             # 网格工具
    ├── curvature.py              # 曲率分析
    ├── features.py               # 特征边检测
    ├── silhouette.py             # 轮廓检测
    ├── normal_deviation.py       # 法线偏差
    ├── classification.py         # 自动分类
    └── qem.py                    # 加权 QEM 核心算法
```

## 核心算法：QEM 边塌缩

### 1. 二次误差矩阵

对于每个三角形面，其平面方程为 `ax + by + cz + d = 0`（`a² + b² + c² = 1`），基本二次矩阵为：

```
K_p = pp^T = [a²  ab  ac  ad]
             [ab  b²  bc  bd]
             [ac  bc  c²  cd]
             [ad  bd  cd  d²]
```

每个顶点的 QEM 矩阵为该顶点相邻所有面的 K_p 之和。

### 2. 边塌缩代价

边 `(u, v)` 的塌缩代价为：

```
cost = min_pos [pos, 1]^T · (Q_u + Q_v) · [pos, 1]
```

最优塌缩位置通过求解线性方程组得到。

### 3. 加权惩罚

将每个顶点的特征权重映射为 QEM 矩阵的缩放因子：

```
Q'_v = Q_v × (1 + penalty_weight)
```

高权重顶点的边塌缩代价更高，更不容易被删除。

### 4. 贪心塌缩

使用优先队列（最小堆），每次选择代价最小的边进行塌缩，直到达到目标面数。

## 开发环境

### 依赖

- Blender 3.6+（内置 Python 3.10+）
- NumPy（Blender 内置）

### 调试

在 Blender 中运行脚本：

```python
# 在 Blender Scripting 面板中
import sys
sys.path.append("/path/to/blender_car_mesh_optimizer")

# 重新加载所有模块
import importlib
import blender_car_mesh_optimizer as addon
importlib.reload(addon)
```

### 日志

Blender 的 `self.report()` 输出会显示在 Info 区域和终端中。

## 已知限制

1. QEM 算法在 Python 中处理 50 万面以上时速度较慢，后续可考虑 Cython/Numba 加速
2. 遮挡检测使用 Blender 的 ray_cast，在极高面数下可能较慢
3. 当前不支持非流形网格
4. 自动分类依赖材质命名规范，不规范命名可能误分类

## 后续优化方向

- [ ] 轮廓感知增强（更多视角采样）
- [ ] 对称性检测与强制对称
- [ ] 面板引导的半自动重拓扑模式
- [ ] Cython/Numba 加速 QEM
- [ ] 法线贴图烘焙补偿细节
- [ ] 批量处理多个模型
- [ ] 误差热力图对比原始模型
- [ ] 局部重减（选中区域单独重新减面）