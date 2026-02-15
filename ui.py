import bpy
from .i18n import *
from .utils import *


class ScriptManagerAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__  # 插件的 module 名
    vscode_path: bpy.props.StringProperty(name=translations("VSCode Path"), subtype="FILE_PATH", default="D:/rj/vscode/Microsoft VS Code/Code.exe")

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "vscode_path")


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
        col.operator("script_manager.new_text", text=translations("New Text"))
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
        split.prop(scene.text_manager_prefs, "use_auto_reload_timer", text=translations("Use Auto Reload Timer"), icon="TIME")
        split.label(text=f"{scene.text_manager_prefs.auto_reload_use_time:.2f}ms", icon="RECORD_OFF" if not auto_reload_flag else "RECORD_ON")
        col.prop(scene.text_manager_prefs, "auto_reload_timer_interval", text=translations("Auto-reload timer interval"))


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
                split.prop(item, "run_in_frame_update", text=translations("Run In Frame Update"), icon="PLAY")
                split.label(text=f"{item.frame_update_run_time:.2f}ms", icon="RECORD_OFF" if not item.frame_update_flag else "RECORD_ON")

                # --- 2. Depsgraph Update ---
                row1 = box.row()
                split = row1.split(factor=0.8)
                split.prop(item, "run_in_desgaph_update", text=translations("Run In Depsgraph Update"), icon="FILE_REFRESH")
                split.label(text=f"{item.desgaph_update_run_time:.2f}ms", icon="RECORD_OFF" if not item.desgaph_updata_flag else "RECORD_ON")

                # --- 3. Render Pre ---
                row1 = box.row()
                split = row1.split(factor=0.8)
                split.prop(item, "run_in_render_pre", text=translations("Run In Render Pre"), icon="RESTRICT_RENDER_OFF")
                split.label(text=f"{item.render_pre_run_time:.2f}ms", icon="RECORD_OFF" if not item.render_pre_flag else "RECORD_ON")

                # --- 4. Render Post ---
                row1 = box.row()
                split = row1.split(factor=0.8)
                split.prop(item, "run_in_render_post", text=translations("Run In Render Post"), icon="RESTRICT_RENDER_ON")
                split.label(text=f"{item.render_post_run_time:.2f}ms", icon="RECORD_OFF" if not item.render_post_flag else "RECORD_ON")

                # --- 5. Load Post ---
                row1 = box.row()
                split = row1.split(factor=0.8)
                split.prop(item, "run_in_load_post", text=translations("Run In Load Post"), icon="INDIRECT_ONLY_ON")
                split.label(text=f"{item.load_post_run_time:.2f}ms", icon="RECORD_OFF" if not item.load_post_flag else "RECORD_ON")

                # --- 6. Save Pre ---
                row1 = box.row()
                split = row1.split(factor=0.8)
                split.prop(item, "run_in_save_pre", text=translations("Run In Save Pre"), icon="FILE_TICK")
                split.label(text=f"{item.save_pre_run_time:.2f}ms", icon="RECORD_OFF" if not item.save_pre_flag else "RECORD_ON")
            else:
                box.label(text=translations("No text data block specified"))
        else:
            box.label(text=translations("No available text data block"))


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
                row.label(text=translations("No property path"))

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
                return translations("[Not iterable]")

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
        col.prop(prefs, "debug_mode", text=translations("Print debug info"), icon="SETTINGS")
        col.prop(prefs, "auto_reload_in_file_open", text=translations("Restore handlers and triggers when opening file"), icon="FILE_REFRESH")
        col.operator("script_manager.remove_addon_handlers", text=translations("Remove plugin handler"))
        col.label(text=translations("Plugin handler"))
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
        col.operator("script_manager.remove_all_handlers", text=translations("Remove all handlers"))
        col.operator("script_manager.remove_handler", text=translations("Remove specified handler"))
        col.prop(prefs, "handler_index", text=translations("Target Handler"))
        i = 0
        frame_change_pre_names = [handler.__name__ for handler in bpy.app.handlers.frame_change_pre]
        depsgraph_update_post_names = [handler.__name__ for handler in bpy.app.handlers.depsgraph_update_post]
        row = col.row()
        row.label(text=translations("All handlers"))
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
        box.label(text=translations("Use msgbus to monitor property changes and trigger specified scripts"))
        box.label(text=translations("Only works for RNA properties; view updates and animation updates have no effect"))
        box.label(text=translations("Geometry node socket properties are not supported"))
        box.label(text=translations("Item content:   Note   |   Monitored property path    |   Script to execute   |   Is active    |   Last execution time"))
        row = col.row()
        row.template_list("SCRIPTMANAGER_UL_MsgBus", "", context.scene.text_manager_prefs, "msgbus_collection", context.scene.text_manager_prefs, "msgbus_index", rows=5)
        col1 = row.column(align=True)
        col1.operator("script_manager.msgbus_add_item", icon="ADD", text="")
        col1.operator("script_manager.msgbus_remove_item", icon="REMOVE", text="")
        col1.separator()
        col1.operator("script_manager.msgbus_move_item_up", icon="TRIA_UP", text="")
        col1.operator("script_manager.msgbus_move_item_down", icon="TRIA_DOWN", text="")


classes = [
    ScriptManagerAddonPreferences,
    PT_SCRIPTMANAGERPanel,
    PT_SCRIPTMANAGERSubPanel,
    PT_SCRIPTMANAGERTools,
    PT_SCRIPTMANAGERDebug,
    SCRIPTMANAGER_UL_texts,
    SCRIPTMANAGER_UL_MsgBus,
    ScriptManagerMsgBusPanel,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
