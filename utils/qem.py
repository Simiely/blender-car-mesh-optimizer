"""加权 QEM 边塌缩算法

多约束加权 Quadric Error Metric：
  Cost(u, v) = QEM_error + λ₁×Curvature + λ₂×Feature + λ₃×Silhouette
             + λ₄×NormalDev + λ₅×Boundary + λ₆×UserWeight

核心流程：
  1. 计算每个顶点的二次误差矩阵
  2. 应用特征惩罚权重
  3. 贪心边塌缩，始终选择代价最小的边
  4. 塌缩后更新受影响的边
"""
import math
import heapq
import numpy as np
import bmesh
from mathutils import Vector


def compute_face_plane(verts):
    """计算三角形面的平面方程 ax + by + cz + d = 0

    (a, b, c) 是单位法向量，d = -(a·p₀)

    Returns:
        np.ndarray: (a, b, c, d) shape (4,)
    """
    v0, v1, v2 = verts[0], verts[1], verts[2]
    # 法向量
    normal = np.cross(v1 - v0, v2 - v0)
    length = np.linalg.norm(normal)
    if length < 1e-12:
        return np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float64)
    normal = normal / length
    d = -np.dot(normal, v0)
    return np.array([normal[0], normal[1], normal[2], d], dtype=np.float64)


def compute_fundamental_quadric(plane):
    """计算平面的基本二次误差矩阵 K_p = pp^T

    Args:
        plane: (a, b, c, d) shape (4,)

    Returns:
        np.ndarray: 4x4 对称矩阵
    """
    p = plane.reshape(4, 1)
    return np.dot(p, p.T)


def compute_vertex_quadrics(vertices, faces):
    """计算每个顶点的二次误差矩阵 Q_v = Σ K_p (p ∈ adjacent faces)

    Args:
        vertices: (n, 3) numpy array
        faces: list of (v0, v1, v2) index triples

    Returns:
        np.ndarray: (n, 4, 4) quadric matrices
    """
    n = len(vertices)
    quadrics = np.zeros((n, 4, 4), dtype=np.float64)

    for face in faces:
        v0, v1, v2 = face
        plane = compute_face_plane([vertices[v0], vertices[v1], vertices[v2]])
        K = compute_fundamental_quadric(plane)
        quadrics[v0] += K
        quadrics[v1] += K
        quadrics[v2] += K

    return quadrics


def compute_collapse_cost(quadric_u, quadric_v, pos_u, pos_v):
    """计算边塌缩的最优代价

    最优塌缩位置 = Q⁻¹ * [0, 0, 0, 1]^T
    代价 = v_new^T * Q * v_new

    Args:
        quadric_u: (4, 4) quadric of vertex u
        quadric_v: (4, 4) quadric of vertex v
        pos_u: (3,) position of vertex u
        pos_v: (3,) position of vertex v

    Returns:
        (cost, optimal_position)
    """
    Q = quadric_u + quadric_v

    # 尝试求解最优位置
    # 构造 Q_3x3 和 q
    Q3 = Q[:3, :3]
    q = Q[:3, 3]

    # 尝试求逆
    try:
        # 使用 pinv 处理奇异矩阵
        Q3_inv = np.linalg.pinv(Q3)
        pos_new = -np.dot(Q3_inv, q)
    except np.linalg.LinAlgError:
        # 如果不可逆，使用中点
        pos_new = (pos_u + pos_v) / 2.0

    # 计算代价
    v = np.append(pos_new, 1.0)
    cost = np.dot(v, np.dot(Q, v))
    cost = max(0.0, cost)

    return cost, pos_new


def build_edge_list(vertices, faces):
    """从面列表构建边列表

    Returns:
        list of (u, v) tuples, sorted (u < v)
    """
    edges = set()
    for face in faces:
        v0, v1, v2 = sorted(face[:3])
        edges.add((v0, v1))
        edges.add((v0, v2))
        edges.add((v1, v2))
    return list(edges)


def build_vertex_adjacency(edges, n_verts):
    """构建顶点邻接表

    Returns:
        list of set: 每个顶点的邻接顶点集合
    """
    adj = [set() for _ in range(n_verts)]
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    return adj


def build_vertex_faces(faces, n_verts):
    """构建顶点-面映射

    Returns:
        list of set: 每个顶点关联的面索引集合
    """
    vf = [set() for _ in range(n_verts)]
    for fi, face in enumerate(faces):
        for v in face:
            vf[v].add(fi)
    return vf


def run_weighted_qem(
    obj,
    target_face_count,
    vertex_weights=None,
    face_mask=None,
    progress_callback=None,
):
    """执行加权 QEM 边塌缩减面

    Args:
        obj: Blender mesh 对象
        target_face_count: 目标面数
        vertex_weights: 每个顶点的保留权重（0 = 可随意删除，越大越难删）
        face_mask: 允许减面的面索引集合（None = 全部）
        progress_callback: 进度回调 (current, total)

    Returns:
        bool: 是否成功
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    n_verts = len(bm.verts)
    n_faces = len(bm.faces)

    # 如果已经在目标面数以下，直接返回
    current_tris = sum(len(f.verts) - 2 for f in bm.faces)
    if current_tris <= target_face_count:
        bm.free()
        return True

    # 提取顶点和面数据
    vertices = np.array([v.co for v in bm.verts], dtype=np.float64)
    faces = []
    for f in bm.faces:
        if len(f.verts) < 3:
            continue
        # 三角化（取前三个顶点）
        faces.append((f.verts[0].index, f.verts[1].index, f.verts[2].index))
        # 如果有更多顶点，拆分为三角形
        for i in range(2, len(f.verts) - 1):
            faces.append((f.verts[0].index, f.verts[i].index, f.verts[i + 1].index))

    if len(faces) == 0:
        bm.free()
        return False

    # 如果指定了 face_mask，只保留 mask 内的面
    if face_mask is not None:
        faces = [f for fi, f in enumerate(faces) if fi in face_mask]

    # 构建边列表和邻接关系
    edges = build_edge_list(vertices, faces)
    vertex_adj = build_vertex_adjacency(edges, n_verts)
    vertex_faces = build_vertex_faces(faces, n_verts)

    # 计算 QEM quadrics
    quadrics = compute_vertex_quadrics(vertices, faces)

    # 应用顶点权重惩罚
    if vertex_weights is not None:
        # 权重越高，quadric 越大，越难塌缩
        for vi in range(n_verts):
            w = vertex_weights[vi] if vi < len(vertex_weights) else 0.0
            scale = 1.0 + w  # 权重映射到 [1, 1 + max_weight]
            quadrics[vi] *= scale

    # 初始化优先队列
    heap = []
    edge_map = {}  # (u, v) -> (cost, pos_new, valid)

    for ei, (u, v) in enumerate(edges):
        cost, pos_new = compute_collapse_cost(
            quadrics[u], quadrics[v], vertices[u], vertices[v]
        )
        heapq.heappush(heap, (cost, ei, u, v))
        edge_map[(u, v)] = (cost, pos_new, ei)

    # 塌缩状态
    vertex_deleted = np.zeros(n_verts, dtype=bool)
    face_deleted = np.zeros(len(faces), dtype=bool)
    vertex_map = np.arange(n_verts)  # vertex_map[vi] = 当前代表顶点

    # 更新边代价值的函数
    def update_edge(u, v, ei):
        if vertex_deleted[u] or vertex_deleted[v]:
            return
        # 映射到当前代表顶点
        ru = vertex_map[u]
        rv = vertex_map[v]
        if ru == rv:
            return
        cost, pos_new = compute_collapse_cost(
            quadrics[ru], quadrics[rv], vertices[ru], vertices[rv]
        )
        heapq.heappush(heap, (cost, ei, ru, rv))
        edge_map[(ru, rv)] = (cost, pos_new, ei)

    # 主循环
    face_count = current_tris
    target = target_face_count
    iterations = 0
    max_iterations = face_count - target + 1000

    while heap and face_count > target and iterations < max_iterations:
        iterations += 1

        if progress_callback and iterations % 100 == 0:
            progress_callback(iterations, face_count - target)

        cost, ei, u, v = heapq.heappop(heap)

        # 检查边是否仍然有效
        if vertex_deleted[u] or vertex_deleted[v]:
            continue
        if vertex_map[u] != u or vertex_map[v] != v:
            # 顶点已被映射到其他代表
            ru = vertex_map[u]
            rv = vertex_map[v]
            if ru == rv:
                continue
            # 重新计算代价
            new_cost, pos_new = compute_collapse_cost(
                quadrics[ru], quadrics[rv], vertices[ru], vertices[rv]
            )
            if new_cost > cost * 1.1:  # 代价变化较大，重新入队
                heapq.heappush(heap, (new_cost, ei, ru, rv))
                continue
            u, v = ru, rv
            cost = new_cost

        # 执行塌缩：将 v 合并到 u
        # u 的吸收位置
        Q = quadrics[u] + quadrics[v]
        try:
            Q3_inv = np.linalg.pinv(Q[:3, :3])
            pos_new = -np.dot(Q3_inv, Q[:3, 3])
        except np.linalg.LinAlgError:
            pos_new = (vertices[u] + vertices[v]) / 2.0

        vertices[u] = pos_new
        quadrics[u] = Q

        # 删除 v
        vertex_deleted[v] = True
        vertex_map[v] = u

        # 删除 u 和 v 之间的退化面
        for fi in vertex_faces[v]:
            if face_deleted[fi]:
                continue
            f = faces[fi]
            if u in f:
                face_deleted[fi] = True
                face_count -= 1
            else:
                # 更新面的顶点引用
                new_face = tuple(u if x == v else x for x in f)
                faces[fi] = new_face

        # 更新邻接关系
        for w in vertex_adj[v]:
            if vertex_deleted[w]:
                continue
            vertex_adj[u].add(w)
            vertex_adj[w].add(u)
            vertex_adj[w].discard(v)

        vertex_adj[u].discard(v)

        # 更新受影响边的代价
        for w in vertex_adj[u]:
            if not vertex_deleted[w]:
                new_ei = (u, w) if u < w else (w, u)
                update_edge(u, w, ei)

        if face_count <= target:
            break

    # 重建网格
    # 收集存活顶点
    alive_verts = np.where(~vertex_deleted)[0]
    old_to_new = -np.ones(n_verts, dtype=int)
    for new_idx, old_idx in enumerate(alive_verts):
        old_to_new[old_idx] = new_idx

    new_verts = vertices[alive_verts]

    # 收集存活面
    new_faces = []
    for fi, face in enumerate(faces):
        if not face_deleted[fi]:
            new_face = tuple(old_to_new[x] for x in face)
            if len(set(new_face)) == 3:  # 确保不是退化三角形
                new_faces.append(new_face)

    # 写回 Blender mesh
    bm.clear()
    bm_verts = [bm.verts.new(v) for v in new_verts]
    bm.verts.ensure_lookup_table()

    for face in new_faces:
        try:
            bm.faces.new([bm_verts[vi] for vi in face])
        except ValueError:
            continue

    bm.to_mesh(obj.data)
    bm.free()

    return True


def register():
    pass


def unregister():
    pass