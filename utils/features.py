"""特征边检测 —— 检测折痕、缝隙等特征边"""
import bpy
import bmesh
import math
import numpy as np
from mathutils import Vector


def compute_dihedral_angles(obj):
    """计算每条边的二面角（dihedral angle）

    Returns:
        np.ndarray: 每条边的二面角（弧度），shape (n_edges,)
        dict: edge_index -> list of face indices
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    n_edges = len(bm.edges)
    angles = np.zeros(n_edges, dtype=np.float32)

    for e in bm.edges:
        link_faces = e.link_faces
        if len(link_faces) == 2:
            f1, f2 = link_faces
            # 计算两个面的法线夹角
            angle = f1.normal.angle(f2.normal)
            angles[e.index] = angle
        elif len(link_faces) == 1:
            # 边界边，标记为特征边
            angles[e.index] = math.pi
        else:
            angles[e.index] = 0.0

    bm.free()
    return angles


def compute_feature_edge_weights(obj, angle_threshold_deg=30.0):
    """计算特征边权重

    检测二面角大于阈值的边，这些边通常是车身的特征线（腰线、门缝等）。

    Args:
        obj: Blender mesh 对象
        angle_threshold_deg: 二面角阈值（度）

    Returns:
        np.ndarray: 每个顶点的特征边权重，shape (n_verts,)
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    n_verts = len(bm.verts)
    angle_threshold = math.radians(angle_threshold_deg)

    # 计算每条边的二面角
    edge_angles = np.zeros(len(bm.edges), dtype=np.float32)
    for e in bm.edges:
        link_faces = e.link_faces
        if len(link_faces) == 2:
            angle = link_faces[0].normal.angle(link_faces[1].normal)
            edge_angles[e.index] = angle
        elif len(link_faces) == 1:
            edge_angles[e.index] = math.pi

    # 对每个顶点，取相连边中最大的二面角作为权重
    vertex_weights = np.zeros(n_verts, dtype=np.float32)
    for v in bm.verts:
        max_angle = 0.0
        for e in v.link_edges:
            if edge_angles[e.index] > max_angle:
                max_angle = edge_angles[e.index]
        # 超过阈值才给权重
        if max_angle > angle_threshold:
            vertex_weights[v.index] = min(1.0, max_angle / math.pi)

    bm.free()
    return vertex_weights


def compute_boundary_edge_weights(obj):
    """检测材质和 UV 边界

    在材质边界或 UV 接缝上的顶点，不允许被塌缩。

    Returns:
        np.ndarray: 每个顶点的边界权重，shape (n_verts,)
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    # 确保有材质数据
    bm.faces.ensure_lookup_table()

    n_verts = len(bm.verts)
    vertex_weights = np.zeros(n_verts, dtype=np.float32)

    # 检测材质边界
    for e in bm.edges:
        link_faces = e.link_faces
        if len(link_faces) == 2:
            if link_faces[0].material_index != link_faces[1].material_index:
                # 材质边界边
                vertex_weights[e.verts[0].index] = 1.0
                vertex_weights[e.verts[1].index] = 1.0
        elif len(link_faces) == 1:
            # 网格边界
            vertex_weights[e.verts[0].index] = 1.0
            vertex_weights[e.verts[1].index] = 1.0

    # 检测 UV 接缝
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is not None:
        for e in bm.edges:
            if vertex_weights[e.verts[0].index] >= 1.0:
                continue
            link_faces = e.link_faces
            if len(link_faces) != 2:
                continue
            # 检查 UV 是否连续
            uv_coords = {}  # vert_index -> set of uv coords
            for f in link_faces:
                for loop in f.loops:
                    uv = loop[uv_layer].uv
                    vi = loop.vert.index
                    uv_tuple = (round(uv.x, 6), round(uv.y, 6))
                    if vi not in uv_coords:
                        uv_coords[vi] = set()
                    uv_coords[vi].add(uv_tuple)

            for vi in (e.verts[0].index, e.verts[1].index):
                if len(uv_coords.get(vi, set())) > 1:
                    vertex_weights[vi] = 1.0

    bm.free()
    return vertex_weights


def register():
    pass


def unregister():
    pass