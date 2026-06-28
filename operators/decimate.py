"""Step 4: 两阶段减面算子

Phase 1: 粗减 —— 使用 Blender 原生 Decimate Modifier，快速大幅减面
Phase 2: 精减 —— 使用加权 QEM 边塌缩，精确控制到目标面数
"""
import time
import bpy
import bmesh
import numpy as np
from ..utils import mesh_utils, qem


class CAR_DECIMATOR_OT_decimate(bpy.types.Operator):
    bl_idname = "car_decimator.decimate"
    bl_label = "开始减面"
    bl_description = "执行两阶段减面：粗减(Blender原生) + 精减(加权QEM)"
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None
    _start_time = None
    _phase = None
    _obj = None
    _original_obj = None

    def execute(self, context):
        obj = mesh_utils.get_active_mesh_obj(context)
        if obj is None:
            self.report({'ERROR'}, "请先选择一个 Mesh 对象")
            return {'CANCELLED'}

        settings = context.scene.car_decimator

        if not settings.is_classified or not settings.is_features_detected:
            self.report({'ERROR'}, "请先完成分类和特征检测")
            return {'CANCELLED'}

        # 保存原始对象引用
        self._obj = obj
        self._start_time = time.time()
        self._phase = 1

        # 计算各区域目标面数
        total_faces = mesh_utils.get_face_count(obj)
        target_total = settings.target_face_count

        # 获取各区域面数
        zone_faces = self._count_zone_faces(obj, settings)

        exterior_faces = zone_faces.get('EXTERIOR', 0)
        interior_faces = zone_faces.get('INTERIOR', 0)
        chassis_faces = zone_faces.get('CHASSIS', 0)

        # 目标面数
        exterior_target = int(target_total * settings.exterior_ratio / 100)
        interior_target = int(target_total * settings.interior_ratio / 100)
        chassis_target = int(target_total * settings.chassis_ratio / 100)

        self.report(
            {'INFO'},
            f"Phase 1 粗减开始... "
            f"外饰: {exterior_faces}→~{int(exterior_faces * (1 - settings.coarse_exterior_ratio))} "
            f"内饰: {interior_faces}→~{int(interior_faces * (1 - settings.coarse_interior_ratio))} "
            f"底盘: {chassis_faces}→~{int(chassis_faces * (1 - settings.coarse_chassis_ratio))}",
        )

        try:
            # Phase 1: 粗减
            self._phase_1_coarse(obj, settings)
        except Exception as e:
            self.report({'ERROR'}, f"Phase 1 粗减失败: {e}")
            return {'CANCELLED'}

        self.report(
            {'INFO'},
            f"Phase 1 完成，当前面数: {mesh_utils.get_face_count(obj)}",
        )

        # Phase 2: 精减
        self._phase = 2
        self.report(
            {'INFO'},
            f"Phase 2 精减开始... "
            f"目标: 外饰 {exterior_target} / 内饰 {interior_target} / 底盘 {chassis_target}",
        )

        try:
            self._phase_2_fine(obj, settings, exterior_target, interior_target, chassis_target)
        except Exception as e:
            self.report({'ERROR'}, f"Phase 2 精减失败: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

        elapsed = time.time() - self._start_time
        final_faces = mesh_utils.get_face_count(obj)

        settings.is_decimated = True
        settings.current_step = 'RESULT'

        self.report(
            {'INFO'},
            f"减面完成！{total_faces} → {final_faces} 面，"
            f"耗时 {elapsed:.1f} 秒",
        )

        return {'FINISHED'}

    def _count_zone_faces(self, obj, settings):
        """统计各区域的三角面数"""
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        vg_exterior = obj.vertex_groups.get(settings.exterior_vg)
        vg_interior = obj.vertex_groups.get(settings.interior_vg)
        vg_chassis = obj.vertex_groups.get(settings.chassis_vg)

        zone_faces = {'EXTERIOR': 0, 'INTERIOR': 0, 'CHASSIS': 0}

        for f in bm.faces:
            # 投票决定面属于哪个区域
            votes = {'EXTERIOR': 0, 'INTERIOR': 0, 'CHASSIS': 0}
            for v in f.verts:
                if vg_exterior:
                    try:
                        if vg_exterior.weight(v.index) > 0:
                            votes['EXTERIOR'] += 1
                    except RuntimeError:
                        pass
                if vg_interior:
                    try:
                        if vg_interior.weight(v.index) > 0:
                            votes['INTERIOR'] += 1
                    except RuntimeError:
                        pass
                if vg_chassis:
                    try:
                        if vg_chassis.weight(v.index) > 0:
                            votes['CHASSIS'] += 1
                    except RuntimeError:
                        pass

            best = max(votes, key=votes.get)
            if votes[best] > 0:
                tris = len(f.verts) - 2
                zone_faces[best] += tris

        bm.free()
        return zone_faces

    def _phase_1_coarse(self, obj, settings):
        """Phase 1: 粗减 —— 使用 Blender Decimate Modifier"""
        # 分别为每个区域应用 Decimate 减面
        # 策略：复制物体，对各区域分别操作，最后合并
        # 简化策略：对整个物体应用不同的 decimate ratio

        # 获取特征权重顶点组
        feature_vg = obj.vertex_groups.get(settings.feature_vg)

        # 为每个区域创建顶点组
        self._ensure_vg_weights(obj, settings)

        # 使用 Decimate Modifier 进行粗减
        # 对每个区域分别应用

        for zone_name, ratio, vg_name in [
            ('EXTERIOR', settings.coarse_exterior_ratio, settings.exterior_vg),
            ('INTERIOR', settings.coarse_interior_ratio, settings.interior_vg),
            ('CHASSIS', settings.coarse_chassis_ratio, settings.chassis_vg),
        ]:
            vg = obj.vertex_groups.get(vg_name)
            if vg is None:
                continue

            # 使用 Decimate Modifier (Collapse 模式)
            mod = obj.modifiers.new(name=f"CD_Coarse_{zone_name}", type='DECIMATE')
            mod.decimate_type = 'COLLAPSE'
            mod.ratio = 1.0 - ratio  # Blender 的 ratio 是保留比例
            mod.use_collapse_triangulate = True
            mod.vertex_group = vg.name
            mod.invert_vertex_group = False  # 只对指定顶点组减面

            # 应用 modifier
            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except RuntimeError as e:
                self.report({'WARNING'}, f"应用 {zone_name} 粗减失败: {e}")
                obj.modifiers.remove(mod)

    def _ensure_vg_weights(self, obj, settings):
        """确保各区域顶点组有正确的权重"""
        # 特征权重融合到保留权重组
        feature_vg = obj.vertex_groups.get(settings.feature_vg)
        if feature_vg is None:
            return

        preserve_vg = mesh_utils.get_vertex_group(obj, settings.weight_vg, create_if_missing=True)
        for v in obj.data.vertices:
            try:
                w = feature_vg.weight(v.index)
                preserve_vg.add([v.index], w, 'REPLACE')
            except RuntimeError:
                pass

    def _phase_2_fine(self, obj, settings, exterior_target, interior_target, chassis_target):
        """Phase 2: 精减 —— 使用加权 QEM"""
        # 获取特征权重
        feature_weights = mesh_utils.get_vertex_group_weights(obj, settings.feature_vg)
        n_verts = len(obj.data.vertices)

        vertex_weights = np.zeros(n_verts, dtype=np.float32)
        for vi, w in feature_weights.items():
            if vi < n_verts:
                vertex_weights[vi] = w

        # 获取用户权重（如果有）
        user_weights = mesh_utils.get_vertex_group_weights(obj, settings.weight_vg)
        for vi, w in user_weights.items():
            if vi < n_verts:
                vertex_weights[vi] += w * settings.user_weight_mult

        # 对每个区域分别执行 QEM
        # 简化：对整个物体执行 QEM，权重来自特征分析
        # 各区域的目标面数按比例分配

        current_faces = mesh_utils.get_face_count(obj)
        total_target = exterior_target + interior_target + chassis_target

        if current_faces <= total_target:
            return

        self.report(
            {'INFO'},
            f"QEM 精减: {current_faces} → {total_target} 面",
        )

        qem.run_weighted_qem(
            obj,
            total_target,
            vertex_weights=vertex_weights,
            face_mask=None,
            progress_callback=None,
        )


class CAR_DECIMATOR_OT_export_result(bpy.types.Operator):
    bl_idname = "car_decimator.export"
    bl_label = "导出减面模型"
    bl_description = "导出减面后的模型"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = mesh_utils.get_active_mesh_obj(context)
        if obj is None:
            self.report({'ERROR'}, "请先选择一个 Mesh 对象")
            return {'CANCELLED'}

        settings = context.scene.car_decimator

        if not settings.is_decimated:
            self.report({'ERROR'}, "请先执行减面")
            return {'CANCELLED'}

        self.report(
            {'INFO'},
            f"当前面数: {mesh_utils.get_face_count(obj)}，"
            "可使用 Blender 的 File > Export 导出"
        )
        return {'FINISHED'}


CLASSES = [
    CAR_DECIMATOR_OT_decimate,
    CAR_DECIMATOR_OT_export_result,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)