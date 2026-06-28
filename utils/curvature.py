"""曲率分析 —— 计算每个顶点的离散曲率"""
import bpy
import bmesh
import math
import numpy as np
from mathutils import Vector


def compute_mean_curvature(obj):
    """计算每个顶点的平均曲率（Mean Curvature）

    使用离散拉普拉斯-贝尔特拉米算子近似：
    H(v_i) ≈ 0.5 * || Δv_i ||
    其中 Δv_i 是顶点 v_i 的离散拉普拉斯

    Returns:
        np.ndarray: 每个顶点的曲率值，shape (n_verts,)
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    n_verts = len(bm.verts)
    curvatures = np.zeros(n_verts, dtype=np.float32)

    for v in bm.verts:
        if not v.link_faces:
            continue

        laplacian = Vector((0.0, 0.0, 0.0))
        total_weight = 0.0

        # 使用 cotangent 权重计算拉普拉斯
        for edge in v.link_edges:
            other = edge.other_vert(v)
            # 获取与该边相邻的两个面
            link_faces = edge.link_faces
            if len(link_faces) < 2:
                continue

            cot_sum = 0.0
            for f in link_faces:
                # 找到该面中不是 v 也不是 other 的顶点
                for fv in f.verts:
                    if fv != v and fv != other:
                        # 计算 cot(angle at fv)
                        a = (other.co - fv.co).length
                        b = (v.co - fv.co).length
                        c = (v.co - other.co).length
                        # cos(angle) = (a² + b² - c²) / (2ab)
                        cos_angle = (a * a + b * b - c * c) / (2.0 * a * b + 1e-10)
                        cos_angle = max(-1.0, min(1.0, cos_angle))
                        sin_angle = math.sqrt(max(0.0, 1.0 - cos_angle * cos_angle))
                        if sin_angle > 1e-8:
                            cot_sum += cos_angle / sin_angle
                        break

            if cot_sum > 0:
                laplacian += cot_sum * (other.co - v.co)
                total_weight += cot_sum

        if total_weight > 0:
            laplacian /= total_weight
            curvatures[v.index] = laplacian.length

    bm.free()

    # 归一化到 [0, 1]
    if curvatures.max() > 0:
        curvatures = curvatures / (curvatures.max() + 1e-8)

    return curvatures


def compute_gaussian_curvature(obj):
    """计算高斯曲率的近似

    K(v) ≈ (2π - Σθ_i) / A_v
    其中 θ_i 是顶点相邻面的内角，A_v 是 Voronoi 面积

    Returns:
        np.ndarray: 每个顶点的高斯曲率，shape (n_verts,)
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    n_verts = len(bm.verts)
    curvatures = np.zeros(n_verts, dtype=np.float32)

    for v in bm.verts:
        if not v.link_faces:
            continue

        angle_sum = 0.0
        area_sum = 0.0

        for f in v.link_faces:
            # 计算该顶点在该面中的内角
            f_verts = f.verts[:]
            vi = f_verts.index(v)
            v_prev = f_verts[(vi - 1) % len(f_verts)]
            v_next = f_verts[(vi + 1) % len(f_verts)]

            a = (v_prev.co - v.co).length
            b = (v_next.co - v.co).length
            c = (v_prev.co - v_next.co).length

            # cos(angle) = (a² + b² - c²) / (2ab)
            cos_angle = (a * a + b * b - c * c) / (2.0 * a * b + 1e-10)
            cos_angle = max(-1.0, min(1.0, cos_angle))
            angle = math.acos(cos_angle)
            angle_sum += angle

            # 三角面面积近似
            area = 0.5 * abs(a * b * math.sin(angle))
            area_sum += area / 3.0  # Voronoi 近似

        if area_sum > 1e-8:
            curvatures[v.index] = abs(2.0 * math.pi - angle_sum) / area_sum

    bm.free()

    # 归一化
    if curvatures.max() > 0:
        curvatures = curvatures / (curvatures.max() + 1e-8)

    return curvatures


def compute_curvature_weights(obj):
    """计算综合曲率权重 —— 平均曲率 + 高斯曲率归一化融合

    Returns:
        np.ndarray: 每个顶点的曲率权重，shape (n_verts,)
    """
    mean_curv = compute_mean_curvature(obj)
    gauss_curv = compute_gaussian_curvature(obj)

    # 融合：平均曲率 + 高斯曲率，各占 50%
    combined = 0.5 * mean_curv + 0.5 * gauss_curv

    if combined.max() > 0:
        combined = combined / (combined.max() + 1e-8)

    return combined.astype(np.float32)


def register():
    pass


def unregister():
    pass