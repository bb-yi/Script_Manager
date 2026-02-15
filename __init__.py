bl_info = {
    "name": "Script Manager",
    "author": "LEDingQ",
    "description": "",
    "blender": (3, 4, 0),
    "version": (0, 1, 4),
    "location": "",
    "warning": "",
    "category": "Generic",
}


import bpy
import hashlib
from .utils import *
from . import operators
from . import ui
from . import property
from .i18n import translations_dict


def register():
    try:
        bpy.app.translations.register(__name__, translations_dict)
    except:
        pass
    property.register()
    operators.register()
    ui.register()

    # 注册文件加载完成后的处理函数
    bpy.app.handlers.load_post.append(ScriptManager_load_post_handler)

    # 在注册完成后恢复handlers(针对插件重新启用的情况)
    def delayed_restore():
        restore_handlers()
        return None

    bpy.app.timers.register(delayed_restore, first_interval=1.0)


def unregister():
    try:
        bpy.app.translations.unregister(__name__)
    except:
        pass
    # 移除文件加载完成后的处理函数
    if ScriptManager_load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(ScriptManager_load_post_handler)
    property.unregister()
    operators.unregister()
    ui.unregister()
