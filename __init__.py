# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "Script Manager",
    "author": "LEDingQ",
    "description": "",
    "blender": (3, 4, 0),
    "version": (0, 1, 1),
    "location": "",
    "warning": "",
    "category": "Generic",
}

import bpy
from bpy.props import StringProperty, BoolProperty, PointerProperty, FloatProperty, CollectionProperty, IntProperty
import os
import time
import subprocess


def DebugPrint(*args):
    if bpy.context.scene.text_manager_prefs.debug_mode:
        print(*args)


class ScriptManagerAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__  # 插件的 module 名

    vscode_path: bpy.props.StringProperty(name="VSCode 路径", subtype="FILE_PATH")

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "vscode_path")


class SCRIPTMANAGER_OT_TestOperator(bpy.types.Operator):
    bl_idname = "object.test_operator"
    bl_label = "Test Operator"
    bl_description = "This is a test operator"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        prefs = context.scene.text_manager_prefs
        text_name = [text.name for text in bpy.data.texts]
        for handler in bpy.app.handlers.frame_change_pre:
            if hasattr(handler, "_ScriptManagerItem_FC_ID"):
                DebugPrint(handler._ScriptManagerItem_FC_ID)
        for handler in bpy.app.handlers.depsgraph_update_post:
            if hasattr(handler, "_ScriptManagerItem_DC_ID"):
                DebugPrint(handler._ScriptManagerItem_DC_ID)
        DebugPrint("Test Operator Executed")
        return {"FINISHED"}


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
            self.report({"INFO"}, f"已移除 Handler: {target_handler_names}")
            return {"FINISHED"}
        else:
            self.report({"WARNING"}, f"未找到 Handler: {target_handler_names}")
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
        addon_prefs = context.preferences.addons[__name__].preferences
        vscode_path = addon_prefs.vscode_path.strip('"').strip()  # 去掉多余空格和引号
        text = bpy.data.texts.get(self.text_name)

        if text is None:
            self.report({"ERROR"}, "没有选择文本")
            return {"CANCELLED"}

        if not text.filepath:
            self.report({"ERROR"}, "文本没有保存")
            return {"CANCELLED"}

        filepath = bpy.path.abspath(text.filepath)

        if not os.path.exists(filepath):
            self.report({"ERROR"}, f"文件不存在: {filepath}")
            return {"CANCELLED"}

        # 处理 VSCode 路径
        vscode_path = bpy.path.abspath(vscode_path)
        if os.path.isdir(vscode_path):
            # 如果是目录，自动补全 Code.exe
            candidate = os.path.join(vscode_path, "Code.exe")
            if os.path.exists(candidate):
                vscode_path = candidate
            else:
                self.report({"ERROR"}, f"VSCode 路径是目录，未找到 Code.exe: {candidate}")
                return {"CANCELLED"}

        elif os.path.isfile(vscode_path):
            # 如果是文件，直接用
            if not vscode_path.lower().endswith("code.exe"):
                self.report({"WARNING"}, f"指定的文件不是 Code.exe: {vscode_path}")
        else:
            # 如果路径不存在，尝试补全 Code.exe
            candidate = vscode_path + "\\Code.exe"
            if os.path.exists(candidate):
                vscode_path = candidate
            else:
                self.report({"ERROR"}, f"VSCode 路径错误: {vscode_path}")
                return {"CANCELLED"}

        try:
            # 调用 VSCode 打开文件
            subprocess.Popen([vscode_path, filepath])
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"启动 VSCode 失败: {str(e)}")
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
        # col.operator("object.test_operator", text="Test Operator") #测试操作符
        col.operator("script_manager.new_text", text="New Text")
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
        split.prop(scene.text_manager_prefs, "use_auto_reload_timer", text="使用自动重载定时器", icon="TIME")
        split.label(text=f"{scene.text_manager_prefs.auto_reload_use_time:.2f}ms", icon="RECORD_OFF" if not auto_reload_flag else "RECORD_ON")
        col.prop(scene.text_manager_prefs, "auto_reload_timer_interval", text="自动重载定时器间隔")


class PT_SCRIPTMANAGERSubPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_script_manager_subpanel"
    bl_label = "Script Options"
    bl_parent_id = "OBJECT_PT_script_manager"  # 指定父面板
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
                # 在box内部创建一行
                row = box.row()
                row.scale_y = 2.0  # 按钮放大
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
                split = row1.split(factor=0.8)  # 左边占 70%，右边占 30%
                split.prop(item, "run_in_frame_update", text="Run In Frame Update", icon="PLAY")
                split.label(text=f"{item.frame_update_run_time:.2f}ms", icon="RECORD_OFF" if not item.frame_update_flag else "RECORD_ON")
                row1 = box.row()
                split = row1.split(factor=0.8)  # 左边占 70%，右边占 30%
                split.prop(item, "run_in_desgaph_update", text="Run In Depsgraph Update", icon="FILE_REFRESH")
                split.label(text=f"{item.desgaph_update_run_time:.2f}ms", icon="RECORD_OFF" if not item.desgaph_updata_flag else "RECORD_ON")
            else:
                box.label(text="没有指定文本数据块")
        else:
            box.label(text="没有可用的文本数据块")


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
                        # 如果是向量属性（长度 2 或 3）
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
                row.label(text="无属性路径")

    def format_value(self, value):
        """统一格式化显示值，保留小数点后五位"""

        # 布尔值
        if isinstance(value, bool):
            return str(value)
        # Blender 数据块
        if hasattr(value, "name") and hasattr(value, "type"):
            return f"{value.name} ({value.type})"
        elif hasattr(value, "name"):
            return value.name

        # 特殊集合类型（如 bpy.data.collections）
        if "bpy_prop_collection" in str(type(value)) or "bpy.data" in str(type(value)):
            try:
                items = [item.name for item in list(value)[:3]]
                return f"({len(value)}) [{', '.join(items)}]" if items else f"({len(value)}) []"
            except:
                return f"[集合] {len(value)}项"

        # 可迭代对象（如 list, tuple）
        if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
            try:
                items = [self.format_number(x) for x in list(value)[:5]]
                return f"[{', '.join(items)}]" if items else "[]"
            except:
                return "[不可遍历]"

        # 数值类型（int, float）保留五位小数
        if isinstance(value, (int, float)):
            return self.format_number(value)

        # 基础类型（如字符串、布尔值等）
        return str(value)[:50] + ("..." if len(str(value)) > 50 else "")

    def format_number(self, x):
        """统一格式化数值类型，保留五位小数"""
        if isinstance(x, (int, float)):
            return f"{x:.5f}"
        return str(x)[:20]


class PT_SCRIPTMANAGERDebug(bpy.types.Panel):
    bl_idname = "OBJECT_PT_script_manager_debug"
    bl_label = "Debug"
    bl_parent_id = "OBJECT_PT_script_manager"  # 指定父面板
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Script Manager"

    def draw(self, context):
        layout = self.layout
        prefs = context.scene.text_manager_prefs
        col = layout.column()
        col.prop(prefs, "debug_mode", text="打印调试信息", icon="SETTINGS")
        col.operator("script_manager.remove_addon_handlers", text="移除插件的Handler")
        col.label(text="插件的handler")
        box = col.box()
        i = 0
        for handler in bpy.app.handlers.frame_change_pre:
            if hasattr(handler, "_ScriptManagerItem_FC_ID"):
                box.label(text=f"{i}.帧更新: {handler._ScriptManagerItem_FC_ID}")
                i += 1
        for handler in bpy.app.handlers.depsgraph_update_post:
            if hasattr(handler, "_ScriptManagerItem_DC_ID"):
                box.label(text=f"{i}.依赖图: {handler._ScriptManagerItem_DC_ID}")
                i += 1
        col.operator("script_manager.remove_all_handlers", text="移除所有Handler")
        col.operator("script_manager.remove_handler", text="移除指定Handler")
        col.prop(prefs, "handler_index", text="目标Handler")
        i = 0
        frame_change_pre_names = [handler.__name__ for handler in bpy.app.handlers.frame_change_pre]
        depsgraph_update_post_names = [handler.__name__ for handler in bpy.app.handlers.depsgraph_update_post]
        col.label(text="所有handler")
        box = col.box()
        for name in frame_change_pre_names:
            row = box.row()
            if i == prefs.handler_index:
                row.alert = True  # 高亮这一行
            row.label(text=f"{i}. 帧更新: {name}")
            i += 1

        for name in depsgraph_update_post_names:
            row = box.row()
            if i == prefs.handler_index:
                row.alert = True  # 高亮这一行
            row.label(text=f"{i}. 依赖图: {name}")
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
            print("添加帧更新回调")
        else:
            print("已更新帧更新回调")
    else:
        for handler in bpy.app.handlers.frame_change_pre:
            if hasattr(handler, "_ScriptManagerItem_FC_ID"):
                if item.text_pointer.name in handler._ScriptManagerItem_FC_ID:
                    bpy.app.handlers.frame_change_pre.remove(handler)
        print("移除帧更新回调")


def use_desgraph_update(self, context):
    # 添加和移除 depsgraph 更新回调
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
            print("添加 depsgraph 更新回调")
        else:
            print("已更新 depsgraph 更新回调")
    else:
        for handler in bpy.app.handlers.depsgraph_update_post:
            if hasattr(handler, "_ScriptManagerItem_DC_ID"):
                if item.text_pointer.name in handler._ScriptManagerItem_DC_ID:
                    bpy.app.handlers.depsgraph_update_post.remove(handler)
        print("移除 depsgraph 更新回调")


# NOTE 防止使用相同的TEXT
def update_text_pointer(self, context):
    prefs = context.scene.text_manager_prefs
    current_name = self.text_pointer.name if self.text_pointer else None
    # 遍历其他 item
    for item in prefs.text_manager_collection:
        if item == self:
            continue
        if item.text_pointer and current_name and item.text_pointer.name == current_name:
            DebugPrint("当前文本被其他 item 使用")
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
        row.prop(item, "text_pointer", text="")
        row.prop(item, "Remarks", text="", emboss=True, icon="BOOKMARKS")
        row.alignment = "RIGHT"
        row.operator("script_manager.run_text", icon="PLAY", text="").text_name = item.text_pointer.name if item.text_pointer else ""


def auto_reload_timer_callback():
    """自动重载文本数据块"""
    global auto_reload_flag
    start_time = time.perf_counter()  # 记录开始时间
    prefs = bpy.context.scene.text_manager_prefs
    # print("自动重载定时器回调")
    # 遍历所有管理的文本
    for item in prefs.text_manager_collection:
        text = item.text_pointer
        if text is None:
            continue
        # print(text.name, text.is_modified, text.is_dirty)
        # 如果文本被修改（is_modified 为 True）并且有文件路径
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


# TODO: 重载方式不一样is_modified始终为True
def reload_text_safely(text: bpy.types.Text) -> bool:
    if not hasattr(bpy.data.window_managers[0].windows[0].screen.areas[0], "type"):
        print("不存在area,无法重载")
        return False
    temp_area = bpy.data.window_managers[0].windows[0].screen.areas[0]
    print(temp_area)
    if text is not None:
        old_area_type = temp_area.type
        # 临时替换当前的上下文
        temp_area.type = "TEXT_EDITOR"
        space = temp_area.spaces
        print(old_area_type)
        space.active.text = text
        print(bpy.ops.text.reload.poll())
        if bpy.ops.text.reload.poll():
            bpy.ops.text.reload()
        else:
            # temp_area.type = old_area_type
            return False
        # temp_area.type = old_area_type
        return True
    else:
        return False


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
            print("自动重载定时器已启动")
        else:
            bpy.app.timers.unregister(auto_reload_timer_callback)
            bpy.app.timers.register(auto_reload_timer_callback, first_interval=prefs.auto_reload_timer_interval)
            print("自动重载定时器已重启")
    else:
        # 移除定时器
        if bpy.app.timers.is_registered(auto_reload_timer_callback):
            bpy.app.timers.unregister(auto_reload_timer_callback)
            print("自动重载定时器已停止")
        else:
            print("自动重载定时器未启动")


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
            DebugPrint("帧更新", ScriptManager_frame_update_handler._ScriptManagerItem_FC_ID)
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
            DebugPrint("依赖图更新", ScriptManager_depsgraph_update_handler._ScriptManagerItem_DC_ID)
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


# 插件属性组
class ScriptManagerPrefs(bpy.types.PropertyGroup):
    # 是否启用自动重载定时器
    use_auto_reload_timer: BoolProperty(name="Use Auto Reload Timer", default=False, update=use_auto_reload_update)
    # 自动重载定时器间隔
    auto_reload_timer_interval: FloatProperty(name="Auto Reload Timer Interval (s)", default=5.0, min=1)
    auto_reload_use_time: FloatProperty(name="Auto Reload Use Time", default=0.0)
    frame_handler_registered: BoolProperty(name="Frame Handler Registered", default=False)
    deps_handler_registered: BoolProperty(name="Deps Handler Registered", default=False)
    text_manager_collection: CollectionProperty(type=ScriptManagerItem)
    script_manager_index: IntProperty(name="Script Manager Index", default=0, update=update_script_manager_index)
    preview_properties: bpy.props.CollectionProperty(type=ScriptManagerPreviewPropertyItem)
    preview_properties_index: bpy.props.IntProperty(name="Index", default=0)
    preview_properties_num: bpy.props.IntProperty(name="Number", default=0)
    handler_index: IntProperty(name="Handler Index", default=0, min=0)
    target_handler_name: StringProperty(name="Target Handler Name", default="")
    debug_mode: BoolProperty(name="Debug Mode", default=False)


classes = (
    ScriptManagerAddonPreferences,
    ScriptManagerPreviewPropertyItem,
    ScriptManagerItem,
    ScriptManagerPrefs,
    SCRIPTMANAGER_UL_texts,
    PT_SCRIPTMANAGERPanel,
    PT_SCRIPTMANAGERSubPanel,
    PT_SCRIPTMANAGERTools,
    PT_SCRIPTMANAGERDebug,
    SCRIPTMANAGER_OT_TestOperator,
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
)


@bpy.app.handlers.persistent
def ScriptManager_load_post_handler(dummy):
    """文件加载完成后的处理函数"""
    print("ScriptManager: 加载了新文件")

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
            print("ScriptManager: 上下文未准备好")
            return False
    except:
        print("ScriptManager: 无法访问上下文")
        return False

    try:
        prefs = bpy.context.scene.text_manager_prefs
        if not prefs:
            print("ScriptManager: prefs未准备好")
            return False
    except:
        print("ScriptManager: 无法访问prefs")
        return False

    print(f"ScriptManager: 开始恢复handlers，共有 {len(prefs.text_manager_collection)} 个items")

    handlers_restored = False

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
                print(f"ScriptManager: 恢复帧更新handler: {item.text_pointer.name}")
                handlers_restored = True

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
                print(f"ScriptManager: 恢复依赖图更新handler: {item.text_pointer.name}")
                handlers_restored = True

    if handlers_restored:
        print("ScriptManager: handlers恢复完成")
    else:
        print("ScriptManager: 没有需要恢复的handlers")

    return handlers_restored


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.text_manager_prefs = PointerProperty(type=ScriptManagerPrefs)
    print("ScriptManager: 脚本管理器注册成功")

    # 注册文件加载完成后的处理函数
    bpy.app.handlers.load_post.append(ScriptManager_load_post_handler)
    print("ScriptManager: 已注册ScriptManager_load_post_handler")

    # 在注册完成后恢复handlers（针对插件重新启用的情况）
    def delayed_restore():
        restore_handlers()
        return None

    bpy.app.timers.register(delayed_restore, first_interval=1.0)


def unregister():
    # 移除文件加载完成后的处理函数
    if ScriptManager_load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(ScriptManager_load_post_handler)
        print("ScriptManager: 已移除ScriptManager_load_post_handler")

    del bpy.types.Scene.text_manager_prefs

    for c in reversed(classes):
        bpy.utils.unregister_class(c)
