# 开发文档 v2.0.1

## 技术架构

### 整体方案

```
用户选中特征边
      │
      ▼
 KDTree 空间索引（边中点 → 最近邻查询）
      │
      ▼
 原始模型 ─→ mesh.copy() ─→ Voxel Remesh（非特征区体素）
      │                              │
      │                      Shrinkwrap 包裹到原模型
      │                              │
      │               KDTree 匹配 → gradient_cuts（渐变细分次数）
      │                              │
      │               bmesh.ops.subdivide_edges（选择性细分）
      │                              │
      │                      再次 Shrinkwrap 精修
      │                              │
      ▼                              ▼
 保持不变                         预览 / 应用
```

### 为什么不手写几何算法

| | v0.1 (QEM) | v2.x |
|---|---|---|
| 核心运算 | Python 手写 QEM（400 行） | Blender C API（0 行自写几何） |
| 百万面性能 | 极慢 | 很快 |
| 外部依赖 | numpy | **零** |
| 用户控制 | 5 固定预设 | 手动选线 + 滑块 |
| 预览 | 无 | 线框实时预览 + 面数统计 |
| 版本兼容 | 3.6+ | **3.6 ~ 5.x** |

## 版本兼容策略

```python
# Voxel Remesh — 三重回退
方案 A: Remesh Modifier（3.6+ 推荐）
方案 B: bpy.ops.object.voxel_remesh(voxel_size=...)
方案 C: bpy.ops.object.voxel_remesh(size=...)  # 部分版本参数名不同

# 面板 UI — emboss 参数保护
try:
    row.prop(..., emboss=False)
except TypeError:
    row.prop(...)                             # 旧版本降级
```

## 项目结构

```
blender-car-mesh-optimizer/
├── blender_car_mesh_optimizer.py   # 全部代码（~630 行单文件）
├── README.md
├── DEVELOPMENT.md
└── .gitignore
```

### 代码分区

```
  1-17    bl_info
 19-25    imports
 27-44    工具函数（3）：_active_mesh, _tri_count, _sel_edge_count
 47-104   密度场（3）：_build_kdtree, _build_kdtree_from_edit, _gradient_cuts
107-165   Remesh 引擎（6）：_voxel_remesh, _shrinkwrap, _ensure_object_mode,
          _safe_remove_mods, _selective_subdivide, _safe_unlink,
          _cleanup_preview_obj, _cleanup_existing, _remesh_pipeline
218-244   属性 PropertyGroup
247-260   预设 PRESETS
263-446   Operators（6）：prepare / capture / preview / cancel / apply / preset
449-576   面板 UI
579-608   register / unregister
```

## 核心 API 依赖

| 功能 | API | 版本 |
|------|-----|------|
| 体素重网格 | Remesh Modifier / `bpy.ops.object.voxel_remesh()` | 3.0+ |
| 表面包裹 | Shrinkwrap Modifier（PROJECT 模式） | 2.8+ |
| 选择性细分 | `bmesh.ops.subdivide_edges()` | 2.6+ |
| 空间查询 | `mathutils.kdtree.KDTree` | 2.6+ |
| 属性系统 | `bpy.props` | 2.8+ |
| 面板 | `bpy.types.Panel` | 2.8+ |

## 调试

单文件插件最方便的调试方式：

1. Blender Scripting 工作区打开 `blender_car_mesh_optimizer.py`
2. 修改后 `Alt+P`（Run Script）自动重载

```python
# Python Console 中手动重载
import importlib
import blender_car_mesh_optimizer
importlib.reload(blender_car_mesh_optimizer)
```

## 已知限制

1. Voxel Remesh 会丢失 UV / 顶点色 / 形态键（原始模型不变，仅结果 mesh 丢失）
2. 特征线影响半径固定为 `3 × 特征区体素`
3. 渐变细分使用线性插值
4. 不支持非流形网格

## 后续方向

- [ ] 特征线影响半径可调
- [ ] 非线性衰减（高斯 / smoothstep）
- [ ] 结果网格 UV 烘焙
- [ ] 批量处理
- [ ] 法线贴图补偿细节
