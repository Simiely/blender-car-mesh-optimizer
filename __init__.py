"""Blender Car Mesh Optimizer - 高面车模智能减面插件"""
bl_info = {
    "name": "Car Mesh Optimizer",
    "author": "Car Mesh Optimizer Team",
    "version": (0, 1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > CarMeshOpt",
    "description": "高面车模智能减面工具 —— 外饰/内饰分区 + 多约束加权 QEM 边塌缩",
    "category": "Mesh",
    "support": "COMMUNITY",
    "doc_url": "https://github.com/Simiely/blender-car-mesh-optimizer",
    "tracker_url": "https://github.com/Simiely/blender-car-mesh-optimizer/issues",
}

import bpy

from . import properties
from . import utils
from . import operators
from . import panels
from . import presets


def register():
    properties.register()
    operators.register()
    panels.register()
    presets.register()


def unregister():
    presets.unregister()
    panels.unregister()
    operators.unregister()
    properties.unregister()


if __name__ == "__main__":
    register()