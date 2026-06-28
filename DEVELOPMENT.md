# 开发文档

## 技术架构 v2.0

### 整体方案：密度自适应重网格化

放弃手写 QEM 边塌缩，改用 Blender 原生 API 的组合 pipeline：

```
原模型 ──→ Voxel Remesh (非特征区密度) ──→ Shrinkwrap
                                         │
                    KDTree 匹配 ←── 用户选中的特征边
                         │
                    Selective Subdivide (渐变密度)
                         │
                    再 Shrinkwrap (精修)
                         │
                    预览 / 应用
```

### 为什么不用 QEM 了

| v1.x (QEM) | v2.0 (Voxel + Subdivide) |
|---|---|
| 手写 400 行 Python QEM | 0 行自写几何运算 |
| 纯 Python，百万面极慢 | 全部走 Blender C API |
| 依赖 numpy | 零外部依赖 |
| 用户无控制权（5 个固定预设） | 手动选线，精确控制 |
| corner case 多（退化三角/非流形） | Blender 原生处理，稳定 |

### Pipeline 详解

```
Step 1: _build_kdtree / _build_kdtree_from_edit
  从用户选中的边中点构建 KDTree，用于后续空间查询

Step 2: _voxel_remesh
  用非特征区体素大小做全局 Voxel Remesh → 均匀低面网格

Step 3: _shrinkwrap (第一次)
  将低面网格投影包裹到原始模型表面

Step 4: _gradient_cuts + _selective_subdivide
  对 remeshed 网格的每条边，通过 KDTree 查询与选中特征边的距离
  距离 < 3×特征区体素 → 标记为高密度区域
  按距离线性插值计算细分次数 (越近越多)
  调用 bmesh.ops.subdivide_edges 选择性细分

Step 5: _shrinkwrap (第二次)
  细分后的网格再次包裹，精修外形

Step 6: _remesh_pipeline
  串联以上步骤，返回预览对象和面数
```

## 项目结构 v2.0

```
blender-car-mesh-optimizer/
├── blender_car_mesh_optimizer.py   # 全部代码（单文件，570 行）
├── README.md
├── DEVELOPMENT.md
└── .gitignore
```

### 代码分区

```
  1-26    bl_info + imports
 29-46    工具函数 (3): _active_mesh, _tri_count, _sel_edge_count
 49-107   密度场 (3): _build_kdtree, _build_kdtree_from_edit, _gradient_cuts
109-216   Remesh 引擎 (6): _voxel_remesh, _shrinkwrap, _selective_subdivide,
          _safe_unlink, _cleanup_preview_obj, _cleanup_existing, _remesh_pipeline
219-244   属性 PropertyGroup
247-261   预设 PRESETS + _apply_preset
264-446   Operators (6): prepare / capture / preview / cancel / apply / preset
449-538   面板 UI
541-570   register / unregister
```

## 核心 API 依赖

| 功能 | API |
|------|-----|
| 体素重网格 | `bpy.ops.object.voxel_remesh()` |
| 表面包裹 | Shrinkwrap Modifier (PROJECT 模式) |
| 选择性细分 | `bmesh.ops.subdivide_edges()` |
| 空间查询 | `mathutils.kdtree.KDTree` |
| 属性 | `bpy.props.FloatProperty` / `IntProperty` / `BoolProperty` / `StringProperty` |
| 面板 | `bpy.types.Panel` (bl_space_type='VIEW_3D', bl_region_type='UI') |

## 开发环境

### 依赖

- **Blender 3.6+**（内置 Python 3.10+）
- **零外部依赖**

### 调试方法

单文件插件最方便的调试方式：
1. 在 Blender Scripting 工作区打开 `blender_car_mesh_optimizer.py`
2. 修改代码后点击 Run Script（或 Alt+P）
3. 自动重新加载插件

```python
# 或者在 Python Console 中手动重载
import importlib
import blender_car_mesh_optimizer
importlib.reload(blender_car_mesh_optimizer)
```

### 日志

`self.report({'INFO'}, msg)` 输出到 Blender 状态栏和系统控制台。

## 已知限制

1. Voxel Remesh 会丢失 UV / 顶点色 / 形态键（原始模型不受影响，仅结果网格丢失）
2. 特征线影响半径固定为 `3×特征区体素`，暂不可调
3. 渐变细分使用线性插值，更复杂的衰减曲线可实现但未加入
4. 不支持非流形网格
5. Voxel Remesh 后的细分使用 `bmesh.ops.subdivide_edges`，大量边时可能较慢

## 后续优化方向

- [ ] 特征线影响半径可调参数
- [ ] 非线性衰减曲线（高斯/平滑步进）
- [ ] 从原始模型烘焙 UV 到结果网格
- [ ] 批量处理多个模型
- [ ] 法线贴图补偿细节损失
- [ ] 支持面选择（不限于边选择）
- [ ] OpenSubdiv 作为替代细分方案
- [ ] 预览时显示误差热力图对比
