# 开发文档 v3.3.0

## 技术架构

### 整体方案

```
用户选中特征点
      │
      ▼
 顶点 → 边转换（两端均被选中的边记为特征边）
      │
      ▼
 构建保护顶点集合
 ├── 特征边两端顶点（用户选中）
 └── 边界边顶点（仅 1 邻接面 → 模型边缘 / 多部件接缝）
      │
      ▼
 原始模型 ─→ mesh.copy() ─→ 顶点组（保护=1.0, 其余=0.0）
      │                              │
      │               Decimate Collapse（vertex_group 加权）
      │                              │
      │               Shrinkwrap（可选，默认关闭）
      │                              │
      │               dissolve_limited（平面溶解 ~5°）
      │                              │
      │               tris_convert_to_quads（循环多轮 ~45°）
      │                              │
      │                     镜像合并（可选 X/Y/Z 轴）
      │                              │
      ▼                              ▼
 保持不变                       最终优化网格
```

### 为什么用顶点组加权 Decimate 替代 Shrinkwrap

| | Shrinkwrap 方案 (v3.2-) | 顶点组加权 (v3.3+) |
|---|---|---|
| 薄壳模型（车盖） | ❌ 双向投影拉出错误表面 | ✅ 不影响表面形状 |
| 特征保护 | 减面后 KBTree 查找再细分（精度低） | 减面时直接保护（精度高） |
| 多部件接缝 | ❌ 跨部件塌边导致断开 | ✅ 边界边顶点自动保护 |
| 四边面产出 | ❌ 不规则拓扑难以合并 | ✅ 平面溶解预处理 + 循环转换 |
| 管线复杂度 | Decimate → SW → Subdivide → SW | Decimate → 溶解 → 四边面 |

## 版本兼容策略

```python
# Decimate Modifier（3.0+ 稳定）
mod = robj.modifiers.new(name="CD_Dec", type='DECIMATE')
mod.decimate_type = 'COLLAPSE'
mod.ratio = target_ratio

# subdivide_edges — quad_corner_type 兼容
for ct in ('INNER_VERT', 'INNER'):      # INNER_VERT 新版本，INNER 旧版本
    try:
        bmesh.ops.subdivide_edges(..., quad_corner_type=ct)
        break
    except Exception:
        pass

# Shrinkwrap — emboss 参数保护
try:
    row.prop(..., emboss=False)
except TypeError:
    row.prop(...)                         # 旧版本降级
```

## 项目结构

```
blender-car-mesh-optimizer/
├── blender_car_mesh_optimizer.py   # 全部代码（~530 行单文件）
├── README.md
├── DEVELOPMENT.md
└── .gitignore
```

### 代码分区

```
  1-17    bl_info（插件元信息）
 19-24    imports（bpy, bmesh, bpy.props, KDTree）
 28-61    工具函数（5）：_active_mesh, _tri_count, _ensure_obj_mode,
          _safe_remove_mods, _sel_count_in_edit
 63-95    选点→特征边（3）：_verts_to_edges, _build_kdtree
 98-112   收缩包裹函数（保留，可选）：_shrinkwrap
114-132   保护顶点构建：_build_protected_verts
134-203   引擎：_run_pipeline（顶点组加权 Decimate + 溶解 + 四边面）
208-245   属性 PropertyGroup（CarDecimatorSettings）
247-252   预设 PRESETS
255-512   Operators（5）：prepare / select_dense / capture / optimize / preset
          Panel（1）：CARMESH_PT_main
516-534   register / unregister
```

## 核心 API 依赖

| 功能 | API | 版本 |
|------|-----|------|
| 粗减面 | Decimate Modifier（COLLAPSE + vertex_group） | 2.8+ |
| 表面包裹 | Shrinkwrap Modifier（PROJECT 模式，可选） | 2.8+ |
| 平面溶解 | `bpy.ops.mesh.dissolve_limited()` | 2.8+ |
| 四边面转换 | `bpy.ops.mesh.tris_convert_to_quads()` | 2.8+ |
| 合并焊接 | `bpy.ops.mesh.remove_doubles()` | 2.8+ |
| 属性系统 | `bpy.props`（含 EnumProperty） | 2.8+ |
| 面板 | `bpy.types.Panel` | 2.8+ |

## 已知限制

1. 结果网格会丢失 UV / 顶点色 / 形态键（原始模型不受影响）
2. 边界检测依赖拓扑（仅 1 邻接面的边），完全合并的多部件无法区分接缝
3. 四边面转换依赖面法线夹角 < 45 度
4. 镜像合并时接缝精度固定为 0.0001m
5. Shrinkwrap 可选功能对薄壳模型不友好，默认关闭

## 后续方向

- [ ] 特征边影响半径可调
- [ ] 非线性衰减（高斯 / smoothstep）
- [ ] 结果网格 UV 烘焙
- [ ] 批量处理
- [ ] 法线贴图补偿细节

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
