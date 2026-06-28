"""Car Mesh Optimizer v2.1 — 高面车模智能减面

选取重要特征线 → 设定密度参数 → 一键生���优化网格
零外部依赖，纯 Blender 原生 API
"""
bl_info = {
    "name": "Car Mesh Optimizer",
    "author": "Simiely",
    "version": (2, 1, 0),
    "blender": (3, 6, 0),
    "location": "3D 视图 > 右侧边栏 > 车模减面",
    "description": "高面车模智能减面 — 选特征线、调密度、一键生成优化网格",
    "category": "Mesh",
    "support": "COMMUNITY",
    "doc_url": "https://github.com/Simiely/blender-car-mesh-optimizer",
    "tracker_url": "https://github.com/Simiely/blender-car-mesh-optimizer/issues",
}

import bpy
import bmesh
from bpy.props import (
    IntProperty, FloatProperty, BoolProperty, StringProperty, PointerProperty,
)
from mathutils.kdtree import KDTree


# ═══════════════════════════════════════════════════════════════════════
# 工具
# ═══════════════════════════════════════════════════════════════════════

def _active_mesh(context):
    obj = context.active_object
    return obj if (obj and obj.type == 'MESH') else None


def _tri_count(obj):
    n = 0
    for p in obj.data.polygons:
        n += max(1, len(p.vertices) - 2)
    return n


def _sel_edge_count(obj):
    return sum(1 for e in obj.data.edges if e.select)


# ═══════════════════════════════════════════════════════════════════════
# 密度场 — KDTree
# ═══���═══════════════════════════════════════════════════════════════════

def _build_kdtree(obj):
    pts, idxs = [], []
    for e in obj.data.edges:
        if e.select:
            v0 = obj.data.vertices[e.vertices[0]].co
            v1 = obj.data.vertices[e.vertices[1]].co
            m = (v0 + v1) / 2.0
            pts.append(m)
            idxs.append(e.index)
    if not pts:
        return None, [], 0
    kd = KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert((p.x, p.y, p.z), i)
    kd.balance()
    return kd, idxs, len(idxs)


def _build_kdtree_from_edit(obj):
    bm = bmesh.from_edit_mesh(obj.data)
    pts = []
    cnt = 0
    for e in obj.data.edges:
        e.select = False
    for e in bm.edges:
        if e.select:
            m = (e.verts[0].co + e.verts[1].co) / 2.0
            pts.append(m)
            if e.index < len(obj.data.edges):
                obj.data.edges[e.index].select = True
            cnt += 1
    if not pts:
        return None, 0
    kd = KDTree(cnt)
    for i, p in enumerate(pts):
        kd.insert((p.x, p.y, p.z), i)
    kd.balance()
    return kd, cnt


def _gradient_cuts(bm, kdtree, fv_size, nf_size):
    radius = fv_size * 3.0
    max_cuts = max(1, int(nf_size / fv_size))
    result = {}
    for e in bm.edges:
        m = (e.verts[0].co + e.verts[1].co) / 2.0
        _, _, dist = kdtree.find((m.x, m.y, m.z))
        if dist < radius:
            t = 1.0 - dist / radius
            result[e] = max(1, int(t * max_cuts))
    return result


# ═══════════════════════════════════════════════════════════════════════
# Remesh 引擎
# ═══════════════════════════════════════════════════════════════════════

def _ensure_object_mode():
    try:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass


def _safe_remove_mods(obj, prefix):
    for m in list(obj.modifiers):
        if m.name.startswith(prefix):
            try:
                obj.modifiers.remove(m)
            except Exception:
                pass


def _voxel_remesh(obj, size):
    _ensure_object_mode()
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        mod = obj.modifiers.new(name="CD_VoxelRemesh", type='REMESH')
        mod.mode = 'VOXEL'
        mod.voxel_size = size
        mod.use_smooth_shade = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        return
    except Exception:
        _safe_remove_mods(obj, "CD_VoxelRemesh")
    for kwargs in [{"voxel_size": size}, {"size": size}]:
        try:
            bpy.ops.object.voxel_remesh(**kwargs)
            return
        except Exception:
            pass
    raise RuntimeError("Voxel Remesh 失败")


def _shrinkwrap(obj, target, offset=0.0005):
    _ensure_object_mode()
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    _safe_remove_mods(obj, "CD_Shrinkwrap")
    mod = obj.modifiers.new(name="CD_Shrinkwrap", type='SHRINKWRAP')
    mod.wrap_method = 'PROJECT'
    mod.target = target
    mod.offset = offset
    mod.use_project_x = mod.use_project_y = mod.use_project_z = True
    mod.use_positive_direction = mod.use_negative_direction = True
    bpy.ops.object.modifier_apply(modifier=mod.name)


def _selective_subdivide(bm, kdtree, fv_size, nf_size):
    cuts_map = _gradient_cuts(bm, kdtree, fv_size, nf_size)
    if not cuts_map:
        return 0
    groups = {}
    for e, c in cuts_map.items():
        groups.setdefault(c, []).append(e)
    total = 0
    for cuts, edges in sorted(groups.items()):
        try:
            bmesh.ops.subdivide_edges(
                bm, edges=edges, cuts=cuts,
                use_grid_fill=True, quad_corner_type='INNER', smooth=0.0,
            )
        except TypeError:
            bmesh.ops.subdivide_edges(
                bm, edges=edges, cuts=cuts,
                use_grid_fill=True, quad_corner_type='INNER_VERT', smooth=0.0,
            )
        total += len(edges)
    return total


def _run_pipeline(orig, fv_size, nf_size, kdtree):
    """一步生成优化网格 → (obj, face_count)"""
    mesh_copy = orig.data.copy()
    mesh_copy.name = orig.data.name + "_Remeshed"
    r_obj = bpy.data.objects.new(orig.name + "_Remeshed", mesh_copy)
    r_obj.matrix_world = orig.matrix_world.copy()
    bpy.context.collection.objects.link(r_obj)
    try:
        _voxel_remesh(r_obj, nf_size)
        _shrinkwrap(r_obj, orig, 0.0005)
        bm = bmesh.new()
        bm.from_mesh(r_obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        n = _selective_subdivide(bm, kdtree, fv_size, nf_size)
        bm.to_mesh(r_obj.data)
        bm.free()
        if n > 0:
            _shrinkwrap(r_obj, orig, 0.0003)
        fc = _tri_count(r_obj)
        return r_obj, fc
    except Exception:
        if r_obj:
            for coll in r_obj.users_collection:
                coll.objects.unlink(r_obj)
            bpy.data.objects.remove(r_obj)
        if mesh_copy and mesh_copy.users == 0:
            bpy.data.meshes.remove(mesh_copy)
        raise


# ═══════════════════════════════════════════════════════════════════════
# 属性
# ═══════════════════════════════════════════════════════════════════════

class CarDecimatorSettings(bpy.types.PropertyGroup):
    feature_voxel_size: FloatProperty(
        name="特征区体素", default=0.02, min=0.001, max=0.5,
        step=0.001, precision=3, subtype='DISTANCE', unit='LENGTH',
        description="选中特征线附近的体素边长（越小越密）",
    )
    nonfeature_voxel_size: FloatProperty(
        name="非特征区体素", default=0.08, min=0.005, max=0.5,
        step=0.001, precision=3, subtype='DISTANCE', unit='LENGTH',
        description="远离特征线区域的体素边长（越大面越少）",
    )
    selected_edge_count: IntProperty(name="已选边数", default=0)
    has_edge_selection: BoolProperty(name="已选取特征线", default=False)
    original_face_count: IntProperty(name="原始面数", default=0)
    original_obj_name: StringProperty(name="原始对象", default="")
    result_face_count: IntProperty(name="结果面���", default=0)
    result_name: StringProperty(name="结果名称", default="")


PRESETS = {
    "DEFAULT": {"name": "默认",   "fv": 0.020, "nf": 0.080},
    "HIGH":    {"name": "高精度", "fv": 0.010, "nf": 0.050},
    "LOW":     {"name": "低面数", "fv": 0.030, "nf": 0.150},
    "BALANCE": {"name": "均衡",   "fv": 0.015, "nf": 0.060},
}


def _apply_preset(settings, key):
    p = PRESETS.get(key, PRESETS["DEFAULT"])
    settings.feature_voxel_size = p["fv"]
    settings.nonfeature_voxel_size = p["nf"]


# ═══════════════════════════════════════════════════════════════════════
# Operators
# ═══════════════════════════════════════════════════════════════════════

class CARMESH_OT_prepare(bpy.types.Operator):
    bl_idname = "carmesh.prepare"
    bl_label = "选取特征线"
    bl_description = "进入编辑模式 — 选择车身重要线条（腰线 / 门缝 / 引擎盖边缘）"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = _active_mesh(context)
        if not obj:
            self.report({'ERROR'}, "请先选中一个网格对象")
            return {'CANCELLED'}
        s = context.scene.car_decimator
        s.original_face_count = _tri_count(obj)
        s.original_obj_name = obj.name
        s.has_edge_selection = False
        s.selected_edge_count = 0
        s.result_face_count = 0
        s.result_name = ""
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='EDGE')
        self.report({'INFO'}, "选好特征边后切换回物体模式即可")
        return {'FINISHED'}


class CARMESH_OT_capture(bpy.types.Operator):
    bl_idname = "carmesh.capture"
    bl_label = "确认选取"
    bl_description = "将当前选中的边标记为特征线"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = _active_mesh(context)
        if not obj:
            self.report({'ERROR'}, "请先选中一个网格对象")
            return {'CANCELLED'}
        s = context.scene.car_decimator
        if obj.mode == 'EDIT':
            _, cnt = _build_kdtree_from_edit(obj)
        else:
            cnt = _sel_edge_count(obj)
        s.selected_edge_count = cnt
        s.has_edge_selection = cnt > 0
        if cnt == 0:
            self.report({'WARNING'}, "未选中任何边，请至少选一条特征线")
            return {'CANCELLED'}
        self.report({'INFO'}, f"已记录 {cnt} 条特征边")
        return {'FINISHED'}


class CARMESH_OT_optimize(bpy.types.Operator):
    bl_idname = "carmesh.optimize"
    bl_label = "生成优化网格"
    bl_description = "一步生成优化后的网格"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = _active_mesh(context)
        if not obj:
            self.report({'ERROR'}, "请先选中一个网格对象")
            return {'CANCELLED'}
        s = context.scene.car_decimator
        if not s.has_edge_selection or s.selected_edge_count == 0:
            self.report({'ERROR'}, "请先选取特征线并确认")
            return {'CANCELLED'}
        fv, nf = s.feature_voxel_size, s.nonfeature_voxel_size
        if fv >= nf:
            self.report({'ERROR'},
                f"特征区体素 ({fv:.3f}) 必须小于非特征区体素 ({nf:.3f})")
            return {'CANCELLED'}
        kdtree, _, _ = _build_kdtree(obj)
        if kdtree is None:
            self.report({'ERROR'}, "特征线数据异常，请重新选取")
            return {'CANCELLED'}
        self.report({'INFO'}, "正在生成优化网格…")
        try:
            r_obj, fc = _run_pipeline(obj, fv, nf, kdtree)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"生成失败：{e}")
            return {'CANCELLED'}
        # 重命名
        base = obj.name + "_优化"
        name = base
        i = 1
        while bpy.data.objects.get(name):
            name = f"{base}_{i}"
            i += 1
        r_obj.name = name
        r_obj.data.name = name
        r_obj.display_type = 'SOLID'
        bpy.ops.object.select_all(action='DESELECT')
        r_obj.select_set(True)
        context.view_layer.objects.active = r_obj
        ofc = s.original_face_count
        s.result_face_count = fc
        s.result_name = name
        s.has_edge_selection = False
        s.selected_edge_count = 0
        msg = f"已生成：{name}，{fc:,} 面"
        if ofc > 0:
            msg += f"（原始 {ofc:,} 面，减少 {(1 - fc / ofc) * 100:.1f}%）"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class CARMESH_OT_preset(bpy.types.Operator):
    bl_idname = "carmesh.preset"
    bl_label = "快速预设"
    bl_description = "一键应用预设的密度参数"
    bl_options = {'REGISTER', 'UNDO'}
    preset_key: bpy.props.StringProperty()

    def execute(self, context):
        _apply_preset(context.scene.car_decimator, self.preset_key)
        self.report({'INFO'}, "已应用预设参数")
        return {'FINISHED'}


# ═══════════════════════════════════════════════════════════════════════
# 面板
# ═══════════════════════════════════════════════════════════════════════

class CARMESH_PT_main(bpy.types.Panel):
    bl_label = "车模网格减面"
    bl_idname = "CARMESH_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "车模减面"

    def draw(self, context):
        layout = self.layout
        try:
            s = context.scene.car_decimator
        except AttributeError:
            layout.label(text="插件未正确加载，请重新启用", icon='ERROR')
            return
        obj = _active_mesh(context)

        # ── 当前模型 ──
        box = layout.box()
        box.label(text="当前模型", icon='OBJECT_DATA')
        if obj is None:
            box.label(text="请选择一个网格对象", icon='ERROR')
            return
        box.label(text=f"名称：{obj.name}")
        box.label(text=f"原���面数：{_tri_count(obj):,}")

        # ── 步骤 ①：选取特征线 ──
        box = layout.box()
        box.label(text="步骤 ①  选取特征线", icon='EDGESEL')
        if s.has_edge_selection:
            col = box.column(align=True)
            col.label(
                text=f"已记录 {s.selected_edge_count} 条特征边",
                icon='CHECKMARK'
            )
            col.operator("carmesh.prepare", text="重新选取", icon='GREASEPENCIL')
        else:
            col = box.column(align=True)
            col.operator("carmesh.prepare", text="选取特征线", icon='GREASEPENCIL')
            col.label(text="编辑模式下选择腰线/门缝/轮廓", icon='INFO')
            col.label(text="选好后切回物体模式，点击下方确认", icon='INFO')
            sel_cnt = _sel_edge_count(obj)
            if sel_cnt > 0:
                col.separator()
                col.operator(
                    "carmesh.capture",
                    text=f"确认选取（{sel_cnt} 条边）",
                    icon='CHECKMARK'
                )

        layout.separator()

        # ── 步骤 ②：密度参数 ──
        box = layout.box()
        box.label(text="步骤 ②  密度参数", icon='PREFERENCES')
        row = box.row(align=True)
        row.label(text="快速预设：", icon='PRESET')
        for k, v in PRESETS.items():
            op = row.operator("carmesh.preset", text=v["name"])
            op.preset_key = k
        col = box.column(align=True)
        col.prop(s, "feature_voxel_size", text="特征区体素")
        col.label(
            text=f"  ↳ 特征线附近边长 ≈ {s.feature_voxel_size:.3f} m",
            icon='DOT'
        )
        col.separator()
        col.prop(s, "nonfeature_voxel_size", text="非特征区体素")
        col.label(
            text=f"  ↳ 其余区域边长 ≈ {s.nonfeature_voxel_size:.3f} m",
            icon='DOT'
        )
        if s.feature_voxel_size > 0:
            r = s.nonfeature_voxel_size / s.feature_voxel_size
            col.label(
                text=f"密度比 {r:.1f} : 1（特征区密 {r:.1f} 倍）",
                icon='SORTSIZE'
            )

        layout.separator()

        # ── 步骤 ③：生成 ──
        box = layout.box()
        box.label(text="步骤 ③  生成优化网格", icon='RESTRICT_RENDER_OFF')
        col = box.column(align=True)
        col.scale_y = 1.8
        col.operator("carmesh.optimize", text="生成优化网格", icon='CHECKMARK')

        layout.separator()

        # ── 上次结果 ──
        if s.result_name:
            box = layout.box()
            box.label(text="上次结果", icon='INFO')
            col = box.column(align=True)
            col.label(text=f"名称：{s.result_name}", icon='OUTLINER_OB_MESH')
            col.label(text=f"面数：{s.result_face_count:,}", icon='MESH_DATA')
            ofc = s.original_face_count
            if ofc > 0:
                pct = s.result_face_count / ofc * 100
                col.label(
                    text=f"占比：{pct:.1f}%（减少 {(100-pct):.1f}%）",
                    icon='SORT_DESC'
                )


# ═══════════════════════════════════════════════════════════════════════
# 注册 / 注销
# ═══════════════════════════════════════════════════════════════════════

CLASSES = (
    CarDecimatorSettings,
    CARMESH_OT_prepare,
    CARMESH_OT_capture,
    CARMESH_OT_optimize,
    CARMESH_OT_preset,
    CARMESH_PT_main,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.car_decimator = PointerProperty(type=CarDecimatorSettings)


def unregister():
    del bpy.types.Scene.car_decimator
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
