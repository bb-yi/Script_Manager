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
from bpy.props import StringProperty, BoolProperty, PointerProperty, FloatProperty, CollectionProperty, IntProperty
import os
import time
import subprocess
import hashlib
import sys
from .i18n import _, load_language, _f


def DebugPrint(*args):
    if bpy.context.scene.text_manager_prefs.debug_mode:
        print(*args)


class ScriptManagerAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__  # 插件的 module 名
    vscode_path: bpy.props.StringProperty(name=_("VSCode Path"), subtype="FILE_PATH")

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "vscode_path")


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
            self.report({"INFO"}, _f("Handler removed: {str}", str=target_handler_names))
            return {"FINISHED"}
        else:
            self.report({"WARNING"}, _f("Handler not found: {str}", str=target_handler_names))
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


def save_text_with_browser(text, context):
    """
    保存指定 Text，弹出文件浏览器(跨上下文)。
    """

    if not text.filepath:
        text.filepath = os.path.join("C:/temp/", text.name)  # 默认路径

    text_area = None
    created_new_area = False
    for area in context.screen.areas:
        if area.type == "TEXT_EDITOR":
            text_area = area
            break

    # 如果没有 Text Editor 区域，则创建一个
    if not text_area:
        # 分割当前区域左侧
        bpy.ops.screen.area_split(direction="VERTICAL", factor=0.01)
        text_area = context.screen.areas[-1]
        text_area.type = "TEXT_EDITOR"
        created_new_area = True
        space = text_area.spaces.active
        if space.type != "TEXT_EDITOR":
            space.type = "TEXT_EDITOR"
        space.text = text

    override = {
        "window": context.window,
        "screen": context.screen,
        "area": text_area,
        "region": text_area.regions[-1],
        "edit_text": text,
    }
    try:
        with context.temp_override(**override):
            pass
            bpy.ops.text.save_as("INVOKE_DEFAULT")
        return True
    except RuntimeError as e:
        print(f"Save text failed: {e}")
        return False
    finally:
        if created_new_area:
            bpy.ops.screen.area_join()
            print("Temporary Text Editor has been cleaned up")


class SCRIPTMANAGER_OT_open_in_vscode(bpy.types.Operator):
    bl_idname = "text_manager.open_in_vscode"
    bl_label = "Open in VSCode"
    bl_description = "Open the selected Blender text in VSCode"

    text_name: bpy.props.StringProperty(name="Text Name")

    def execute(self, context):
        addon_prefs = context.preferences.addons[__name__].preferences
        vscode_path = addon_prefs.vscode_path.strip('"').strip()
        # vscode_path = "D:/rj/vscode/Microsoft VS Code/Code.exe"#调试用
        text = bpy.data.texts.get(self.text_name)

        if text is None:
            self.report({"ERROR"}, _("No text selected"))
            return {"CANCELLED"}

        if not text.filepath:
            self.report({"ERROR"}, _("Text not saved"))
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


def run_text_block(text: bpy.types.Text):
    if text is None:
        return False, "No text block provided"
    try:
        code = text.as_string()
        # 使用 Blender 全局环境
        exec(code, globals())

        return True, f"Text '{text.name}' executed"
    except Exception as e:
        print(f"Error running '{text.name}': {e}")
        return False, f"Error running '{text.name}': {e}"


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


auto_reload_flag = False


class PT_SCRIPTMANAGERPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_script_manager"
    bl_label = "Script Manager"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Script Manager"

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        col = layout.column()
        col.operator("script_manager.new_text", text=_("New Text"))
        row = col.row()
        row.template_list("SCRIPTMANAGER_UL_texts", "", scene.text_manager_prefs, "text_manager_collection", scene.text_manager_prefs, "script_manager_index", rows=6)
        col1 = row.column(align=True)
        col1.operator("script_manager.add_item", icon="ADD", text="")
        col1.operator("script_manager.remove_item", icon="REMOVE", text="")
        col1.separator()
        col1.operator("script_manager.move_item_up", icon="TRIA_UP", text="")
        col1.operator("script_manager.move_item_down", icon="TRIA_DOWN", text="")
        row = col.row()
        split = row.split(factor=0.8)
        split.prop(scene.text_manager_prefs, "use_auto_reload_timer", text=_("Use Auto Reload Timer"), icon="TIME")
        split.label(text=f"{scene.text_manager_prefs.auto_reload_use_time:.2f}ms", icon="RECORD_OFF" if not auto_reload_flag else "RECORD_ON")
        col.prop(scene.text_manager_prefs, "auto_reload_timer_interval", text=_("Auto-reload timer interval"))


class PT_SCRIPTMANAGERSubPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_script_manager_subpanel"
    bl_label = "Script Options"
    bl_parent_id = "OBJECT_PT_script_manager"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Script Manager"

    def draw(self, context):
        layout = self.layout
        prefs = context.scene.text_manager_prefs
        box = layout.box()
        if len(prefs.text_manager_collection) != 0:
            item = prefs.text_manager_collection[prefs.script_manager_index]
            if item.text_pointer:
                row = box.row()
                row.scale_y = 2.0
                row.operator("script_manager.run_text", text="Run", icon="PLAY").text_name = item.text_pointer.name
                row = box.row()
                row.operator("text_manager.open_in_vscode", text="Open in VSCode", icon="TEXT").text_name = item.text_pointer.name
                row = box.row()
                row.enabled = False
                row.label(icon="RECORD_OFF" if not item.updata_flag else "RECORD_ON")
                row.enabled = True
                row.prop(item, "text_pointer", text="")
                box.prop(item.text_pointer, "filepath", text="Filepath")
                box.prop(item, "auto_reload", text="Auto Reload", icon="FILE_REFRESH")
                row1 = box.row()
                split = row1.split(factor=0.8)
                split.prop(item, "run_in_frame_update", text="Run In Frame Update", icon="PLAY")
                split.label(text=f"{item.frame_update_run_time:.2f}ms", icon="RECORD_OFF" if not item.frame_update_flag else "RECORD_ON")
                row1 = box.row()
                split = row1.split(factor=0.8)
                split.prop(item, "run_in_desgaph_update", text="Run In Depsgraph Update", icon="FILE_REFRESH")
                split.label(text=f"{item.desgaph_update_run_time:.2f}ms", icon="RECORD_OFF" if not item.desgaph_updata_flag else "RECORD_ON")
            else:
                box.label(text=_("No text data block specified"))
        else:
            box.label(text=_("No available text data block"))


class PT_SCRIPTMANAGERTools(bpy.types.Panel):
    bl_idname = "OBJECT_PT_script_manager_tools"
    bl_label = "Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Script Manager"

    def draw(self, context):
        layout = self.layout
        prefs = context.scene.text_manager_prefs

        # 工具面板
        col = layout.column()
        box = col.box()
        box.label(text="属性预览")

        # 操作按钮
        row = box.row()
        row.operator("script_manager.add_preview_property", text="Add", icon="ADD")
        row.operator("script_manager.remove_preview_property", text="Remove", icon="REMOVE")

        # 属性列表
        box1 = box.box()
        for item in prefs.preview_properties:
            row = box1.row()
            row.prop(item, "path", text="")

            if item.path:
                try:
                    value = eval(item.path)
                    # 显示类型和值
                    row1 = row.row()
                    row1.alignment = "RIGHT"
                    row1.label(text=f"{type(value).__name__}")
                    display_val = self.format_value(value)
                    row1.label(text=f"{display_val}")
                    obj, attr_name = eval(f"({item.path.rsplit('.',1)[0]}, '{item.path.rsplit('.',1)[1]}')")
                    if hasattr(obj, "bl_rna") and attr_name in obj.bl_rna.properties:
                        # row.prop(obj, attr_name, text="", index=0)
                        # 如果是向量属性(长度 2 或 3)
                        attr_value = getattr(obj, attr_name)
                        # 判断是否是颜色属性
                        is_color = False
                        if hasattr(obj.bl_rna.properties[attr_name], "subtype"):
                            is_color = obj.bl_rna.properties[attr_name].subtype == "COLOR"
                        if hasattr(attr_value, "__len__") and len(attr_value) in (2, 3) and not is_color:
                            row_vec = row.row(align=True)  # align=True 可以取消间隔
                            row_vec.prop(obj, attr_name, index=0, text="")
                            row_vec.prop(obj, attr_name, index=1, text="")
                            if len(attr_value) == 3:
                                row_vec.prop(obj, attr_name, index=2, text="")
                        else:
                            # 普通 RNA 属性
                            row.prop(obj, attr_name, text="")
                except Exception as e:
                    DebugPrint(f"Error previewing property: {e}")
                    row.label(text=f"Error: {e}", icon="ERROR")
            else:
                row.label(text=_("No property path"))

    def format_value(self, value):
        # 布尔值
        if isinstance(value, bool):
            return str(value)
        # Blender 数据块
        if hasattr(value, "name") and hasattr(value, "type"):
            return f"{value.name} ({value.type})"
        elif hasattr(value, "name"):
            return value.name

        # 特殊集合类型(如 bpy.data.collections)
        if "bpy_prop_collection" in str(type(value)) or "bpy.data" in str(type(value)):
            try:
                items = [item.name for item in list(value)[:3]]
                return f"({len(value)}) [{', '.join(items)}]" if items else f"({len(value)}) []"
            except:
                return f"[Collection] {len(value)}items"

        # 可迭代对象(如 list, tuple)
        if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
            try:
                items = [self.format_number(x) for x in list(value)[:5]]
                return f"[{', '.join(items)}]" if items else "[]"
            except:
                return _("[Not iterable]")

        # 数值类型(int, float)保留五位小数
        if isinstance(value, (int, float)):
            return self.format_number(value)

        # 基础类型(如字符串、布尔值等)
        return str(value)[:50] + ("..." if len(str(value)) > 50 else "")

    def format_number(self, x):
        if isinstance(x, (int, float)):
            return f"{x:.5f}"
        return str(x)[:20]


class PT_SCRIPTMANAGERDebug(bpy.types.Panel):
    bl_idname = "OBJECT_PT_script_manager_debug"
    bl_label = "Debug"
    bl_parent_id = "OBJECT_PT_script_manager_tools"  # 指定父面板
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Script Manager"

    def draw(self, context):
        layout = self.layout
        prefs = context.scene.text_manager_prefs
        col = layout.column()
        col.prop(prefs, "debug_mode", text=_("Print debug info"), icon="SETTINGS")
        col.prop(prefs, "auto_reload_in_file_open", text=_("Restore handlers and triggers when opening file"), icon="FILE_REFRESH")
        col.operator("script_manager.remove_addon_handlers", text=_("Remove plugin handler"))
        col.label(text=_("Plugin handler"))
        box = col.box()
        i = 0
        for handler in bpy.app.handlers.frame_change_pre:
            if hasattr(handler, "_ScriptManagerItem_FC_ID"):
                box.label(text=f"{i}.Frame: {handler._ScriptManagerItem_FC_ID}")
                i += 1
        for handler in bpy.app.handlers.depsgraph_update_post:
            if hasattr(handler, "_ScriptManagerItem_DC_ID"):
                box.label(text=f"{i}.Deps: {handler._ScriptManagerItem_DC_ID}")
                i += 1
        col.operator("script_manager.remove_all_handlers", text=_("Remove all handlers"))
        col.operator("script_manager.remove_handler", text=_("Remove specified handler"))
        col.prop(prefs, "handler_index", text=_("Target Handler"))
        i = 0
        frame_change_pre_names = [handler.__name__ for handler in bpy.app.handlers.frame_change_pre]
        depsgraph_update_post_names = [handler.__name__ for handler in bpy.app.handlers.depsgraph_update_post]
        row = col.row()
        row.label(text=_("All handlers"))
        row.prop(prefs, "display_handler_list", text="", icon="TRIA_DOWN" if prefs.display_handler_list else "TRIA_RIGHT")
        box = col.box()
        if prefs.display_handler_list:
            for name in frame_change_pre_names:
                row = box.row()
                if i == prefs.handler_index:
                    row.alert = True  # 高亮这一行
                row.label(text=f"{i}. Frame: {name}")
                i += 1

            for name in depsgraph_update_post_names:
                row = box.row()
                if i == prefs.handler_index:
                    row.alert = True  # 高亮这一行
                row.label(text=f"{i}. Deps: {name}")
                i += 1


def use_frame_update(self, context):
    # 添加和移除帧更新回调
    prefs = context.scene.text_manager_prefs
    item = prefs.text_manager_collection[prefs.script_manager_index]
    if item.run_in_frame_update:
        has_handler = False
        for handler in bpy.app.handlers.frame_change_pre:
            if hasattr(handler, "_ScriptManagerItem_FC_ID") and handler._ScriptManagerItem_FC_ID == item.text_pointer.name:
                if item.text_pointer.name in handler._ScriptManagerItem_FC_ID:
                    bpy.app.handlers.frame_change_pre.remove(handler)
                    has_handler = True
        bpy.app.handlers.frame_change_pre.append(make_ScriptManager_frame_update_handler(item.text_pointer.name))
        if not has_handler:
            print(_("Add frame update"))
        else:
            print(_("Frame update updated"))
    else:
        for handler in bpy.app.handlers.frame_change_pre:
            if hasattr(handler, "_ScriptManagerItem_FC_ID"):
                if item.text_pointer.name in handler._ScriptManagerItem_FC_ID:
                    bpy.app.handlers.frame_change_pre.remove(handler)
        print(_("Remove frame update"))


def use_desgraph_update(self, context):
    prefs = context.scene.text_manager_prefs
    item = prefs.text_manager_collection[prefs.script_manager_index]
    if item.run_in_desgaph_update:
        has_handler = False
        for handler in bpy.app.handlers.depsgraph_update_post:
            if hasattr(handler, "_ScriptManagerItem_DC_ID"):
                if item.text_pointer.name in handler._ScriptManagerItem_DC_ID:
                    bpy.app.handlers.depsgraph_update_post.remove(handler)
                    has_handler = True
        bpy.app.handlers.depsgraph_update_post.append(make_ScriptManager_depsgraph_update_handler(item.text_pointer.name))
        if not has_handler:
            print(_("Add depsgraph update"))
        else:
            print(_("Depsgraph update updated"))
    else:
        for handler in bpy.app.handlers.depsgraph_update_post:
            if hasattr(handler, "_ScriptManagerItem_DC_ID"):
                if item.text_pointer.name in handler._ScriptManagerItem_DC_ID:
                    bpy.app.handlers.depsgraph_update_post.remove(handler)
        print(_("Remove depsgraph update"))


# NOTE 防止使用相同的TEXT
def update_text_pointer(self, context):
    prefs = context.scene.text_manager_prefs
    current_name = self.text_pointer.name if self.text_pointer else None
    # 遍历其他 item
    for item in prefs.text_manager_collection:
        if item == self:
            continue
        if item.text_pointer and current_name and item.text_pointer.name == current_name:
            DebugPrint(_("Current text is used by another item"))
            # 重置为 None，或者弹出提示
            item.text_pointer = None
            break


class ScriptManagerPreviewPropertyItem(bpy.types.PropertyGroup):
    path: bpy.props.StringProperty(name="Property Path", default="")


# item属性
class ScriptManagerItem(bpy.types.PropertyGroup):
    selected: BoolProperty(name="Selected", default=False)
    Remarks: StringProperty(name="Remarks", default="")
    text_pointer: PointerProperty(type=bpy.types.Text, update=update_text_pointer)
    auto_reload: BoolProperty(name="Auto Reload", default=False)
    run_in_frame_update: BoolProperty(name="Run In Frame Update", default=False, update=use_frame_update)
    frame_update_flag: BoolProperty(name="flag", default=False)
    frame_update_run_time: FloatProperty(name="Run Time", default=0.0)
    run_in_desgaph_update: BoolProperty(name="Run In Depsgraph Update", default=False, update=use_desgraph_update)
    desgaph_updata_flag: BoolProperty(name="flag", default=False)
    desgaph_update_run_time: FloatProperty(name="Run Time", default=0.0)
    updata_flag: BoolProperty(name="flag", default=False)


# item面板
class SCRIPTMANAGER_UL_texts(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.alignment = "LEFT"
        row.label(icon="RECORD_OFF" if not item.updata_flag else "RECORD_ON")
        row.label(text="-" if item.text_pointer is None or not item.text_pointer.is_dirty else "*")
        row.label(text=f"{index}.")
        row.prop(item, "selected", text="", emboss=False, icon="CHECKBOX_DEHLT" if not item.selected else "CHECKBOX_HLT")
        row.alignment = "EXPAND"
        row.prop(item, "Remarks", text="", emboss=True, icon="BOOKMARKS")
        row.prop(item, "text_pointer", text="")
        row.alignment = "RIGHT"
        row.operator("script_manager.run_text", icon="PLAY", text="").text_name = item.text_pointer.name if item.text_pointer else ""


def auto_reload_timer_callback():
    """自动重载文本数据块"""
    global auto_reload_flag
    start_time = time.perf_counter()  # 记录开始时间
    prefs = bpy.context.scene.text_manager_prefs
    # print("自动重载定时器回调")

    for item in prefs.text_manager_collection:
        text = item.text_pointer
        if text is None:
            continue
        # print(text.name, text.is_modified, text.is_dirty)
        if text.is_modified and text.filepath and os.path.exists(bpy.path.abspath(text.filepath)) and item.auto_reload:
            reload_text_block(text)

    # 如果定时器仍然启用，返回下一次调用间隔；否则返回 None 停止定时器
    if prefs.use_auto_reload_timer:
        elapsed = (time.perf_counter() - start_time) * 1000  # 运行耗时(毫秒)
        bpy.context.scene.text_manager_prefs.auto_reload_use_time = elapsed
        auto_reload_flag = not auto_reload_flag
        # print(f"自动重载定时器回调，耗时 {elapsed:.3f} 毫秒")
        return prefs.auto_reload_timer_interval
    else:
        return None


def reload_text_block(text: bpy.types.Text):
    """用文件内容替换 Text block,同时重置 is_modified"""
    if not text.filepath:
        # print(f"{text.name} 没有关联文件，跳过")
        return

    filepath = bpy.path.abspath(text.filepath)
    if not os.path.exists(filepath):
        # print(f"文件不存在: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        file_content = f.read()
    # 清空并写入新内容
    text.clear()
    text.write(file_content)


# 布尔属性更新回调
def use_auto_reload_update(self, context):
    prefs = context.scene.text_manager_prefs
    if prefs.use_auto_reload_timer:
        # 添加定时器
        if not bpy.app.timers.is_registered(auto_reload_timer_callback):
            bpy.app.timers.register(auto_reload_timer_callback, first_interval=prefs.auto_reload_timer_interval)
            print(_("Auto-reload timer started"))
        else:
            bpy.app.timers.unregister(auto_reload_timer_callback)
            bpy.app.timers.register(auto_reload_timer_callback, first_interval=prefs.auto_reload_timer_interval)
            print(_("Auto-reload timer restarted"))
    else:
        # 移除定时器
        if bpy.app.timers.is_registered(auto_reload_timer_callback):
            bpy.app.timers.unregister(auto_reload_timer_callback)
            print(_("Auto-reload timer stopped"))
        else:
            print(_("Auto-reload timer not started"))


# NOTE 帧更新回调
def make_ScriptManager_frame_update_handler(item_name):
    def ScriptManager_frame_update_handler(scene):
        start_time = time.perf_counter()  # 记录开始时间
        prefs = scene.text_manager_prefs
        item = None
        for temp in prefs.text_manager_collection:
            if temp.run_in_frame_update and temp.text_pointer and temp.text_pointer.name == ScriptManager_frame_update_handler._ScriptManagerItem_FC_ID:
                item = temp
        if item:
            DebugPrint("Frame update:", ScriptManager_frame_update_handler._ScriptManagerItem_FC_ID)
            run_text_block(item.text_pointer)
            item.frame_update_flag = not item.frame_update_flag
            item.updata_flag = not item.updata_flag
            elapsed = (time.perf_counter() - start_time) * 1000  # 运行耗时(毫秒)
            item.frame_update_run_time = elapsed

    ScriptManager_frame_update_handler._ScriptManagerItem_FC_ID = item_name
    return ScriptManager_frame_update_handler


# NOTE depsgraph 更新回调
def make_ScriptManager_depsgraph_update_handler(item_name):
    def ScriptManager_depsgraph_update_handler(scene):
        start_time = time.perf_counter()  # 记录开始时间
        prefs = scene.text_manager_prefs
        item = None
        for temp in prefs.text_manager_collection:
            if temp.run_in_desgaph_update and temp.text_pointer and temp.text_pointer.name == ScriptManager_depsgraph_update_handler._ScriptManagerItem_DC_ID:
                item = temp
        if item:
            DebugPrint("Depsgraph update:", ScriptManager_depsgraph_update_handler._ScriptManagerItem_DC_ID)
            run_text_block(item.text_pointer)
            item.desgaph_updata_flag = not item.desgaph_updata_flag
            item.updata_flag = not item.updata_flag
            elapsed = (time.perf_counter() - start_time) * 1000  # 运行耗时(毫秒)
            item.desgaph_update_run_time = elapsed

    ScriptManager_depsgraph_update_handler._ScriptManagerItem_DC_ID = item_name
    return ScriptManager_depsgraph_update_handler


# NOTE 切换文本编辑器为激活文本
def update_script_manager_index(self, context):
    prefs = context.scene.text_manager_prefs
    index = prefs.script_manager_index
    # 确保 index 在范围内
    if index < 0 or index >= len(prefs.text_manager_collection):
        return

    item = prefs.text_manager_collection[index]
    text = item.text_pointer
    if text is None:
        return

    # 遍历所有窗口和区域，寻找 Text Editor
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "TEXT_EDITOR":
                for space in area.spaces:
                    if space.type == "TEXT_EDITOR":
                        # 切换当前文本
                        space.text = text
                        break
                break  # 只切一个文本编辑器


def get_rna_display_name(path_str: str):
    try:
        # 分割出属性名(最后一部分)
        # 例如 bpy.data.scenes['Scene'].cycles.samples → samples
        attr_name = path_str.split(".")[-1]

        # 获取对象(不包含最后一段属性名)
        obj_path = ".".join(path_str.split(".")[:-1])
        obj = eval(obj_path)

        # 获取属性的 RNA 信息
        rna = getattr(obj, "bl_rna", None)
        if not rna:
            return None
            # return f"[Error] Object {obj} has no RNA type"

        prop = rna.properties.get(attr_name)
        if not prop:
            return None
            # return f"[Error] Attribute '{attr_name}' not found"

        return prop.name

    except Exception as e:
        # print(f"Error getting RNA display name for '{path_str}': {e}")
        return None


def update_item_remark(self, context):
    valid_path, key = get_msgbus_key(self.RNA_path)
    if valid_path:
        name = get_rna_display_name(self.RNA_path)
        if name and self.Remarks == f"":
            self.Remarks = f"{name}"


def update_registered_status(self, context):
    msgbus_collection = context.scene.text_manager_prefs.msgbus_collection
    index = -1
    for i, item in enumerate(msgbus_collection):
        if item == self:
            index = i
            break
    if index == -1:
        return
    if self.is_registered:
        bpy.ops.script_manager.msgbus_register_msgbus(index=index)
    else:
        bpy.ops.script_manager.msgbus_unregister_msgbus(RNA_path=self.RNA_path)


class ScriptManagerMsgBusItem(bpy.types.PropertyGroup):
    Remarks: StringProperty(name="Remarks", default="")
    RNA_path: StringProperty(name="RNA Path", default="", update=update_item_remark)
    text_pointer: PointerProperty(type=bpy.types.Text)
    is_registered: BoolProperty(name="Is Registered", default=False, update=update_registered_status)
    update_flag: BoolProperty(name="flag", default=False)
    msgbus_run_time: FloatProperty(name="Run Time", default=0.0)


class SCRIPTMANAGER_UL_MsgBus(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.alignment = "LEFT"
        row.label(text=f"{index}.")
        row.alignment = "EXPAND"
        row.prop(item, "Remarks", text="", icon="BOOKMARKS")
        row.prop(item, "RNA_path", text="")
        row.prop(item, "text_pointer", text="")
        # op = row.operator("script_manager.msgbus_register_msgbus", icon="PLUS", text="")
        # op.index = index
        # op1 = row.operator("script_manager.msgbus_unregister_msgbus", icon="TRASH", text="")
        # op1.RNA_path = item.RNA_path
        # row.prop(item, "is_registered", text="", icon="HIDE_OFF" if item.is_registered else "HIDE_ON")
        subrow = row.row(align=True)  # 创建子布局
        subrow.enabled = item.RNA_path != "" and item.text_pointer != None  # 禁用交互(灰化)
        subrow.prop(item, "is_registered", text="", icon="RECORD_ON" if item.is_registered else "RECORD_OFF")
        row.label(text=f"{item.msgbus_run_time:.2f}ms", icon="TIME")


class ScriptManagerMsgBusPanel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_ScriptManagerMsgBusPanel"
    bl_label = "Trigger"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Script Manager"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        box = col.box()
        box.label(text=_("Monitor property changes using msgbus"))
        box.label(text=_("Only works for RNA properties; view updates and animation updates have no effect"))
        box.label(text=_("Geometry node socket properties are not supported"))
        box.label(text=_("Item content:   Note   |   Monitored property path    |   Script to execute   |   Is active    |   Last execution time"))
        row = col.row()
        row.template_list("SCRIPTMANAGER_UL_MsgBus", "", context.scene.text_manager_prefs, "msgbus_collection", context.scene.text_manager_prefs, "msgbus_index", rows=5)
        col1 = row.column(align=True)
        col1.operator("script_manager.msgbus_add_item", icon="ADD", text="")
        col1.operator("script_manager.msgbus_remove_item", icon="REMOVE", text="")
        col1.separator()
        col1.operator("script_manager.msgbus_move_item_up", icon="TRIA_UP", text="")
        col1.operator("script_manager.msgbus_move_item_down", icon="TRIA_DOWN", text="")


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
                self.report({"ERROR"}, _("This item is not unregistered. Please unregister it before deleting."))
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


# NOTE 制作属性监听回调函数
def make_ScriptManagerMsgBus_update_callback(index):
    def ScriptManagerMsgBus_update_callback():
        prefs = bpy.context.scene.text_manager_prefs
        msgbus_collection = prefs.msgbus_collection
        start_time = time.perf_counter()  # 记录开始时间
        # DebugPrint(f"{owner}属性更新了,执行{text_name}")
        run_text_block(bpy.data.texts[msgbus_collection[index].text_pointer.name])
        msgbus_collection[index].update_flag = not msgbus_collection[index].update_flag
        end_time = time.perf_counter()  # 记录结束时间
        msgbus_collection[index].msgbus_run_time = (end_time - start_time) * 1000
        DebugPrint(f"Triggered property updated, executing {msgbus_collection[index].text_pointer.name}, took {msgbus_collection[index].msgbus_run_time:.2f} ms")

    return ScriptManagerMsgBus_update_callback


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


def get_msgbus_key(path_str: str) -> tuple[bool, object]:
    try:
        if "." not in path_str:
            return False, None
            # raise ValueError("路径必须包含属性，如 'bpy.data.scenes[\"Scene\"].frame_current'")

        parts = path_str.split(".")
        property_name = parts[-1]  # 最后一个部分是属性名，如 'frame_current'
        base_str = ".".join(parts[:-1])  # 基对象，如 'bpy.data.scenes["Scene"]'

        base_obj = eval(base_str, {"__builtins__": {}}, {"bpy": bpy})

        if base_obj is None:
            return False, None
            # raise ValueError(f"无法解析基对象: {base_str}")

        key = base_obj.path_resolve(property_name, False)

        if key is None:
            return False, None
            # raise ValueError(f"属性 '{property_name}' 在对象中无效")

        return True, key

    except Exception as e:
        print(f"Parsing error: {e}")
        return False, None


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


classes = (
    ScriptManagerAddonPreferences,
    ScriptManagerPreviewPropertyItem,
    ScriptManagerItem,
    ScriptManagerMsgBusItem,
    ScriptManagerPrefs,
    SCRIPTMANAGER_UL_texts,
    SCRIPTMANAGER_UL_MsgBus,
    PT_SCRIPTMANAGERPanel,
    PT_SCRIPTMANAGERSubPanel,
    ScriptManagerMsgBusPanel,
    PT_SCRIPTMANAGERTools,
    PT_SCRIPTMANAGERDebug,
    SCRIPTMANAGER_OT_remove_all_handlers,
    SCRIPTMANAGER_OT_remove_handler,
    SCRIPTMANAGER_OT_add_item,
    SCRIPTMANAGER_OT_remove_item,
    SCRIPTMANAGER_OT_move_item_up,
    SCRIPTMANAGER_OT_move_item_down,
    SCRIPTMANAGER_OT_new_text,
    SCRIPTMANAGER_OT_run_text,
    SCRIPTMANAGER_OT_open_in_vscode,
    SCRIPT_MANAGER_OT_add_preview_property,
    SCRIPT_MANAGER_OT_remove_preview_property,
    SCRIPTMANAGER_OT_remove_addon_handlers,
    ScriptManagerMsgBus_OT_add_item,
    ScriptManagerMsgBus_OT_remove_item,
    ScriptManagerMsgBus_OT_move_item_up,
    ScriptManagerMsgBus_OT_move_item_down,
    ScriptManagerMsgBus_OT_register_msgbus,
    ScriptManagerMsgBus_OT_unregister_msgbus,
)


@bpy.app.handlers.persistent
def ScriptManager_load_post_handler(dummy):
    # print("ScriptManager: 加载了新文件")

    # 延迟执行以确保上下文完全准备好
    def delayed_restore():
        restore_handlers()
        return None

    bpy.app.timers.register(delayed_restore, first_interval=0.1)


def restore_handlers():
    """恢复之前注册的handlers"""
    # 检查上下文是否准备就绪
    try:
        if not hasattr(bpy.context, "scene") or not bpy.context.scene:
            print("ScriptManager: Context not ready")
            return False
    except:
        print("ScriptManager: Cannot access context")
        return False

    try:
        prefs = bpy.context.scene.text_manager_prefs
        if not prefs:
            print("ScriptManager: Preferences not ready")
            return False
    except:
        print("ScriptManager: Cannot access preferences")
        return False

    handlers_restored = False
    frame_handlers_num = 0
    deps_handlers_num = 0
    msgbus_num = 0
    # 恢复帧更新handlers
    for item in prefs.text_manager_collection:
        if item.text_pointer and item.run_in_frame_update:
            has_handler = False
            # 检查是否已经存在对应的handler
            for handler in bpy.app.handlers.frame_change_pre:
                if hasattr(handler, "_ScriptManagerItem_FC_ID") and handler._ScriptManagerItem_FC_ID == item.text_pointer.name:
                    has_handler = True
                    break

            # 如果不存在，则添加
            if not has_handler:
                handler_func = make_ScriptManager_frame_update_handler(item.text_pointer.name)
                bpy.app.handlers.frame_change_pre.append(handler_func)
                print(f"ScriptManager: Restore frame update: {item.text_pointer.name}")
                handlers_restored = True
                frame_handlers_num += 1

    # 恢复依赖图更新handlers
    for item in prefs.text_manager_collection:
        if item.text_pointer and item.run_in_desgaph_update:
            has_handler = False
            # 检查是否已经存在对应的handler
            for handler in bpy.app.handlers.depsgraph_update_post:
                if hasattr(handler, "_ScriptManagerItem_DC_ID") and handler._ScriptManagerItem_DC_ID == item.text_pointer.name:
                    has_handler = True
                    break

            # 如果不存在，则添加
            if not has_handler:
                handler_func = make_ScriptManager_depsgraph_update_handler(item.text_pointer.name)
                bpy.app.handlers.depsgraph_update_post.append(handler_func)
                print(f"ScriptManager: Restore depsgraph update handler: {item.text_pointer.name}")
                handlers_restored = True
                deps_handlers_num += 1
    # 恢复msgbus
    for i, item in enumerate(prefs.msgbus_collection):
        if item.RNA_path != "" and item.text_pointer and item.is_registered:
            RNA_path = prefs.msgbus_collection[i].RNA_path
            text_name = prefs.msgbus_collection[i].text_pointer.name if prefs.msgbus_collection[i].text_pointer else ""
            if RNA_path == "" or text_name == "":
                DebugPrint(f"ScriptManager: Path or script cannot be empty: {RNA_path} - {text_name}")
                continue
            valid_path, key = get_msgbus_key(RNA_path)
            if RNA_path and valid_path and text_name != "":
                DebugPrint(f"ScriptManager: Register Trigger monitoring: {RNA_path} - {text_name}-key: {key}")

                bpy.msgbus.subscribe_rna(
                    key=key,
                    owner=sys.intern(str(RNA_path).strip()),  # 保证注册时和注销时是完全一致的对象
                    args=(),
                    notify=make_ScriptManagerMsgBus_update_callback(i),
                )
                handlers_restored = True
                msgbus_num += 1
            else:
                DebugPrint(f"ScriptManager: Invalid path or the specified script is empty: {RNA_path}")
                continue

    if handlers_restored:
        print(f"ScriptManager: Restore complete, restored {frame_handlers_num} frame update, {deps_handlers_num} depsgraph update, {msgbus_num} Trigger monitors")
    else:
        print("ScriptManager: No update to restore")

    return handlers_restored


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.text_manager_prefs = PointerProperty(type=ScriptManagerPrefs)

    # 注册文件加载完成后的处理函数
    bpy.app.handlers.load_post.append(ScriptManager_load_post_handler)
    load_language()

    # 在注册完成后恢复handlers(针对插件重新启用的情况)
    def delayed_restore():
        restore_handlers()
        return None

    bpy.app.timers.register(delayed_restore, first_interval=1.0)


def unregister():
    # 移除文件加载完成后的处理函数
    if ScriptManager_load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(ScriptManager_load_post_handler)

    del bpy.types.Scene.text_manager_prefs

    for c in reversed(classes):
        bpy.utils.unregister_class(c)
