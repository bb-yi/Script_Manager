import bpy
import subprocess
from .utils import *
from .i18n import *
from bpy.props import StringProperty, IntProperty
import sys


class SCRIPTMANAGER_OT_remove_all_handlers(bpy.types.Operator):
    bl_idname = "script_manager.remove_all_handlers"
    bl_label = "Remove All Handlers"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        for handler in list(bpy.app.handlers.frame_change_pre):
            bpy.app.handlers.frame_change_pre.remove(handler)
        for handler in list(bpy.app.handlers.depsgraph_update_post):
            bpy.app.handlers.depsgraph_update_post.remove(handler)
        prefs = context.scene.text_manager_prefs
        for item in prefs.text_manager_collection:
            item.run_in_desgaph_update = False
            item.run_in_frame_update = False
        return {"FINISHED"}


class SCRIPTMANAGER_OT_remove_addon_handlers(bpy.types.Operator):
    bl_idname = "script_manager.remove_addon_handlers"
    bl_label = "Remove All Handlers"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        for handler in list(bpy.app.handlers.frame_change_pre):
            if hasattr(handler, "_ScriptManagerItem_FC_ID"):
                bpy.app.handlers.frame_change_pre.remove(handler)
        for handler in list(bpy.app.handlers.depsgraph_update_post):
            if hasattr(handler, "_ScriptManagerItem_DC_ID"):
                bpy.app.handlers.depsgraph_update_post.remove(handler)
        prefs = context.scene.text_manager_prefs
        for item in prefs.text_manager_collection:
            item.run_in_desgaph_update = False
            item.run_in_frame_update = False
        return {"FINISHED"}


class SCRIPTMANAGER_OT_remove_handler(bpy.types.Operator):
    bl_idname = "script_manager.remove_handler"
    bl_label = "Remove Handler by Name"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        removed = False
        frame_change_pre_names = [handler.__name__ for handler in bpy.app.handlers.frame_change_pre]
        depsgraph_update_post_names = [handler.__name__ for handler in bpy.app.handlers.depsgraph_update_post]
        tmep = frame_change_pre_names + depsgraph_update_post_names
        target_handler_names = tmep[context.scene.text_manager_prefs.handler_index]
        # 移除 frame_change_pre 中的 handler
        for handler in list(bpy.app.handlers.frame_change_pre):
            if handler.__name__ == target_handler_names:
                bpy.app.handlers.frame_change_pre.remove(handler)
                removed = True

        # 移除 depsgraph_update_post 中的 handler
        for handler in list(bpy.app.handlers.depsgraph_update_post):
            if handler.__name__ == target_handler_names:
                bpy.app.handlers.depsgraph_update_post.remove(handler)
                removed = True

        if removed:
            self.report({"INFO"}, f"Handler removed: {target_handler_names}")
            return {"FINISHED"}
        else:
            self.report({"WARNING"}, f"Handler not found: {target_handler_names}")
            return {"CANCELLED"}


# 操作按钮
class SCRIPTMANAGER_OT_add_item(bpy.types.Operator):
    bl_idname = "script_manager.add_item"
    bl_label = "Add Item"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        prefs = context.scene.text_manager_prefs
        item = prefs.text_manager_collection.add()
        item.text_name = "New Text"
        prefs.script_manager_index = len(prefs.text_manager_collection) - 1
        return {"FINISHED"}


class SCRIPTMANAGER_OT_remove_item(bpy.types.Operator):
    bl_idname = "script_manager.remove_item"
    bl_label = "Remove Item"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        prefs = context.scene.text_manager_prefs
        # 先收集所有选中项的索引
        selected_indices = [i for i, item in enumerate(prefs.text_manager_collection) if getattr(item, "selected", False)]

        if selected_indices:
            # 倒序删除，避免索引错位
            for idx in reversed(selected_indices):
                prefs.text_manager_collection.remove(idx)
            # 更新 active_index
            prefs.script_manager_index = min(selected_indices[0], len(prefs.text_manager_collection) - 1)
        else:
            # 如果没有选中项，就删除当前 active_index
            idx = prefs.script_manager_index
            if 0 <= idx < len(prefs.text_manager_collection):
                prefs.text_manager_collection.remove(idx)
                prefs.script_manager_index = max(0, idx - 1)
        return {"FINISHED"}


class SCRIPTMANAGER_OT_move_item_up(bpy.types.Operator):
    bl_idname = "script_manager.move_item_up"
    bl_label = "Move Item Up"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        prefs = context.scene.text_manager_prefs
        idx = prefs.script_manager_index
        if idx > 0:
            prefs.text_manager_collection.move(idx, idx - 1)
            prefs.script_manager_index = idx - 1
        return {"FINISHED"}


class SCRIPTMANAGER_OT_new_text(bpy.types.Operator):
    bl_idname = "script_manager.new_text"
    bl_label = "New Text"
    bl_description = "Create a new Blender text and add to the manager"
    bl_options = {"REGISTER", "UNDO"}
    text_name: StringProperty(name="Text Name", default="New Script")

    def execute(self, context):
        prefs = context.scene.text_manager_prefs

        # 创建 Blender 文本数据块
        new_text = bpy.data.texts.new(self.text_name)

        # 添加到 text_manager_collection
        item = prefs.text_manager_collection.add()
        item.text_name = new_text.name
        item.text_pointer = new_text
        prefs.script_manager_index = len(prefs.text_manager_collection) - 1

        return {"FINISHED"}

    def invoke(self, context, event):
        # 弹出输入框让用户修改名称
        return context.window_manager.invoke_props_dialog(self)


class SCRIPTMANAGER_OT_move_item_down(bpy.types.Operator):
    bl_idname = "script_manager.move_item_down"
    bl_label = "Move Item Down"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        prefs = context.scene.text_manager_prefs
        idx = prefs.script_manager_index
        if idx < len(prefs.text_manager_collection) - 1:
            prefs.text_manager_collection.move(idx, idx + 1)
            prefs.script_manager_index = idx + 1
        return {"FINISHED"}


class SCRIPTMANAGER_OT_open_in_vscode(bpy.types.Operator):
    bl_idname = "text_manager.open_in_vscode"
    bl_label = "Open in VSCode"
    bl_description = "Open the selected Blender text in VSCode"

    text_name: bpy.props.StringProperty(name="Text Name")

    def execute(self, context):
        addon_prefs = context.preferences.addons[__package__].preferences
        vscode_path = addon_prefs.vscode_path.strip('"').strip()
        # vscode_path = "D:/rj/vscode/Microsoft VS Code/Code.exe"#调试用
        text = bpy.data.texts.get(self.text_name)

        if text is None:
            self.report({"ERROR"}, translations("No text selected"))
            return {"CANCELLED"}

        if not text.filepath:
            self.report({"ERROR"}, translations("Text not saved"))
            success = save_text_with_browser(text, context)
            self.report({"INFO"}, f"{success}")
            return {"FINISHED"}

        filepath = bpy.path.abspath(text.filepath)

        if not os.path.exists(filepath):
            self.report({"ERROR"}, f"File not found: {filepath}")
            return {"CANCELLED"}

        # 处理 VSCode 路径
        vscode_path = bpy.path.abspath(vscode_path)
        if os.path.isdir(vscode_path):
            # 如果是目录，自动补全 Code.exe
            candidate = os.path.join(vscode_path, "Code.exe")
            if os.path.exists(candidate):
                vscode_path = candidate
            else:
                self.report({"ERROR"}, f"VSCode path is a directory, Code.exe not found: {candidate}")
                return {"CANCELLED"}

        elif os.path.isfile(vscode_path):
            # 如果是文件，直接用
            if not vscode_path.lower().endswith("code.exe"):
                self.report({"WARNING"}, f"The specified file is not Code.exe: {vscode_path}")
        else:
            # 如果路径不存在，尝试补全 Code.exe
            candidate = vscode_path + "\\Code.exe"
            if os.path.exists(candidate):
                vscode_path = candidate
            else:
                self.report({"ERROR"}, f"Invalid VSCode path: {vscode_path}")
                return {"CANCELLED"}

        try:
            # 调用 VSCode 打开文件
            subprocess.Popen([vscode_path, filepath])
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Failed to launch VSCode: {str(e)}")
            return {"CANCELLED"}


class SCRIPT_MANAGER_OT_add_preview_property(bpy.types.Operator):
    bl_idname = "script_manager.add_preview_property"
    bl_label = "Add Preview Property"

    def execute(self, context):
        prefs = context.scene.text_manager_prefs
        prefs.preview_properties.add()
        return {"FINISHED"}


class SCRIPT_MANAGER_OT_remove_preview_property(bpy.types.Operator):
    bl_idname = "script_manager.remove_preview_property"
    bl_label = "Remove Preview Property"

    def execute(self, context):
        prefs = context.scene.text_manager_prefs
        if prefs.preview_properties:
            prefs.preview_properties.remove(len(prefs.preview_properties) - 1)
        return {"FINISHED"}


class SCRIPTMANAGER_OT_run_text(bpy.types.Operator):
    bl_idname = "script_manager.run_text"
    bl_label = "Run Text"
    bl_description = "Run the selected Blender text"

    text_name: StringProperty(name="Text Name")

    def execute(self, context):
        text = bpy.data.texts.get(self.text_name)
        ok, msg = run_text_block(text)
        self.report({"INFO"} if ok else {"ERROR"}, msg)
        return {"FINISHED"} if ok else {"CANCELLED"}


class ScriptManagerMsgBus_OT_add_item(bpy.types.Operator):
    bl_idname = "script_manager.msgbus_add_item"
    bl_label = "Add MsgBus Item"

    def execute(self, context):
        prefs = context.scene.text_manager_prefs
        item = prefs.msgbus_collection.add()
        item.RNA_path = "RNA Path"
        prefs.msgbus_index = len(prefs.msgbus_collection) - 1
        return {"FINISHED"}


class ScriptManagerMsgBus_OT_remove_item(bpy.types.Operator):
    bl_idname = "script_manager.msgbus_remove_item"
    bl_label = "Remove MsgBus Item"

    def execute(self, context):
        prefs = context.scene.text_manager_prefs
        # 如果没有选中项，就删除当前 active_index
        idx = prefs.msgbus_index
        if 0 <= idx < len(prefs.msgbus_collection):
            if prefs.msgbus_collection[idx].is_registered:
                self.report({"ERROR"}, translations("This item is not unregistered. Please unregister it before deleting."))
                return {"CANCELLED"}
            prefs.msgbus_collection.remove(idx)
            prefs.msgbus_index = max(0, idx - 1)
        return {"FINISHED"}


class ScriptManagerMsgBus_OT_move_item_up(bpy.types.Operator):
    bl_idname = "script_manager.msgbus_move_item_up"
    bl_label = "Move MsgBus Item Up"

    def execute(self, context):
        prefs = context.scene.text_manager_prefs
        index = prefs.msgbus_index
        if index > 0:
            prefs.msgbus_index = index - 1
            prefs.msgbus_collection.move(index, index - 1)
        return {"FINISHED"}


class ScriptManagerMsgBus_OT_move_item_down(bpy.types.Operator):
    bl_idname = "script_manager.msgbus_move_item_down"
    bl_label = "Move MsgBus Item Down"

    def execute(self, context):
        prefs = context.scene.text_manager_prefs
        index = prefs.msgbus_index
        if index < len(prefs.msgbus_collection) - 1:
            prefs.msgbus_index = index + 1
            prefs.msgbus_collection.move(index, index + 1)
        return {"FINISHED"}


class ScriptManagerMsgBus_OT_register_msgbus(bpy.types.Operator):
    bl_idname = "script_manager.msgbus_register_msgbus"
    bl_label = "Register MsgBus Handlers"
    bl_options = {"REGISTER", "UNDO"}  # 确保 REGISTER 以记录报告到状态栏

    index: IntProperty(name="Index", default=0)

    def execute(self, context):
        pref = context.scene.text_manager_prefs
        RNA_path = pref.msgbus_collection[self.index].RNA_path
        text_name = pref.msgbus_collection[self.index].text_pointer.name if pref.msgbus_collection[self.index].text_pointer else ""
        if RNA_path == "" or text_name == "":
            self.report({"ERROR"}, f"Path or script cannot be empty: {RNA_path} - {text_name}")
            return {"CANCELLED"}
        valid_path, key = get_msgbus_key(RNA_path)
        if RNA_path and valid_path and text_name != "":
            self.report({"INFO"}, f"Register Trigger monitoring: {RNA_path} - {text_name}-key: {key}")

            bpy.msgbus.subscribe_rna(
                key=key,
                owner=sys.intern(str(RNA_path).strip()),  # 保证注册时和注销时是完全一致的对象
                args=(),
                notify=make_ScriptManagerMsgBus_update_callback(self.index),
            )
            return {"FINISHED"}
        else:
            self.report({"ERROR"}, f"Invalid path or the specified script is empty: {RNA_path}")
            return {"CANCELLED"}


class ScriptManagerMsgBus_OT_unregister_msgbus(bpy.types.Operator):
    bl_idname = "script_manager.msgbus_unregister_msgbus"
    bl_label = "Unregister MsgBus Handlers"

    RNA_path: StringProperty(name="RNA Path")

    def execute(self, context):
        if self.RNA_path != "":
            # print(f"注销MsgBus监控: {self.RNA_path}")
            bpy.msgbus.clear_by_owner(sys.intern(str(self.RNA_path).strip()))
            self.report({"INFO"}, f"Unregister Trigger monitoring: {self.RNA_path}")
        else:
            pass
            self.report({"ERROR"}, f"Invalid path: {self.RNA_path}")
        return {"FINISHED"}


classes = [
    SCRIPTMANAGER_OT_remove_all_handlers,
    SCRIPTMANAGER_OT_remove_addon_handlers,
    SCRIPTMANAGER_OT_remove_item,
    SCRIPTMANAGER_OT_remove_handler,
    SCRIPTMANAGER_OT_add_item,
    SCRIPTMANAGER_OT_move_item_up,
    SCRIPTMANAGER_OT_move_item_down,
    SCRIPTMANAGER_OT_new_text,
    SCRIPTMANAGER_OT_run_text,
    SCRIPTMANAGER_OT_open_in_vscode,
    SCRIPT_MANAGER_OT_add_preview_property,
    SCRIPT_MANAGER_OT_remove_preview_property,
    ScriptManagerMsgBus_OT_add_item,
    ScriptManagerMsgBus_OT_remove_item,
    ScriptManagerMsgBus_OT_move_item_up,
    ScriptManagerMsgBus_OT_move_item_down,
    ScriptManagerMsgBus_OT_register_msgbus,
    ScriptManagerMsgBus_OT_unregister_msgbus,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
