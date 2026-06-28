"""Step 1: 模型分析算子"""
import bpy
from ..utils import mesh_utils


class CAR_DECIMATOR_OT_analyze(bpy.types.Operator):
    bl_idname = "car_decimator.analyze"
    bl_label = "分析模型"
    bl_description = "分析当前模型的顶点数、面数、材质等基本信息"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = mesh_utils.get_active_mesh_obj(context)
        if obj is None:
            self.report({'ERROR'}, "请先选择一个 Mesh 对象")
            return {'CANCELLED'}

        settings = context.scene.car_decimator

        settings.original_face_count = mesh_utils.get_face_count(obj)
        vert_count = mesh_utils.get_vertex_count(obj)
        mat_names = mesh_utils.get_material_names(obj)

        settings.is_analyzed = True
        settings.current_step = 'CLASSIFY'

        self.report(
            {'INFO'},
            f"分析完成：{vert_count} 顶点, "
            f"{settings.original_face_count} 面, "
            f"{len(mat_names)} 材质",
        )

        return {'FINISHED'}


class CAR_DECIMATOR_OT_reset(bpy.types.Operator):
    bl_idname = "car_decimator.reset"
    bl_label = "重置"
    bl_description = "重置所有分析结果"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.car_decimator
        settings.is_analyzed = False
        settings.is_classified = False
        settings.is_features_detected = False
        settings.is_decimated = False
        settings.current_step = 'ANALYZE'
        settings.original_face_count = 0

        self.report({'INFO'}, "已重置")
        return {'FINISHED'}


CLASSES = [
    CAR_DECIMATOR_OT_analyze,
    CAR_DECIMATOR_OT_reset,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)