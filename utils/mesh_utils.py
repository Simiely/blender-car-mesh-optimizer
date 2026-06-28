"""网格通用工具函数"""
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix


def get_active_mesh_obj(context):
    """获取当前活动的 mesh 对象"""
    obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return None
    return obj


def get_bmesh_from_object(obj):
    """从对象获取 bmesh（需要处于编辑模式或使用临时 bmesh）"""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    return bm


def write_bmesh_to_object(bm, obj):
    """将 bmesh 写回对象"""
    bm.to_mesh(obj.data)
    bm.free()


def get_vertex_group(obj, name, create_if_missing=False):
    """获取或创建顶点组"""
    vg = obj.vertex_groups.get(name)
    if vg is None and create_if_missing:
        vg = obj.vertex_groups.new(name=name)
    return vg


def set_vertex_group_weights(obj, vg_name, weights, vert_indices=None):
    """批量设置顶点组权重"""
    vg = get_vertex_group(obj, vg_name, create_if_missing=True)
    if vg is None:
        return

    if vert_indices is None:
        vert_indices = range(len(weights))

    for i, w in zip(vert_indices, weights):
        if w > 0:
            vg.add([i], w, 'REPLACE')
        else:
            vg.remove([i])


def get_vertex_group_weights(obj, vg_name):
    """获取顶点组的所有权重"""
    vg = get_vertex_group(obj, vg_name)
    if vg is None:
        return {}

    weights = {}
    for v in obj.data.vertices:
        try:
            w = vg.weight(v.index)
            if w > 0:
                weights[v.index] = w
        except RuntimeError:
            pass
    return weights


def ensure_vertex_color_layer(obj, name="CD_Display"):
    """确保存在顶点色层，用于可视化"""
    if name not in obj.data.color_attributes:
        obj.data.color_attributes.new(name=name, type='FLOAT_COLOR', domain='POINT')
    return obj.data.color_attributes[name]


def set_vertex_colors_heatmap(obj, values, layer_name="CD_Display"):
    """将值映射为热力图颜色写入顶点色层"""
    color_layer = ensure_vertex_color_layer(obj, layer_name)
    values = np.array(values, dtype=np.float32)

    if len(values) == 0:
        return

    vmin, vmax = np.min(values), np.max(values)
    if vmax - vmin < 1e-8:
        vmax = vmin + 1.0

    normalized = (values - vmin) / (vmax - vmin)

    # 蓝(0,0,1) → 青(0,1,1) → 绿(0,1,0) → 黄(1,1,0) → 红(1,0,0)
    colors = np.zeros((len(values), 4), dtype=np.float32)
    for i, t in enumerate(normalized):
        if t < 0.25:
            r, g, b = 0.0, t * 4.0, 1.0
        elif t < 0.5:
            r, g, b = 0.0, 1.0, 1.0 - (t - 0.25) * 4.0
        elif t < 0.75:
            r, g, b = (t - 0.5) * 4.0, 1.0, 0.0
        else:
            r, g, b = 1.0, 1.0 - (t - 0.75) * 4.0, 0.0
        colors[i] = (r, g, b, 1.0)

    domain_data = color_layer.data
    for i, col in enumerate(colors):
        if i < len(domain_data):
            domain_data[i].color = col


def clear_vertex_group(obj, vg_name):
    """清空顶点组"""
    vg = obj.vertex_groups.get(vg_name)
    if vg:
        obj.vertex_groups.remove(vg)


def merge_vertex_groups_multiply(obj, vg_names, output_name):
    """将多个顶点组的权重相乘，输出到新顶点组"""
    clear_vertex_group(obj, output_name)
    out_vg = obj.vertex_groups.new(name=output_name)

    if not vg_names:
        return

    # 获取所有顶点索引
    all_verts = set()
    for name in vg_names:
        vg = obj.vertex_groups.get(name)
        if vg:
            for v in obj.data.vertices:
                try:
                    if vg.weight(v.index) > 0:
                        all_verts.add(v.index)
                except RuntimeError:
                    pass

    for vi in all_verts:
        w = 1.0
        for name in vg_names:
            vg = obj.vertex_groups.get(name)
            if vg:
                try:
                    w *= vg.weight(vi)
                except RuntimeError:
                    w = 0
                    break
        if w > 0:
            out_vg.add([vi], w, 'REPLACE')


def get_face_count(obj):
    """获取对象的三角面数"""
    bm = get_bmesh_from_object(obj)
    bm.faces.ensure_lookup_table()
    # 统计三角面数
    count = 0
    for f in bm.faces:
        count += len(f.verts) - 2
    bm.free()
    return count


def get_vertex_count(obj):
    """获取顶点数"""
    return len(obj.data.vertices)


def get_material_names(obj):
    """获取对象的所有材质名"""
    return [mat.name for mat in obj.data.materials if mat is not None]


def clone_object(obj, suffix="_decimated"):
    """复制对象"""
    new_obj = obj.copy()
    new_obj.data = obj.data.copy()
    new_obj.name = obj.name + suffix
    obj.users_collection[0].objects.link(new_obj)
    return new_obj