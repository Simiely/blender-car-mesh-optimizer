# 开发文档 v3.2.0

## 技术架构

### 整体方案

```
用户选中特征点
      │
      ▼
 顶点 → 边转换（两端均被选中的边记为特征边）
      │
      ▼
 KDTree 空间索引（边中点 → 最近邻查询）
      │
      ▼
 原始模型 ─→ mesh.copy() ─→ Decimate Collapse 粗减（非特征区比例）
      │                              │
      │                      Shrinkwrap 包裹到原模型（PROJECT 双向投影）
      │                              │
      │               KDTree 匹配 → 特征边附近细分（subdivide_edges）
      │                              │
      │                      再次 Shrinkwrap 精修
      │                              │
      │                     tris_convert_to_quads（四边面合并）
      │                              │
      │                     镜像合并（可选 X/Y/Z 轴）
      │                              │
      ▼                              ▼
 保持不变                       最终优化网格
```

### 为什么从 Voxel Remesh 切换到 Decimate

| | Voxel Remesh | Decimate Collapse |
|---|---|---|
| 薄壳模型（车盖） | ❌ 只生成一圈轮廓 | ✅ 正确保留薄壳形状 |
| 体积依赖 | 需要封闭体积 | 无体积要求 |
| 结果拓扑 | 全三角面 | 保留原始拓扑结构 |
| 细分兼容 | 需要大量操作 | 可直接细分特征边 |
| Blender API | voxel_size 参数名变化 | DECIMATE 稳定 |

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
 28-57    工具函数（5）：_active_mesh, _tri_count, _ensure_obj_mode,
          _safe_remove_mods, _sel_count_in_edit
 61-91    选点→特征边（3）：_verts_to_edges, _build_kdtree
 96-163   引擎（2）：_shrinkwrap, _run_pipeline
168-199   属性 PropertyGroup（CarDecimatorSettings）
203-208   预设 PRESETS
211-215   _apply_preset
219-422   Operators（5）：prepare / select_dense / capture / optimize / preset
425-508   面板 UI（CARMESH_PT_main）
511-529   register / unregister
```

## 核心 API 依赖

| 功能 | API | 版本 |
|------|-----|------|
| 粗减面 | Decimate Modifier（COLLAPSE 模式） | 2.8+ |
| 表面包裹 | Shrinkwrap Modifier（PROJECT 模式） | 2.8+ |
| 选择性细分 | `bmesh.ops.subdivide_edges()` | 2.6+ |
| 空间查询 | `mathutils.kdtree.KDTree` | 2.6+ |
| 四边面转换 | `bpy.ops.mesh.tris_convert_to_quads()` | 2.8+ |
| 合并焊接 | `bpy.ops.mesh.remove_doubles()` | 2.8+ |
| 属性系统 | `bpy.props`（含 EnumProperty） | 2.8+ |
| 面板 | `bpy.types.Panel` | 2.8+ |

## 已知限制

1. 结果网格会丢失 UV / 顶点色 / 形态键（原始模型不受影响）
2. 特征边影响半径固定为 0.01（KDTree 匹配距离）
3. 四边面转换依赖面法线夹角 < 40 度
4. 镜像合并时接缝精度固定为 0.0001m

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
