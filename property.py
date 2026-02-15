import bpy
from bpy.props import BoolProperty, CollectionProperty, FloatProperty, IntProperty, PointerProperty, StringProperty
from .utils import *


class ScriptManagerPreviewPropertyItem(bpy.types.PropertyGroup):
    path: bpy.props.StringProperty(name="Property Path", default="")


# item属性
class ScriptManagerItem(bpy.types.PropertyGroup):
    # --- 基础属性 ---
    selected: BoolProperty(name="Selected", default=False)
    Remarks: StringProperty(name="Remarks", default="")
    text_pointer: PointerProperty(type=bpy.types.Text, update=update_text_pointer)
    auto_reload: BoolProperty(name="Auto Reload", default=False)

    # --- 1. Frame Update (帧更新) ---
    run_in_frame_update: BoolProperty(name="Run In Frame Update", default=False, update=use_frame_update)
    frame_update_flag: BoolProperty(name="flag", default=False)
    frame_update_run_time: FloatProperty(name="Run Time", default=0.0)

    # --- 2. Depsgraph Update (依赖图更新) ---
    run_in_desgaph_update: BoolProperty(name="Run In Depsgraph Update", default=False, update=use_desgraph_update)
    desgaph_updata_flag: BoolProperty(name="flag", default=False)
    desgaph_update_run_time: FloatProperty(name="Run Time", default=0.0)

    # --- 3. Render Pre (渲染前) ---
    run_in_render_pre: BoolProperty(name="Run In Render Pre", default=False, update=use_render_pre_update)
    render_pre_flag: BoolProperty(name="flag", default=False)
    render_pre_run_time: FloatProperty(name="Run Time", default=0.0)

    # --- 4. Render Post (渲染后) ---
    run_in_render_post: BoolProperty(name="Run In Render Post", default=False, update=use_render_post_update)
    render_post_flag: BoolProperty(name="flag", default=False)
    render_post_run_time: FloatProperty(name="Run Time", default=0.0)

    # --- 5. Load Post (加载文件后) [新增] ---
    run_in_load_post: BoolProperty(name="Run On File Load", default=False)
    load_post_flag: BoolProperty(name="flag", default=False)
    load_post_run_time: FloatProperty(name="Run Time", default=0.0)

    # --- 6. Save Pre (保存文件前) [新增] ---
    run_in_save_pre: BoolProperty(name="Run Before Save", default=False, update=use_save_pre_update)
    save_pre_flag: BoolProperty(name="flag", default=False)
    save_pre_run_time: FloatProperty(name="Run Time", default=0.0)

    # --- 通用更新标记 ---
    updata_flag: BoolProperty(name="flag", default=False)


class ScriptManagerMsgBusItem(bpy.types.PropertyGroup):
    Remarks: StringProperty(name="Remarks", default="")
    RNA_path: StringProperty(name="RNA Path", default="", update=update_item_remark)
    text_pointer: PointerProperty(type=bpy.types.Text)
    is_registered: BoolProperty(name="Is Registered", default=False, update=update_registered_status)
    update_flag: BoolProperty(name="flag", default=False)
    msgbus_run_time: FloatProperty(name="Run Time", default=0.0)


# 插件属性组
class ScriptManagerPrefs(bpy.types.PropertyGroup):
    # 是否启用自动重载定时器
    use_auto_reload_timer: BoolProperty(name="Use Auto Reload Timer", default=False, update=use_auto_reload_update)
    # 自动重载定时器间隔
    auto_reload_timer_interval: FloatProperty(name="Auto Reload Timer Interval (s)", default=1.0, min=1)
    auto_reload_use_time: FloatProperty(name="Auto Reload Use Time", default=0.0)
    frame_handler_registered: BoolProperty(name="Frame Handler Registered", default=False)
    deps_handler_registered: BoolProperty(name="Deps Handler Registered", default=False)
    text_manager_collection: CollectionProperty(type=ScriptManagerItem)
    script_manager_index: IntProperty(name="Script Manager Index", default=0, update=update_script_manager_index)
    preview_properties: bpy.props.CollectionProperty(type=ScriptManagerPreviewPropertyItem)
    preview_properties_index: bpy.props.IntProperty(name="Index", default=0)
    preview_properties_num: bpy.props.IntProperty(name="Number", default=0)
    display_handler_list: BoolProperty(name="Display Handler List", default=False)
    handler_index: IntProperty(name="Handler Index", default=0, min=0)
    target_handler_name: StringProperty(name="Target Handler Name", default="")
    debug_mode: BoolProperty(name="Debug Mode", default=False)
    msgbus_collection: CollectionProperty(type=ScriptManagerMsgBusItem)
    msgbus_index: IntProperty(name="MsgBus Index", default=0)
    auto_reload_in_file_open: BoolProperty(name="Auto Reload In File Open", default=True)


classes = [
    ScriptManagerItem,
    ScriptManagerMsgBusItem,
    ScriptManagerPreviewPropertyItem,
    ScriptManagerPrefs,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.text_manager_prefs = PointerProperty(type=ScriptManagerPrefs)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    del bpy.types.Scene.text_manager_prefs
