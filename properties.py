"""插件属性定义 —— 存储在 Blender Scene 上的全局设置"""
import bpy
from bpy.props import (
    IntProperty,
    FloatProperty,
    BoolProperty,
    EnumProperty,
    FloatVectorProperty,
    StringProperty,
    CollectionProperty,
    PointerProperty,
)


class CarDecimatorZone(bpy.types.PropertyGroup):
    """单个分区属性"""
    name: StringProperty(name="分区名", default="")
    face_count: IntProperty(name="面数", default=0)
    face_budget: IntProperty(name="目标面数", default=0)
    budget_ratio: FloatProperty(name="预算占比", default=33.0, min=0.0, max=100.0, subtype='PERCENTAGE')


class CarDecimatorSettings(bpy.types.PropertyGroup):
    """插件全局设置 —— 挂载到 bpy.types.Scene"""

    # ========== 基础信息 ==========
    target_face_count: IntProperty(
        name="目标总面数",
        default=200000,
        min=1000,
        max=10000000,
        description="最终期望的面数",
    )

    original_face_count: IntProperty(name="原始面数", default=0)

    # ========== 分区预算 ==========
    exterior_ratio: IntProperty(
        name="外饰占比",
        default=75,
        min=0,
        max=100,
        subtype='PERCENTAGE',
        description="外饰在总面数预算中的占比",
    )
    interior_ratio: IntProperty(
        name="内饰占比",
        default=17,
        min=0,
        max=100,
        subtype='PERCENTAGE',
    )
    chassis_ratio: IntProperty(
        name="底盘占比",
        default=8,
        min=0,
        max=100,
        subtype='PERCENTAGE',
    )

    zones: CollectionProperty(type=CarDecimatorZone)

    # ========== 特征权重 (λ 参数) ==========
    curvature_weight: FloatProperty(
        name="曲率权重",
        default=2.0,
        min=0.0,
        max=10.0,
        description="λ₁ 曲率惩罚系数",
    )
    feature_edge_weight: FloatProperty(
        name="特征边权重",
        default=20.0,
        min=0.0,
        max=100.0,
        description="λ₂ 特征边惩罚系数（极高值保护特征线）",
    )
    silhouette_weight: FloatProperty(
        name="轮廓权重",
        default=5.0,
        min=0.0,
        max=20.0,
        description="λ₃ 轮廓惩罚系数",
    )
    normal_dev_weight: FloatProperty(
        name="法线偏差权重",
        default=3.0,
        min=0.0,
        max=10.0,
        description="λ₄ 法线偏差惩罚系数",
    )
    boundary_weight: FloatProperty(
        name="边界权重",
        default=20.0,
        min=0.0,
        max=100.0,
        description="λ₅ 材质/UV边界惩罚系数",
    )
    user_weight_mult: FloatProperty(
        name="用户权重倍数",
        default=1.0,
        min=0.0,
        max=10.0,
        description="λ₆ 用户权重倍乘系数",
    )

    # ========== 减面参数 ==========
    coarse_exterior_ratio: FloatProperty(
        name="外饰粗减比",
        default=0.50,
        min=0.0,
        max=1.0,
        description="Phase 1 外饰减面比例",
    )
    coarse_interior_ratio: FloatProperty(
        name="内饰粗减比",
        default=0.90,
        min=0.0,
        max=1.0,
    )
    coarse_chassis_ratio: FloatProperty(
        name="底盘粗减比",
        default=0.90,
        min=0.0,
        max=1.0,
    )

    # ========== 特征检测参数 ==========
    feature_edge_angle: FloatProperty(
        name="特征边角度",
        default=30.0,
        min=0.0,
        max=180.0,
        subtype='ANGLE',
        description="判定特征边的二面角阈值（度）",
    )
    silhouette_views: IntProperty(
        name="轮廓采样视角",
        default=8,
        min=4,
        max=32,
        description="轮廓检测的采样视角数",
    )

    # ========== 状态标记 ==========
    is_analyzed: BoolProperty(name="已分析", default=False)
    is_classified: BoolProperty(name="已分类", default=False)
    is_features_detected: BoolProperty(name="已检测特征", default=False)
    is_decimated: BoolProperty(name="已减面", default=False)

    # 当前步骤
    current_step: EnumProperty(
        name="当前步骤",
        items=[
            ('ANALYZE', "分析", "分析模型基本信息"),
            ('CLASSIFY', "分类", "自动分类外饰/内饰/底盘"),
            ('FEATURES', "特征", "检测几何特征"),
            ('DECIMATE', "减面", "执行减面"),
            ('RESULT', "结果", "检查结果"),
        ],
        default='ANALYZE',
    )

    # 对应的顶点组名
    exterior_vg: StringProperty(name="外饰顶点组", default="CD_Exterior")
    interior_vg: StringProperty(name="内饰顶点组", default="CD_Interior")
    chassis_vg: StringProperty(name="底盘顶点组", default="CD_Chassis")
    weight_vg: StringProperty(name="保留权重组", default="CD_PreserveWeight")
    feature_vg: StringProperty(name="特征权重组", default="CD_FeatureWeight")
    curvature_vg: StringProperty(name="曲率权重组", default="CD_CurvatureWeight")
    error_vg: StringProperty(name="误差组", default="CD_Error")


CLASSES = [
    CarDecimatorZone,
    CarDecimatorSettings,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.car_decimator = PointerProperty(type=CarDecimatorSettings)


def unregister():
    del bpy.types.Scene.car_decimator
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)