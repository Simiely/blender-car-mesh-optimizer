"""Step 2: 自动分类算子"""
import bpy
from ..utils import mesh_utils, classification


class CAR_DECIMATOR_OT_classify(bpy.types.Operator):
    bl_idname = "car_decimator.classify"
    bl_label = "自动分类"
    bl_description = "自动将模型分为外饰、内饰、底盘三个区域"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = mesh_utils.get_active_mesh_obj(context)
        if obj is None:
            self.report({'ERROR'}, "请先选择一个 Mesh 对象")
            return {'CANCELLED'}

        settings = context.scene.car_decimator

        self.report({'INFO'}, "正在分析材质并检测遮挡...")

        # 执行分类
        result = classification.classify_mesh(obj, use_occlusion=True)

        # 统计
        exterior_count = sum(1 for v in result.values() if v == "EXTERIOR")
        interior_count = sum(1 for v in result.values() if v == "INTERIOR")
        chassis_count = sum(1 for v in result.values() if v == "CHASSIS")
        total = len(result)

        # 创建顶点组
        vg_exterior = mesh_utils.get_vertex_group(obj, settings.exterior_vg, create_if_missing=True)
        vg_interior = mesh_utils.get_vertex_group(obj, settings.interior_vg, create_if_missing=True)
        vg_chassis = mesh_utils.get_vertex_group(obj, settings.chassis_vg, create_if_missing=True)

        # 清空旧数据
        for vg in [vg_exterior, vg_interior, vg_chassis]:
            if vg:
                for v in obj.data.vertices:
                    try:
                        vg.remove([v.index])
                    except RuntimeError:
                        pass

        # 设置权重
        for vi, zone in result.items():
            if zone == "EXTERIOR":
                vg_exterior.add([vi], 1.0, 'REPLACE')
            elif zone == "INTERIOR":
                vg_interior.add([vi], 1.0, 'REPLACE')
            elif zone == "CHASSIS":
                vg_chassis.add([vi], 1.0, 'REPLACE')

        # 可视化分类结果
        # 外饰=蓝, 内饰=绿, 底盘=黄
        try:
            color_layer = mesh_utils.ensure_vertex_color_layer(obj, "CD_Classification")
            color_data = color_layer.data
            for vi, zone in result.items():
                if vi < len(color_data):
                    if zone == "EXTERIOR":
                        color_data[vi].color = (0.2, 0.4, 0.9, 1.0)
                    elif zone == "INTERIOR":
                        color_data[vi].color = (0.2, 0.8, 0.3, 1.0)
                    else:
                        color_data[vi].color = (0.9, 0.7, 0.2, 1.0)
        except Exception:
            pass

        settings.is_classified = True
        settings.current_step = 'FEATURES'

        self.report(
            {'INFO'},
            f"分类完成：外饰 {exterior_count}({exterior_count*100//total}%) / "
            f"内饰 {interior_count}({interior_count*100//total}%) / "
            f"底盘 {chassis_count}({chassis_count*100//total}%)",
        )

        return {'FINISHED'}


CLASSES = [
    CAR_DECIMATOR_OT_classify,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)