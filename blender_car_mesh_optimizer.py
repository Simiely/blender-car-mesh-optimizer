"""Car Mesh Optimizer v3.0 — 高面车模智能减面

选取特征线 → 调参数 → 一键生成优化网格
Decimate 粗减 + 特征区细分 + Shrinkwrap 包裹，薄壳/实体均可用
"""
bl_info = {
    "name": "Car Mesh Optimizer",
    "author": "Simiely",
    "version": (3, 0, 0),
    "blender": (3, 6, 0),
    "location": "3D 视图 > 右侧边栏 > 车模减面",
    "description": "高面车模智能减面 — 手动或按边长选特征线，Decimate + 细分 + 包裹，一键优化",
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


# ══════════════ 工具 ══════════════

def _active_mesh(ctx):
    obj = ctx.active_object
    return obj if (obj and obj.type == 'MESH') else None

def _tri_count(obj):
    return sum(max(1, len(p.vertices) - 2) for p in obj.data.polygons)

def _sel_edge_count(obj):
    return sum(1 for e in obj.data.edges if e.select)

def _ensure_obj_mode():
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


# ══════════════ KDTree ══════════════

def _build_kdtree(obj):
    pts, idxs = [], []
    for e in obj.data.edges:
        if e.select:
            v0 = obj.data.vertices[e.vertices[0]].co
            v1 = obj.data.vertices[e.vertices[1]].co
            pts.append((v0 + v1) / 2.0)
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
    pts, cnt = [], 0
    for e in obj.data.edges:
        e.select = False
    for e in bm.edges:
        if e.select:
            pts.append((e.verts[0].co + e.verts[1].co) / 2.0)
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


# ══════════════ 引擎 ══════════════

def _shrinkwrap(obj, target, offset=0.0005):
    _ensure_obj_mode()
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    _safe_remove_mods(obj, "CD_SW")
    mod = obj.modifiers.new(name="CD_SW", type='SHRINKWRAP')
    mod.wrap_method = 'PROJECT'
    mod.target = target
    mod.offset = offset
    mod.use_project_x = mod.use_project_y = mod.use_project_z = True
    mod.use_positive_direction = mod.use_negative_direction = True
    bpy.ops.object.modifier_apply(modifier=mod.name)


def _subdivide_edges(bm, edges, cuts):
    for ct in ('INNER_VERT', 'INNER'):
        try:
            bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts,
                use_grid_fill=True, quad_corner_type=ct, smooth=0.0)
            return
        except Exception:
            pass
    raise RuntimeError("subdivide_edges 失败")


def _run_pipeline(orig, f_pct, nf_pct, kdtree):
    """Decimate 粗减 + 特征区细分 + Shrinkwrap"""
    mesh = orig.data.copy()
    mesh.name = orig.data.name + "_tmp"
    robj = bpy.data.objects.new(orig.name + "_tmp", mesh)
    robj.matrix_world = orig.matrix_world.copy()
    bpy.context.collection.objects.link(robj)
    try:
        # 1. 整体粗减
        _ensure_obj_mode()
        bpy.ops.object.select_all(action='DESELECT')
        robj.select_set(True)
        bpy.context.view_layer.objects.active = robj
        mod = robj.modifiers.new(name="CD_Dec", type='DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = min(1.0, max(0.01, nf_pct / 100.0))
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=mod.name)

        # 2. 包裹
        _shrinkwrap(robj, orig, 0.0005)

        # 3. 特征区细分
        bm = bmesh.new()
        bm.from_mesh(robj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        subdiv = max(0, int(f_pct / max(nf_pct, 1)) - 1)
        if subdiv > 0:
            # 按距离标记高密度边
            radius = 0.01  # 固定影响半径
            edge_cuts = {}
            for e in bm.edges:
                m = (e.verts[0].co + e.verts[1].co) / 2.0
                _, _, dist = kdtree.find((m.x, m.y, m.z))
                if dist < radius:
                    edge_cuts[e] = subdiv

            # 分组细分
            groups = {}
            for e, c in edge_cuts.items():
                groups.setdefault(c, []).append(e)
            for cuts, edges in sorted(groups.items()):
                _subdivide_edges(bm, edges, cuts)

        bm.to_mesh(robj.data)
        bm.free()

        # 4. 精修包裹
        _shrinkwrap(robj, orig, 0.0003)

        return robj, _tri_count(robj)
    except Exception:
        if robj:
            for coll in robj.users_collection:
                coll.objects.unlink(robj)
            bpy.data.objects.remove(robj)
        if mesh and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
        raise


# ══════════════ 属性 ══════════════

class CarDecimatorSettings(bpy.types.PropertyGroup):
    feature_keep: FloatProperty(
        name="特征区保留比例", default=30.0, min=1.0, max=100.0,
        subtype='PERCENTAGE',
        description="特征线附近的面保留比例，越高越密")
    nonfeature_keep: FloatProperty(
        name="非特征区保留比例", default=5.0, min=1.0, max=100.0,
        subtype='PERCENTAGE',
        description="远离特征线的面保留比例，越低面越少")
    edge_length_max: FloatProperty(
        name="短边阈值", default=0.05, min=0.001, max=10.0,
        step=0.001, precision=3, subtype='DISTANCE', unit='LENGTH',
        description="长度小于此值的边将被自动选中")
    selected_edge_count: IntProperty(name="已选边数", default=0)
    has_edge_selection: BoolProperty(name="已选取特征线", default=False)
    original_face_count: IntProperty(name="原始面数", default=0)
    original_obj_name: StringProperty(name="原始对象", default="")
    result_face_count: IntProperty(name="结果面数", default=0)
    result_name: StringProperty(name="结果名称", default="")


PRESETS = {
    "DEFAULT": {"name": "默认",   "fv": 30, "nf": 5},
    "HIGH":    {"name": "高精度", "fv": 50, "nf": 10},
    "LOW":     {"name": "低面数", "fv": 15, "nf": 2},
    "BALANCE": {"name": "均衡",   "fv": 25, "nf": 5},
}


def _apply_preset(s, key):
    p = PRESETS.get(key, PRESETS["DEFAULT"])
    s.feature_keep = p["fv"]
    s.nonfeature_keep = p["nf"]


# ══════════════ Operators ══════════════

class CARMESH_OT_prepare(bpy.types.Operator):
    bl_idname = "carmesh.prepare"
    bl_label = "选取特征线"
    bl_description = "进入编辑模式手动选择重要边"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, ctx):
        obj = _active_mesh(ctx)
        if not obj:
            self.report({'ERROR'}, "请先选中一个网格对象")
            return {'CANCELLED'}
        s = ctx.scene.car_decimator
        s.original_face_count = _tri_count(obj)
        s.original_obj_name = obj.name
        s.has_edge_selection = False
        s.selected_edge_count = 0
        s.result_face_count = 0
        s.result_name = ""
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='EDGE')
        self.report({'INFO'}, "选好后切回物体模式，点击确认")
        return {'FINISHED'}


class CARMESH_OT_select_short(bpy.types.Operator):
    bl_idname = "carmesh.select_short"
    bl_label = "按长度选短边"
    bl_description = "自动选中长度小于阈值的边"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, ctx):
        obj = _active_mesh(ctx)
        if not obj:
            self.report({'ERROR'}, "请先选中一个网格对象")
            return {'CANCELLED'}
        t = ctx.scene.car_decimator.edge_length_max
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='EDGE')
        bpy.ops.mesh.select_all(action='DESELECT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        for e in obj.data.edges:
            e.select = False
        cnt = 0
        for e in bm.edges:
            if e.calc_length() < t:
                e.select = True
                if e.index < len(obj.data.edges):
                    obj.data.edges[e.index].select = True
                cnt += 1
        bmesh.update_edit_mesh(obj.data)
        for a in ctx.screen.areas:
            if a.type == 'VIEW_3D':
                a.tag_redraw()
        if cnt == 0:
            self.report({'WARNING'}, f"没有长度 < {t:.3f}m 的边")
        else:
            self.report({'INFO'}, f"已选中 {cnt} 条短边")
        return {'FINISHED'}


class CARMESH_OT_capture(bpy.types.Operator):
    bl_idname = "carmesh.capture"
    bl_label = "确认选取"
    bl_description = "记录当前选中的边作为特征线"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, ctx):
        obj = _active_mesh(ctx)
        if not obj:
            self.report({'ERROR'}, "请先选中一个网格对象")
            return {'CANCELLED'}
        s = ctx.scene.car_decimator
        if obj.mode == 'EDIT':
            _, cnt = _build_kdtree_from_edit(obj)
        else:
            cnt = _sel_edge_count(obj)
        s.selected_edge_count = cnt
        s.has_edge_selection = cnt > 0
        if cnt == 0:
            self.report({'WARNING'}, "未选中任何边")
            return {'CANCELLED'}
        self.report({'INFO'}, f"已记录 {cnt} 条特征边")
        return {'FINISHED'}


class CARMESH_OT_optimize(bpy.types.Operator):
    bl_idname = "carmesh.optimize"
    bl_label = "生成优化网格"
    bl_description = "一键生成优化后的网格"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, ctx):
        obj = _active_mesh(ctx)
        if not obj:
            self.report({'ERROR'}, "请先选中一个网格对象")
            return {'CANCELLED'}
        s = ctx.scene.car_decimator
        if not s.has_edge_selection:
            self.report({'ERROR'}, "请先选取特征线并确认")
            return {'CANCELLED'}
        fp, np_ = s.feature_keep, s.nonfeature_keep
        if fp <= np_:
            self.report({'ERROR'}, f"特征区保留比例({fp:.0f}%)必须大于非特征区({np_:.0f}%)")
            return {'CANCELLED'}
        kdtree, _, _ = _build_kdtree(obj)
        if kdtree is None:
            self.report({'ERROR'}, "特征线数据异常，请重新选取")
            return {'CANCELLED'}
        self.report({'INFO'}, "正在生成...")
        try:
            robj, fc = _run_pipeline(obj, fp, np_, kdtree)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"生成失败: {e}")
            return {'CANCELLED'}
        base = obj.name + "_优化"
        name = base
        i = 1
        while bpy.data.objects.get(name):
            name = f"{base}_{i}"
            i += 1
        robj.name = name
        robj.data.name = name
        robj.display_type = 'SOLID'
        bpy.ops.object.select_all(action='DESELECT')
        robj.select_set(True)
        ctx.view_layer.objects.active = robj
        ofc = s.original_face_count
        s.result_face_count = fc
        s.result_name = name
        s.has_edge_selection = False
        s.selected_edge_count = 0
        msg = f"已生成: {name}, {fc:,} 面"
        if ofc > 0:
            msg += f" (原始 {ofc:,}, -{(1-fc/ofc)*100:.1f}%)"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class CARMESH_OT_preset(bpy.types.Operator):
    bl_idname = "carmesh.preset"
    bl_label = "快速预设"
    bl_options = {'REGISTER', 'UNDO'}
    preset_key: bpy.props.StringProperty()

    def execute(self, ctx):
        _apply_preset(ctx.scene.car_decimator, self.preset_key)
        self.report({'INFO'}, "已应用预设")
        return {'FINISHED'}


# ══════════════ 面板 ══════════════

class CARMESH_PT_main(bpy.types.Panel):
    bl_label = "车模网格减面"
    bl_idname = "CARMESH_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "车模减面"

    def draw(self, ctx):
        layout = self.layout
        try:
            s = ctx.scene.car_decimator
        except AttributeError:
            layout.label(text="插件未正确加载", icon='ERROR')
            return
        obj = _active_mesh(ctx)

        box = layout.box()
        box.label(text="当前模型", icon='OBJECT_DATA')
        if obj is None:
            box.label(text="请选择一个网格对象", icon='ERROR')
            return
        box.label(text=f"名称: {obj.name}")
        box.label(text=f"原始面数: {_tri_count(obj):,}")

        # 选线
        box = layout.box()
        box.label(text="步骤 1  选取特征线", icon='EDGESEL')
        if s.has_edge_selection:
            col = box.column(align=True)
            col.label(text=f"已记录 {s.selected_edge_count} 条", icon='CHECKMARK')
            col.operator("carmesh.prepare", text="重新选取")
        else:
            col = box.column(align=True)
            col.operator("carmesh.prepare", text="手动选取")
            row = col.row(align=True)
            row.prop(s, "edge_length_max", text="短边阈值")
            row.operator("carmesh.select_short", text="", icon='AUTO')
            col.label(text="选好后切回物体模式点确认", icon='INFO')
            cnt = _sel_edge_count(obj)
            if obj.mode == 'EDIT' and cnt == 0:
                bm = bmesh.from_edit_mesh(obj.data)
                cnt = sum(1 for e in bm.edges if e.select)
            if cnt > 0:
                col.separator()
                col.operator("carmesh.capture",
                    text=f"确认选取 ({cnt} 条)", icon='CHECKMARK')

        layout.separator()

        # 参数
        box = layout.box()
        box.label(text="步骤 2  密度参数", icon='PREFERENCES')
        row = box.row(align=True)
        for k, v in PRESETS.items():
            op = row.operator("carmesh.preset", text=v["name"])
            op.preset_key = k
        col = box.column(align=True)
        col.prop(s, "feature_keep", text="特征区保留")
        col.separator()
        col.prop(s, "nonfeature_keep", text="非特征区保留")
        r = s.feature_keep / max(s.nonfeature_keep, 1)
        col.label(text=f"特征区密度是非特征区的 {r:.1f} 倍", icon='SORTSIZE')

        layout.separator()

        # 生成
        box = layout.box()
        box.label(text="步骤 3  生成", icon='RESTRICT_RENDER_OFF')
        col = box.column(align=True)
        col.scale_y = 1.8
        col.operator("carmesh.optimize", text="生成优化网格", icon='CHECKMARK')

        layout.separator()

        if s.result_name:
            box = layout.box()
            box.label(text="上次结果", icon='INFO')
            col = box.column(align=True)
            col.label(text=f"{s.result_name}", icon='OUTLINER_OB_MESH')
            col.label(text=f"{s.result_face_count:,} 面", icon='MESH_DATA')
            ofc = s.original_face_count
            if ofc > 0:
                pct = s.result_face_count / ofc * 100
                col.label(text=f"占比 {pct:.1f}% (-{(100-pct):.1f}%)")


# ══════════════ 注册 ══════════════

CLASSES = (
    CarDecimatorSettings,
    CARMESH_OT_prepare, CARMESH_OT_select_short, CARMESH_OT_capture,
    CARMESH_OT_optimize, CARMESH_OT_preset, CARMESH_PT_main,
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
