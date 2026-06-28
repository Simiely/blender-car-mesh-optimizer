"""Step 3: 特征检测算子"""
import bpy
import numpy as np
from ..utils import mesh_utils, curvature, features, silhouette, normal_deviation


class CAR_DECIMATOR_OT_detect_features(bpy.types.Operator):
    bl_idname = "car_decimator.detect_features"
    bl_label = "检测特征"
    bl_description = "检测曲率、特征边、轮廓、法线偏差等几何特征"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = mesh_utils.get_active_mesh_obj(context)
        if obj is None:
            self.report({'ERROR'}, "请先选择一个 Mesh 对象")
            return {'CANCELLED'}

        settings = context.scene.car_decimator

        self.report({'INFO'}, "正在计算曲率...")

        # 1. 曲率分析
        try:
            curv_weights = curvature.compute_curvature_weights(obj)
            mesh_utils.set_vertex_group_weights(obj, settings.curvature_vg, curv_weights)
            self.report({'INFO'}, "曲率分析完成")
        except Exception as e:
            self.report({'WARNING'}, f"曲率计算失败: {e}")
            curv_weights = np.zeros(len(obj.data.vertices), dtype=np.float32)

        # 2. 特征边检测
        self.report({'INFO'}, "正在检测特征边...")
        try:
            feature_edge_weights = features.compute_feature_edge_weights(
                obj, angle_threshold_deg=settings.feature_edge_angle
            )
        except Exception as e:
            self.report({'WARNING'}, f"特征边检测失败: {e}")
            feature_edge_weights = np.zeros(len(obj.data.vertices), dtype=np.float32)

        # 3. 轮廓检测
        self.report({'INFO'}, "正在检测轮廓...")
        try:
            silhouette_weights = silhouette.compute_silhouette_weights(
                obj, num_views=settings.silhouette_views
            )
        except Exception as e:
            self.report({'WARNING'}, f"轮廓检测失败: {e}")
            silhouette_weights = np.zeros(len(obj.data.vertices), dtype=np.float32)

        # 4. 法线偏差
        self.report({'INFO'}, "正在计算法线偏差...")
        try:
            normal_weights = normal_deviation.compute_normal_deviation(obj)
        except Exception as e:
            self.report({'WARNING'}, f"法线偏差计算失败: {e}")
            normal_weights = np.zeros(len(obj.data.vertices), dtype=np.float32)

        # 5. 材质/UV 边界检测
        self.report({'INFO'}, "正在检测材质边界...")
        try:
            boundary_weights = features.compute_boundary_edge_weights(obj)
        except Exception as e:
            self.report({'WARNING'}, f"边界检测失败: {e}")
            boundary_weights = np.zeros(len(obj.data.vertices), dtype=np.float32)

        # 融合权重：加权求和
        # 最终保留权重 = Σ(λ_i * weight_i)
        combined = (
            settings.curvature_weight * curv_weights
            + settings.feature_edge_weight * feature_edge_weights
            + settings.silhouette_weight * silhouette_weights
            + settings.normal_dev_weight * normal_weights
            + settings.boundary_weight * boundary_weights
        )

        # 归一化
        max_val = combined.max()
        if max_val > 0:
            combined = combined / max_val

        # 存储特征权重
        mesh_utils.set_vertex_group_weights(obj, settings.feature_vg, combined)

        # 可视化：热力图
        try:
            mesh_utils.set_vertex_colors_heatmap(obj, combined, "CD_Features")
        except Exception:
            pass

        settings.is_features_detected = True
        settings.current_step = 'DECIMATE'

        self.report(
            {'INFO'},
            "特征检测完成！曲率 + 特征边 + 轮廓 + 法线偏差 + 边界",
        )

        return {'FINISHED'}


class CAR_DECIMATOR_OT_show_feature(bpy.types.Operator):
    bl_idname = "car_decimator.show_feature"
    bl_label = "显示特征热力图"
    bl_description = "在模型上显示特征热力图蓝色=低权重, 红色=高权重"
    bl_options = {'REGISTER', 'UNDO'}

    feature_type: bpy.props.EnumProperty(
        name="特征类型",
        items=[
            ('COMBINED', "综合", "所有特征融合"),
            ('CURVATURE', "曲率", "曲率热力图"),
            ('FEATURE_EDGE', "特征边", "特征边热力图"),
            ('SILHOUETTE', "轮廓", "轮廓热力图"),
        ],
        default='COMBINED',
    )

    def execute(self, context):
        obj = mesh_utils.get_active_mesh_obj(context)
        if obj is None:
            self.report({'ERROR'}, "请先选择一个 Mesh 对象")
            return {'CANCELLED'}

        settings = context.scene.car_decimator

        vg_map = {
            'COMBINED': settings.feature_vg,
            'CURVATURE': settings.curvature_vg,
        }

        vg_name = vg_map.get(self.feature_type, settings.feature_vg)
        weights = mesh_utils.get_vertex_group_weights(obj, vg_name)

        if not weights:
            self.report({'WARNING'}, "请先执行特征检测")
            return {'CANCELLED'}

        all_weights = np.zeros(len(obj.data.vertices), dtype=np.float32)
        for vi, w in weights.items():
            all_weights[vi] = w

        mesh_utils.set_vertex_colors_heatmap(obj, all_weights, "CD_Display")

        self.report({'INFO'}, "热力图已更新")
        return {'FINISHED'}


CLASSES = [
    CAR_DECIMATOR_OT_detect_features,
    CAR_DECIMATOR_OT_show_feature,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)