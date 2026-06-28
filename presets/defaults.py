"""预设参数 —— 不同车型的默认配置"""
import bpy


PRESETS = {
    "DEFAULT": {
        "name": "默认",
        "description": "通用车模预设",
        "target_face_count": 200000,
        "exterior_ratio": 75,
        "interior_ratio": 17,
        "chassis_ratio": 8,
        "curvature_weight": 2.0,
        "feature_edge_weight": 20.0,
        "silhouette_weight": 5.0,
        "normal_dev_weight": 3.0,
        "boundary_weight": 20.0,
        "coarse_exterior_ratio": 0.50,
        "coarse_interior_ratio": 0.90,
        "coarse_chassis_ratio": 0.90,
        "feature_edge_angle": 30.0,
        "silhouette_views": 8,
    },
    "SEDAN": {
        "name": "轿车",
        "description": "三厢轿车，车身面板曲率平缓",
        "target_face_count": 200000,
        "exterior_ratio": 78,
        "interior_ratio": 15,
        "chassis_ratio": 7,
        "curvature_weight": 2.0,
        "feature_edge_weight": 25.0,
        "silhouette_weight": 5.0,
        "normal_dev_weight": 2.5,
        "boundary_weight": 20.0,
        "coarse_exterior_ratio": 0.55,
        "coarse_interior_ratio": 0.90,
        "coarse_chassis_ratio": 0.90,
        "feature_edge_angle": 28.0,
        "silhouette_views": 8,
    },
    "SUV": {
        "name": "SUV",
        "description": "SUV，车身较高，轮廓更方正",
        "target_face_count": 200000,
        "exterior_ratio": 75,
        "interior_ratio": 17,
        "chassis_ratio": 8,
        "curvature_weight": 2.5,
        "feature_edge_weight": 20.0,
        "silhouette_weight": 6.0,
        "normal_dev_weight": 3.0,
        "boundary_weight": 20.0,
        "coarse_exterior_ratio": 0.50,
        "coarse_interior_ratio": 0.90,
        "coarse_chassis_ratio": 0.90,
        "feature_edge_angle": 32.0,
        "silhouette_views": 10,
    },
    "SPORTS": {
        "name": "跑车",
        "description": "跑车，曲面复杂，特征线丰富",
        "target_face_count": 250000,
        "exterior_ratio": 82,
        "interior_ratio": 12,
        "chassis_ratio": 6,
        "curvature_weight": 3.0,
        "feature_edge_weight": 30.0,
        "silhouette_weight": 5.0,
        "normal_dev_weight": 3.5,
        "boundary_weight": 25.0,
        "coarse_exterior_ratio": 0.45,
        "coarse_interior_ratio": 0.92,
        "coarse_chassis_ratio": 0.92,
        "feature_edge_angle": 25.0,
        "silhouette_views": 12,
    },
    "AGGRESSIVE": {
        "name": "激进减面",
        "description": "极限减面，最小面数优先",
        "target_face_count": 100000,
        "exterior_ratio": 70,
        "interior_ratio": 20,
        "chassis_ratio": 10,
        "curvature_weight": 1.5,
        "feature_edge_weight": 15.0,
        "silhouette_weight": 4.0,
        "normal_dev_weight": 2.0,
        "boundary_weight": 15.0,
        "coarse_exterior_ratio": 0.65,
        "coarse_interior_ratio": 0.95,
        "coarse_chassis_ratio": 0.95,
        "feature_edge_angle": 35.0,
        "silhouette_views": 6,
    },
}


def get_preset_items():
    """返回 EnumProperty items 格式的预设列表"""
    return [(key, val["name"], val["description"]) for key, val in PRESETS.items()]


def apply_preset(context, preset_key):
    """将预设参数应用到当前场景"""
    settings = context.scene.car_decimator
    preset = PRESETS.get(preset_key, PRESETS["DEFAULT"])

    for key, value in preset.items():
        if key in ("name", "description"):
            continue
        if hasattr(settings, key):
            setattr(settings, key, value)


def register():
    pass


def unregister():
    pass