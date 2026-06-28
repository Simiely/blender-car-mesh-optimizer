"""Car Mesh Optimizer v2.0 — 高面车模智能减面

选择重要特征线 → 设定高/低密度区域体素大小 → 预览布线 → 应用生成
零外部依赖，全部使用 Blender 原生 API (bpy / bmesh / KDTree / Voxel Remesh / Shrinkwrap)
"""
bl_info = {
    "name": "Car Mesh Optimizer",
    "author": "Simiely",
    "version": (2, 0, 1),
    "blender": (3, 6, 0),
    "location": "3D 视图 > 右侧边栏 > 车模减面",
    "description": "高面车模智能减面工具 — 选特征线、配密度参数、预览布线效果、一键生成优化网格",
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
# 工具函数
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
# 密度场 — KDTree 空间查询
# ═══════════════════════════════════════════════════════════════════════

def _build_kdtree(obj):
    """从 obj.data.edges 选中状态构建 KDTree"""
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
    """编辑模式 → 同步选中边到 data 层级 → 构建 KDTree"""
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
    """返回 {BMEdge: cuts} — 越靠近特征线，cuts 越多"""
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
# Remesh 引擎 — Voxel Remesh + Subdivide + Shrinkwrap
# ═══════════════════════════════════════════════════════════════════════

def _voxel_remesh(obj, size):
    _ensure_object_mode()
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    # 方案 A: Remesh Modifier（Blender 3.6+）
    try:
        mod = obj.modifiers.new(name="CD_VoxelRemesh", type='REMESH')
        mod.mode = 'VOXEL'
        mod.voxel_size = size
        mod.use_smooth_shade = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        return
    except Exception:
        _safe_remove_mods(obj, "CD_VoxelRemesh")
    # 方案 B: voxel_remesh operator（部分版本参数名不同，逐个尝试）
    for kwargs in [
        {"voxel_size": size},
        {"size": size},
    ]:
        try:
            bpy.ops.object.voxel_remesh(**kwargs)
            return
        except Exception:
            pass
    raise RuntimeError(f"Voxel Remesh 失败，当前 Blender 版本可能不支持")


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


def _ensure_object_mode():
    """确保当前不在编辑模式"""
    try:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass


def _safe_remove_mods(obj, prefix):
    """删除所有以 prefix 开头的 modifier"""
    for m in list(obj.modifiers):
        if m.name.startswith(prefix):
            try:
                obj.modifiers.remove(m)
            except Exception:
                pass


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


def _safe_unlink(obj):
    for coll in obj.users_collection:
        coll.objects.unlink(obj)


def _cleanup_preview_obj(obj):
    if obj is None:
        return
    md = obj.data
    _safe_unlink(obj)
    bpy.data.objects.remove(obj)
    if md and md.users == 0:
        bpy.data.meshes.remove(md)


def _cleanup_existing(context):
    s = context.scene.car_decimator
    if s.preview_obj_name:
        p = bpy.data.objects.get(s.preview_obj_name)
        if p:
            _cleanup_preview_obj(p)
    for o in list(bpy.data.objects):
        if o.name.endswith(("_Preview", "_Remeshed")):
            if o.name.startswith(s.original_obj_name):
                _cleanup_preview_obj(o)


def _remesh_pipeline(orig, fv_size, nf_size, kdtree):
    """完整 pipeline → (preview_obj, face_count)"""
    mesh_copy = orig.data.copy()
    mesh_copy.name = orig.data.name + "_Remeshed"
    r_obj = bpy.data.objects.new(orig.name + "_Preview", mesh_copy)
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
            _safe_unlink(r_obj)
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
        description="选中特征线附近的体素边长（越小越密，保留更多细节）",
    )
    nonfeature_voxel_size: FloatProperty(
        name="非特征区体素", default=0.08, min=0.005, max=0.5,
        step=0.001, precision=3, subtype='DISTANCE', unit='LENGTH',
        description="远离特征线区域的体素边长（越大面数越少）",
    )
    selected_edge_count: IntProperty(name="已选边数", default=0)
    has_edge_selection: BoolProperty(name="已选取特征线", default=False)
    is_previewing: BoolProperty(name="预览中", default=False)
    preview_obj_name: StringProperty(name="预览对象", default="")
    preview_face_count: IntProperty(name="预览面数", default=0)
    original_face_count: IntProperty(name="原始面数", default=0)
    face_reduction_pct: FloatProperty(
        name="面数占比", default=100.0, min=0.0, max=100.0,
        subtype='PERCENTAGE', description="预览网格面数占原始面数的百分比",
    )
    original_obj_name: StringProperty(name="原始对象", default="")


# ═══════════════════════════════════════════════════════════════════════
# 预设
# ═══════════════════════════════════════════════════════════════════════

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
            self.report({'ERROR'}, "请先选择一个 Mesh 对象")
            return {'CANCELLED'}
        s = context.scene.car_decimator
        s.original_face_count = _tri_count(obj)
        s.original_obj_name = obj.name
        _cleanup_existing(context)
        s.is_previewing = False
        s.preview_obj_name = ""
        s.preview_face_count = 0
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='EDGE')
        self.report({'INFO'}, "选好特征边后切换回物体模式即可")
        return {'FINISHED'}


class CARMESH_OT_capture(bpy.types.Operator):
    bl_idname = "carmesh.capture"
    bl_label = "记录选取"
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


class CARMESH_OT_preview(bpy.types.Operator):
    bl_idname = "carmesh.preview"
    bl_label = "生成预览"
    bl_description = "生成临时网格预览布线效果和面数"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = _active_mesh(context)
        if not obj:
            self.report({'ERROR'}, "请先选中一个网格对象")
            return {'CANCELLED'}
        s = context.scene.car_decimator
        if not s.has_edge_selection or s.selected_edge_count == 0:
            self.report({'ERROR'}, "请先选取特征线")
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
        _cleanup_existing(context)
        self.report({'INFO'}, "正在生成预览网格…")
        try:
            p_obj, fc = _remesh_pipeline(obj, fv, nf, kdtree)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"预览生成失败：{e}")
            return {'CANCELLED'}
        p_obj.display_type = 'WIRE'
        p_obj.show_wire = True
        p_obj.show_all_edges = True
        s.is_previewing = True
        s.preview_obj_name = p_obj.name
        s.preview_face_count = fc
        s.original_face_count = _tri_count(obj)
        if s.original_face_count > 0:
            s.face_reduction_pct = fc / s.original_face_count * 100.0
        bpy.ops.object.select_all(action='DESELECT')
        p_obj.select_set(True)
        context.view_layer.objects.active = p_obj
        self.report({'INFO'}, f"预览完成：{fc:,} 面（{s.face_reduction_pct:.1f}%）")
        return {'FINISHED'}


class CARMESH_OT_cancel(bpy.types.Operator):
    bl_idname = "carmesh.cancel"
    bl_label = "取消预览"
    bl_description = "删除预览网格，回到原始模型"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.car_decimator
        _cleanup_existing(context)
        s.is_previewing = False
        s.preview_obj_name = ""
        s.preview_face_count = 0
        s.face_reduction_pct = 100.0
        if s.original_obj_name:
            orig = bpy.data.objects.get(s.original_obj_name)
            if orig:
                bpy.ops.object.select_all(action='DESELECT')
                orig.select_set(True)
                context.view_layer.objects.active = orig
                orig.show_wire = False
                orig.display_type = 'SOLID'
        self.report({'INFO'}, "预览已取消")
        return {'FINISHED'}


class CARMESH_OT_apply(bpy.types.Operator):
    bl_idname = "carmesh.apply"
    bl_label = "应用结果"
    bl_description = "应用当前预览，生成最终优化后的网格"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.car_decimator
        if not s.is_previewing:
            self.report({'ERROR'}, "请先生成预览")
            return {'CANCELLED'}
        p_obj = bpy.data.objects.get(s.preview_obj_name)
        if p_obj is None:
            self.report({'ERROR'}, "预览对象已丢失，请重新生成预览")
            s.is_previewing = False
            s.preview_obj_name = ""
            return {'CANCELLED'}
        base = (s.original_obj_name or "Mesh") + "_优化"
        name = base
        i = 1
        while bpy.data.objects.get(name):
            name = f"{base}_{i}"
            i += 1
        p_obj.name = name
        p_obj.data.name = name
        p_obj.show_wire = False
        p_obj.show_all_edges = False
        p_obj.display_type = 'SOLID'
        bpy.ops.object.select_all(action='DESELECT')
        p_obj.select_set(True)
        context.view_layer.objects.active = p_obj
        fc = _tri_count(p_obj)
        ofc = s.original_face_count
        s.is_previewing = False
        s.preview_obj_name = ""
        s.has_edge_selection = False
        s.selected_edge_count = 0
        msg = f"已生成：{name}，{fc:,} 面"
        if ofc > 0:
            msg += f"（原始 {ofc:,} 面）"
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
        self.report({'INFO'}, f"已应用预设参数")
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
        box.label(text=f"原始面数：{_tri_count(obj):,}")

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
            col.label(text="编辑模式下选择重要的腰线/缝隙/轮廓", icon='INFO')
            col.label(text="选好后切回物体模式，点击下方按钮确认", icon='INFO')
            # 检测是否有 pending 的边选择
            sel_cnt = _sel_edge_count(obj)
            if sel_cnt > 0:
                col.separator()
                col.operator(
                    "carmesh.capture", text=f"确认选取（{sel_cnt} 条边）",
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

        # ── 步骤 ③：预览 & 应用 ──
        box = layout.box()
        box.label(text="步骤 ③  预览 / 应用", icon='RESTRICT_RENDER_OFF')
        row = box.row(align=True)
        row.scale_y = 1.5
        row.operator("carmesh.preview", text="生成预览", icon='VIEWZOOM')
        if s.is_previewing:
            row.operator("carmesh.apply", text="应用结果", icon='CHECKMARK')
            box.operator("carmesh.cancel", text="取消预览", icon='X')

        layout.separator()

        # ── 预览数据 ──
        if s.is_previewing:
            box = layout.box()
            box.label(text="预览数据", icon='INFO')
            col = box.column(align=True)
            col.label(
                text=f"预览面数：{s.preview_face_count:,}",
                icon='MESH_DATA'
            )
            col.label(
                text=f"原始面数：{s.original_face_count:,}",
                icon='MESH_DATA'
            )
            pct = s.face_reduction_pct
            if pct < 50:
                icon = 'SORT_DESC'
            elif pct < 80:
                icon = 'SORT_ASC'
            else:
                icon = 'MOD_DECIM'
            col.label(
                text=f"占比：{pct:.1f}%（减少 {(100 - pct):.1f}%）",
                icon=icon
            )
            row = col.row(align=True)
            try:
                row.prop(s, "face_reduction_pct", text="", slider=True, emboss=False)
            except TypeError:
                row.prop(s, "face_reduction_pct", text="", slider=True)
            row.enabled = False
            col.separator()
            col.label(
                text=f"预览对象：{s.preview_obj_name}",
                icon='OUTLINER_OB_MESH'
            )


# ═══════════════════════════════════════════════════════════════════════
# 注册 / 注销
# ═══════════════════════════════════════════════════════════════════════

CLASSES = (
    CarDecimatorSettings,
    CARMESH_OT_prepare,
    CARMESH_OT_capture,
    CARMESH_OT_preview,
    CARMESH_OT_cancel,
    CARMESH_OT_apply,
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
