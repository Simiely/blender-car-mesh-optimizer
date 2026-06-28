"""法线偏差检测 —— 检测顶点邻域法线变化"""
import bpy
import bmesh
import math
import numpy as np
from mathutils import Vector


def compute_vertex_normals(bm):
    """计算每个顶点的法线（面法线面积加权平均）"""
    n_verts = len(bm.verts)
    normals = np.zeros((n_verts, 3), dtype=np.float32)

    for f in bm.faces:
        fn = np.array(f.normal, dtype=np.float32)
        area = f.calc_area()
        for v in f.verts:
            normals[v.index] += fn * area

    # 归一化
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    lengths = np.where(lengths < 1e-8, 1.0, lengths)
    normals /= lengths

    return normals


def compute_normal_deviation(obj):
    """计算每个顶点的法线偏差

    法线偏差 = 顶点法线与邻域顶点法线之间的最大/平均角度差。
    高偏差意味着该顶点附近有折痕或尖锐特征。

    Returns:
        np.ndarray: 每个顶点的法线偏差，shape (n_verts,)
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    n_verts = len(bm.verts)
    vertex_normals = compute_vertex_normals(bm)
    deviations = np.zeros(n_verts, dtype=np.float32)

    for v in bm.verts:
        vn = vertex_normals[v.index]
        angles = []
        for e in v.link_edges:
            other = e.other_vert(v)
            on = vertex_normals[other.index]
            # 法线夹角
            cos_angle = np.dot(vn, on)
            cos_angle = max(-1.0, min(1.0, cos_angle))
            angle = math.acos(cos_angle)
            angles.append(angle)

        if angles:
            # 使用最大角度差作为偏差
            deviations[v.index] = max(angles)

    bm.free()

    # 归一化
    if deviations.max() > 0:
        deviations = deviations / (deviations.max() + 1e-8)

    return deviations.astype(np.float32)


def compute_sharp_edge_penalty(obj, angle_threshold_deg=30.0):
    """计算尖锐边惩罚 —— 对法线偏差大的顶点施加高权重

    这是法线偏差的增强版，直接映射到 [0, 1] 的惩罚权重。
    """
    deviations = compute_normal_deviation(obj)
    threshold = math.radians(angle_threshold_deg)

    # 超过阈值的直接给满权重，否则线性映射
    penalties = np.minimum(1.0, deviations / (threshold + 1e-8))
    return penalties.astype(np.float32)


def register():
    pass


def unregister():
    pass