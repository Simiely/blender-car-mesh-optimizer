"""导出算子"""
import bpy
from ..utils import mesh_utils


class CAR_DECIMATOR_OT_export(bpy.types.Operator):
    bl_idname = "car_decimator.export_result"
    bl_label = "导出结果"
    bl_description = "导出减面后的模型为 OBJ/FBX"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default='*.obj;*.fbx', options={'HIDDEN'})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        obj = mesh_utils.get_active_mesh_obj(context)
        if obj is None:
            self.report({'ERROR'}, "请先选择一个 Mesh 对象")
            return {'CANCELLED'}

        if not self.filepath:
            self.report({'ERROR'}, "请选择保存路径")
            return {'CANCELLED'}

        # 临时选中对象
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        if self.filepath.endswith('.obj'):
            bpy.ops.export_scene.obj(
                filepath=self.filepath,
                use_selection=True,
                use_materials=True,
            )
        elif self.filepath.endswith('.fbx'):
            bpy.ops.export_scene.fbx(
                filepath=self.filepath,
                use_selection=True,
            )
        else:
            self.report({'ERROR'}, "不支持的格式，请使用 .obj 或 .fbx")
            return {'CANCELLED'}

        self.report({'INFO'}, f"已导出到: {self.filepath}")
        return {'FINISHED'}


CLASSES = [
    CAR_DECIMATOR_OT_export,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)