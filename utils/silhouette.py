"""轮廓检测 —— 从多视角检测轮廓顶点"""
import bpy
import bmesh
import math
import numpy as np
from mathutils import Vector, Matrix


def compute_silhouette_weights(obj, num_views=8):
    """从多个视角检测轮廓顶点

    使用简单的外积法：对于每条边，如果相邻两个面的法线一个朝向相机、一个背向相机，
    则该边为轮廓边。

    对相机环形采样，统计每个顶点出现在轮廓中的次数。

    Args:
        obj: Blender mesh 对象
        num_views: 采样视角数（默认 8 个，绕水平面均匀分布）

    Returns:
        np.ndarray: 每个顶点的轮廓权重，shape (n_verts,)
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    n_verts = len(bm.verts)
    vertex_silhouette_count = np.zeros(n_verts, dtype=np.float32)

    # 计算模型包围盒中心和半径
    verts_co = np.array([v.co for v in bm.verts], dtype=np.float32)
    center = verts_co.mean(axis=0)
    radius = np.max(np.linalg.norm(verts_co - center, axis=1)) * 2.0

    # 预计算每个面的法线（世界空间）
    # 获取对象的世界矩阵
    world_matrix = np.array(obj.matrix_world)
    face_normals = np.array([f.normal for f in bm.faces], dtype=np.float32)
    # 转换法线到世界空间
    n_faces = len(bm.faces)

    for vi in range(num_views):
        angle = 2.0 * math.pi * vi / num_views
        # 相机位置：绕 Y 轴（上方）旋转
        cam_dir = Vector((math.cos(angle), 0.0, math.sin(angle)))
        cam_pos = center + np.array(cam_dir) * radius

        # 预计算每个面的朝向（点积）
        face_dots = np.zeros(n_faces, dtype=np.float32)
        for fi, f in enumerate(bm.faces):
            centroid = np.array(f.calc_center_median())
            to_cam = cam_pos - centroid
            to_cam = to_cam / (np.linalg.norm(to_cam) + 1e-8)
            face_dots[fi] = np.dot(face_normals[fi], to_cam)

        # 检测轮廓边
        for e in bm.edges:
            link_faces = e.link_faces
            if len(link_faces) != 2:
                continue
            f1, f2 = link_faces
            # 一个面朝相机，一个面背向相机 → 轮廓边
            if face_dots[f1.index] * face_dots[f2.index] < 0:
                vertex_silhouette_count[e.verts[0].index] += 1.0
                vertex_silhouette_count[e.verts[1].index] += 1.0

    bm.free()

    # 归一化到 [0, 1]
    if vertex_silhouette_count.max() > 0:
        vertex_silhouette_count /= vertex_silhouette_count.max()

    return vertex_silhouette_count.astype(np.float32)


def register():
    pass


def unregister():
    pass