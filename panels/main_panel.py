"""主面板 UI —— 向导式操作流程"""
import bpy
from ..presets.defaults import get_preset_items, apply_preset
from ..utils import mesh_utils


class CAR_DECIMATOR_PT_main(bpy.types.Panel):
    bl_label = "Car Mesh Optimizer"
    bl_idname = "CAR_DECIMATOR_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CarMeshOpt"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.car_decimator
        obj = mesh_utils.get_active_mesh_obj(context)

        # 当前对象信息
        if obj is None:
            layout.label(text="请选择一个 Mesh 对象", icon='ERROR')
            return

        if obj.type != 'MESH':
            layout.label(text="选中的对象不是 Mesh", icon='ERROR')
            return

        # 对象名称和面数
        box = layout.box()
        row = box.row()
        row.label(text=f"对象: {obj.name}", icon='OBJECT_DATA')

        if settings.original_face_count > 0:
            row = box.row()
            row.label(text=f"原始面数: {settings.original_face_count:,}")

            current = mesh_utils.get_face_count(obj)
            if current != settings.original_face_count:
                row = box.row()
                row.label(text=f"当前面数: {current:,}")

        # 预设选择
        box = layout.box()
        box.label(text="预设", icon='PRESET')
        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(settings, "target_face_count")

        row = col.row(align=True)
        row.operator("car_decimator.apply_preset", text="轿车").preset_key = "SEDAN"
        row.operator("car_decimator.apply_preset", text="SUV").preset_key = "SUV"
        row = col.row(align=True)
        row.operator("car_decimator.apply_preset", text="跑车").preset_key = "SPORTS"
        row.operator("car_decimator.apply_preset", text="激进").preset_key = "AGGRESSIVE"
        row = col.row(align=True)
        row.operator("car_decimator.apply_preset", text="默认").preset_key = "DEFAULT"

        layout.separator()

        # 步骤指示器
        box = layout.box()
        box.label(text="操作步骤", icon='SEQ_SEQUENTIAL')

        steps = ['ANALYZE', 'CLASSIFY', 'FEATURES', 'DECIMATE', 'RESULT']
        step_labels = ['分析', '分类', '特征', '减面', '结果']
        current_idx = steps.index(settings.current_step) if settings.current_step in steps else 0

        row = box.row(align=True)
        for i, (step, label) in enumerate(zip(steps, step_labels)):
            if i < current_idx:
                row.label(text=label, icon='CHECKMARK')
            elif i == current_idx:
                row.label(text=label, icon='PLAY')
            else:
                row.label(text=label, icon='BLANK1')

        layout.separator()

        # 根据当前步骤显示不同内容
        if settings.current_step == 'ANALYZE':
            self._draw_analyze(layout, settings)
        elif settings.current_step == 'CLASSIFY':
            self._draw_classify(layout, settings)
        elif settings.current_step == 'FEATURES':
            self._draw_features(layout, settings)
        elif settings.current_step == 'DECIMATE':
            self._draw_decimate(layout, settings)
        elif settings.current_step == 'RESULT':
            self._draw_result(layout, settings, obj)

        # 底部重置按钮
        layout.separator()
        layout.operator("car_decimator.reset", icon='LOOP_BACK')

    def _draw_analyze(self, layout, settings):
        """Step 1: 分析"""
        box = layout.box()
        box.label(text="Step 1: 分析模型", icon='INFO')
        col = box.column(align=True)
        col.operator("car_decimator.analyze", text="开始分析", icon='VIEWZOOM')

    def _draw_classify(self, layout, settings):
        """Step 2: 分类"""
        box = layout.box()
        box.label(text="Step 2: 自动分类", icon='GROUP_VERTEX')
        col = box.column(align=True)
        col.operator("car_decimator.classify", text="自动分类", icon='AUTO')

        if settings.is_classified:
            box = layout.box()
            box.label(text="分类结果", icon='OUTLINER_OB_GROUP_INSTANCE')
            col = box.column(align=True)
            col.label(text=f"外饰 (蓝) - 顶点组: {settings.exterior_vg}")
            col.label(text=f"内饰 (绿) - 顶点组: {settings.interior_vg}")
            col.label(text=f"底盘 (黄) - 顶点组: {settings.chassis_vg}")

            # 预算分配
            box = layout.box()
            box.label(text="面数预算分配", icon='PREFERENCES')
            col = box.column(align=True)
            col.prop(settings, "exterior_ratio", text="外饰占比")
            col.prop(settings, "interior_ratio", text="内饰占比")
            col.prop(settings, "chassis_ratio", text="底盘占比")

    def _draw_features(self, layout, settings):
        """Step 3: 特征检测"""
        box = layout.box()
        box.label(text="Step 3: 特征检测", icon='SHADING_RENDERED')

        col = box.column(align=True)
        col.prop(settings, "feature_edge_angle", text="特征边角度阈值")
        col.prop(settings, "silhouette_views", text="轮廓采样视角")

        col = box.column(align=True)
        col.operator("car_decimator.detect_features", text="检测特征", icon='RADIOBUT_ON')

        if settings.is_features_detected:
            box = layout.box()
            box.label(text="特征权重", icon='MODIFIER')
            col = box.column(align=True)
            col.prop(settings, "curvature_weight", text="曲率 λ₁", slider=True)
            col.prop(settings, "feature_edge_weight", text="特征边 λ₂", slider=True)
            col.prop(settings, "silhouette_weight", text="轮廓 λ₃", slider=True)
            col.prop(settings, "normal_dev_weight", text="法线偏差 λ₄", slider=True)
            col.prop(settings, "boundary_weight", text="边界 λ₅", slider=True)
            col.prop(settings, "user_weight_mult", text="用户权重 λ₆", slider=True)

            col = layout.column(align=True)
            col.operator("car_decimator.show_feature", text="显示特征热力图", icon="SHADING_TEXTURE")

    def _draw_decimate(self, layout, settings):
        """Step 4: 减面"""
        box = layout.box()
        box.label(text="Step 4: 执行减面", icon='MOD_DECIM')

        col = box.column(align=True)
        col.prop(settings, "target_face_count", text="目标总面数")

        # 粗减参数
        box = layout.box()
        box.label(text="Phase 1 粗减参数", icon='MESH_PLANE')
        col = box.column(align=True)
        col.prop(settings, "coarse_exterior_ratio", text="外饰粗减比", slider=True)
        col.prop(settings, "coarse_interior_ratio", text="内饰粗减比", slider=True)
        col.prop(settings, "coarse_chassis_ratio", text="底盘粗减比", slider=True)

        # 执行按钮
        col = layout.column(align=True)
        col.scale_y = 2.0
        col.operator("car_decimator.decimate", text="开始减面", icon='PLAY')

    def _draw_result(self, layout, settings, obj):
        """Step 5: 结果"""
        box = layout.box()
        box.label(text="Step 5: 减面完成", icon='CHECKMARK')

        current = mesh_utils.get_face_count(obj)
        col = box.column(align=True)
        col.label(text=f"原始面数: {settings.original_face_count:,}")
        col.label(text=f"当前面数: {current:,}")
        if settings.original_face_count > 0:
            reduction = (1 - current / settings.original_face_count) * 100
            col.label(text=f"减面: {reduction:.1f}%")

        col = layout.column(align=True)
        col.operator("car_decimator.export_result", text="导出模型", icon='EXPORT')

        col = layout.column(align=True)
        col.operator("car_decimator.show_feature", text="查看误差热力图", icon='SHADING_TEXTURE')


class CAR_DECIMATOR_OT_apply_preset(bpy.types.Operator):
    bl_idname = "car_decimator.apply_preset"
    bl_label = "应用预设"
    bl_description = "应用车型预设参数"
    bl_options = {'REGISTER', 'UNDO'}

    preset_key: bpy.props.StringProperty()

    def execute(self, context):
        apply_preset(context, self.preset_key)
        self.report({'INFO'}, f"已应用预设: {self.preset_key}")
        return {'FINISHED'}


CLASSES = [
    CAR_DECIMATOR_PT_main,
    CAR_DECIMATOR_OT_apply_preset,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)