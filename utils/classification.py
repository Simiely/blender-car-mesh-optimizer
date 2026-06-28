"""自动分类 —— 将车模分为外饰、内饰、底盘"""
import bpy
import bmesh
import math
import numpy as np
from mathutils import Vector, Matrix


# 分类关键词
EXTERIOR_KEYWORDS = [
    "body", "exterior", "paint", "panel", "door", "hood", "bonnet",
    "fender", "bumper", "trunk", "boot", "roof", "spoiler", "wing",
    "mirror", "headlight", "taillight", "grill", "grille", "badge",
    "window_frame", "trim", "molding", "pillar", "quarter",
    "车身", "外饰", "车漆", "车门", "引擎盖", "翼子板", "保险杠",
    "后备箱", "车顶", "扰流板", "后视镜", "大灯", "尾灯", "格栅",
]

INTERIOR_KEYWORDS = [
    "interior", "dash", "dashboard", "seat", "steering", "wheel",
    "carpet", "headliner", "console", "door_panel", "door_card",
    "pedal", "shifter", "gauge", "cluster", "vent", "handle",
    "内饰", "仪表", "座椅", "方向盘", "地毯", "顶棚", "中控",
    "门板", "踏板", "换挡", "仪表盘", "出风口", "拉手",
]

CHASSIS_KEYWORDS = [
    "chassis", "frame", "suspension", "exhaust", "engine", "motor",
    "drivetrain", "axle", "brake", "rotor", "caliper", "tire",
    "wheel_", "rim", "undercarriage", "floor", "underbody",
    "底盘", "车架", "悬挂", "排气", "引擎", "发动机", "驱动",
    "车轴", "刹车", "轮胎", "轮毂", "底", "地板",
]

GLASS_KEYWORDS = [
    "glass", "window", "windshield", "windscreen", "玻璃", "窗", "挡风",
]


def classify_by_material(material_name):
    """根据材质名称分类"""
    name_lower = material_name.lower().replace(" ", "_").replace("-", "_")

    # 玻璃默认归为外饰（不影响视觉）
    for kw in GLASS_KEYWORDS:
        if kw.lower() in name_lower:
            return "EXTERIOR"

    for kw in INTERIOR_KEYWORDS:
        if kw.lower() in name_lower:
            return "INTERIOR"

    for kw in CHASSIS_KEYWORDS:
        if kw.lower() in name_lower:
            return "CHASSIS"

    for kw in EXTERIOR_KEYWORDS:
        if kw.lower() in name_lower:
            return "EXTERIOR"

    return "UNKNOWN"


def classify_by_occlusion(obj, num_rays=100):
    """通过遮挡检测辅助分类

    从外部多方向发射射线，打不到的顶点更可能是内饰或底盘。

    Returns:
        np.ndarray: 每个顶点的可见性分数 [0, 1]，1 = 完全可见（外饰）
    """
    # 获取世界空间顶点位置
    world_matrix = np.array(obj.matrix_world)
    verts_local = np.array([v.co for v in obj.data.vertices], dtype=np.float32)
    verts_world = verts_local.copy()
    for i in range(len(verts_world)):
        verts_world[i] = world_matrix[:3, :3] @ verts_local[i] + world_matrix[:3, 3]

    # 中心
    center = verts_world.mean(axis=0)
    radius = np.max(np.linalg.norm(verts_world - center, axis=1)) * 1.5

    n_verts = len(verts_world)
    visibility = np.zeros(n_verts, dtype=np.float32)

    # 从均匀分布的球面方向发射射线
    # 使用斐波那契球面分布
    phi = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(num_rays):
        y = 1.0 - (i / float(num_rays - 1)) * 2.0
        radius_at_y = math.sqrt(1.0 - y * y)
        theta = phi * i

        direction = Vector((
            math.cos(theta) * radius_at_y,
            y,
            math.sin(theta) * radius_at_y,
        ))

        ray_origin = center + np.array(direction) * radius

        # 对每个顶点，检查是否被遮挡
        # 简化：使用 BVH 树进行射线检测
        # 这里使用 Blender 的 ray_cast
        scene = bpy.context.scene
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)

        # 批量射线检测较慢，改为采样
        # 对该方向，找最外层顶点
        for vi in range(n_verts):
            v_pos = Vector(verts_world[vi])
            ray_dir = (ray_origin - v_pos).normalized()
            # 从顶点稍微向外的位置发射射线，检查是否被遮挡
            hit, loc, normal, face_index = scene.ray_cast(
                depsgraph, v_pos + ray_dir * 0.001, ray_dir, distance=radius * 3
            )
            if not hit:
                visibility[vi] += 1.0

    visibility /= num_rays
    return visibility.astype(np.float32)


def classify_mesh(obj, use_occlusion=True):
    """综合分类：材质名 + 遮挡检测

    Returns:
        dict: vertex_index -> 'EXTERIOR' | 'INTERIOR' | 'CHASSIS'
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    n_verts = len(bm.verts)

    # 材质分类
    material_classification = {}
    face_to_zone = {}
    for f in bm.faces:
        if f.material_index < len(obj.data.materials):
            mat_name = obj.data.materials[f.material_index].name if obj.data.materials[f.material_index] else ""
        else:
            mat_name = ""
        zone = classify_by_material(mat_name)
        face_to_zone[f.index] = zone

    # 顶点投票
    vertex_votes = {vi: {"EXTERIOR": 0, "INTERIOR": 0, "CHASSIS": 0, "UNKNOWN": 0}
                    for vi in range(n_verts)}
    for f in bm.faces:
        zone = face_to_zone.get(f.index, "UNKNOWN")
        for v in f.verts:
            vertex_votes[v.index][zone] += 1

    # 遮挡检测
    if use_occlusion:
        try:
            visibility = classify_by_occlusion(obj)
        except Exception:
            visibility = np.ones(n_verts, dtype=np.float32)
    else:
        visibility = np.ones(n_verts, dtype=np.float32)

    # 综合判定
    result = {}
    for vi in range(n_verts):
        votes = vertex_votes[vi]
        # 如果已知材质有明确分类，优先使用
        total_known = votes["EXTERIOR"] + votes["INTERIOR"] + votes["CHASSIS"]
        if total_known > 0:
            # 按已知材质投票
            best = max(["EXTERIOR", "INTERIOR", "CHASSIS"], key=lambda k: votes[k])
            result[vi] = best
        elif visibility[vi] > 0.5:
            result[vi] = "EXTERIOR"  # 高可见性 → 外饰
        elif visibility[vi] > 0.2:
            result[vi] = "INTERIOR"
        else:
            result[vi] = "CHASSIS"

    bm.free()
    return result


def register():
    pass


def unregister():
    pass