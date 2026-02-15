import bpy
import os
from .i18n import *
import time
import sys
from bpy.app.handlers import persistent

# 自动重载标注符
auto_reload_flag = False


def DebugPrint(*args):
    if bpy.context.scene.text_manager_prefs.debug_mode:
        print(*args)


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
            print(translations("Add frame update"))
        else:
            print(translations("Frame update updated"))
    else:
        for handler in bpy.app.handlers.frame_change_pre:
            if hasattr(handler, "_ScriptManagerItem_FC_ID"):
                if item.text_pointer.name in handler._ScriptManagerItem_FC_ID:
                    bpy.app.handlers.frame_change_pre.remove(handler)
        print(translations("Remove frame update"))


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
            print(translations("Add depsgraph update"))
        else:
            print(translations("Depsgraph update updated"))
    else:
        for handler in bpy.app.handlers.depsgraph_update_post:
            if hasattr(handler, "_ScriptManagerItem_DC_ID"):
                if item.text_pointer.name in handler._ScriptManagerItem_DC_ID:
                    bpy.app.handlers.depsgraph_update_post.remove(handler)
        print(translations("Remove depsgraph update"))


# NOTE 防止使用相同的TEXT
def update_text_pointer(self, context):
    prefs = context.scene.text_manager_prefs
    current_name = self.text_pointer.name if self.text_pointer else None
    # 遍历其他 item
    for item in prefs.text_manager_collection:
        if item == self:
            continue
        if item.text_pointer and current_name and item.text_pointer.name == current_name:
            DebugPrint(translations("Current text is used by another item"))
            # 重置为 None，或者弹出提示
            item.text_pointer = None
            break


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


# 布尔属性更新回调
def use_auto_reload_update(self, context):
    prefs = context.scene.text_manager_prefs
    if prefs.use_auto_reload_timer:
        # 添加定时器
        if not bpy.app.timers.is_registered(auto_reload_timer_callback):
            bpy.app.timers.register(auto_reload_timer_callback, first_interval=prefs.auto_reload_timer_interval)
            print(translations("Auto-reload timer started"))
        else:
            bpy.app.timers.unregister(auto_reload_timer_callback)
            bpy.app.timers.register(auto_reload_timer_callback, first_interval=prefs.auto_reload_timer_interval)
            print(translations("Auto-reload timer restarted"))
    else:
        # 移除定时器
        if bpy.app.timers.is_registered(auto_reload_timer_callback):
            bpy.app.timers.unregister(auto_reload_timer_callback)
            print(translations("Auto-reload timer stopped"))
        else:
            print(translations("Auto-reload timer not started"))


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


@bpy.app.handlers.persistent
def ScriptManager_load_post_handler(dummy):
    # print("ScriptManager: 加载了新文件")

    # 延迟执行以确保上下文完全准备好
    def delayed_restore():
        restore_handlers()
        return None

    bpy.app.timers.register(delayed_restore, first_interval=0.1)


def restore_handlers():
    """恢复之前注册的handlers，并执行标记为加载时运行的脚本，同时恢复定时器"""
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
    render_pre_num = 0
    render_post_num = 0
    load_post_exec_num = 0
    save_pre_num = 0
    msgbus_num = 0
    auto_reload_timer_status = "OFF"

    # 1. 恢复帧更新 (Frame Update)
    for item in prefs.text_manager_collection:
        if item.text_pointer and item.run_in_frame_update:
            has_handler = False
            for handler in bpy.app.handlers.frame_change_pre:
                if hasattr(handler, "_ScriptManagerItem_FC_ID") and handler._ScriptManagerItem_FC_ID == item.text_pointer.name:
                    has_handler = True
                    break
            if not has_handler:
                bpy.app.handlers.frame_change_pre.append(make_ScriptManager_frame_update_handler(item.text_pointer.name))
                frame_handlers_num += 1
                handlers_restored = True

    # 2. 恢复依赖图更新 (Depsgraph Update)
    for item in prefs.text_manager_collection:
        if item.text_pointer and item.run_in_desgaph_update:
            has_handler = False
            for handler in bpy.app.handlers.depsgraph_update_post:
                if hasattr(handler, "_ScriptManagerItem_DC_ID") and handler._ScriptManagerItem_DC_ID == item.text_pointer.name:
                    has_handler = True
                    break
            if not has_handler:
                bpy.app.handlers.depsgraph_update_post.append(make_ScriptManager_depsgraph_update_handler(item.text_pointer.name))
                deps_handlers_num += 1
                handlers_restored = True

    # 3. 恢复渲染前 (Render Pre)
    for item in prefs.text_manager_collection:
        if item.text_pointer and getattr(item, "run_in_render_pre", False):
            has_handler = False
            for handler in bpy.app.handlers.render_pre:
                if hasattr(handler, "_ScriptManagerItem_RPRE_ID") and handler._ScriptManagerItem_RPRE_ID == item.text_pointer.name:
                    has_handler = True
                    break
            if not has_handler:
                bpy.app.handlers.render_pre.append(make_ScriptManager_render_pre_handler(item.text_pointer.name))
                render_pre_num += 1
                handlers_restored = True

    # 4. 恢复渲染后 (Render Post)
    for item in prefs.text_manager_collection:
        if item.text_pointer and getattr(item, "run_in_render_post", False):
            has_handler = False
            for handler in bpy.app.handlers.render_post:
                if hasattr(handler, "_ScriptManagerItem_RPOST_ID") and handler._ScriptManagerItem_RPOST_ID == item.text_pointer.name:
                    has_handler = True
                    break
            if not has_handler:
                bpy.app.handlers.render_post.append(make_ScriptManager_render_post_handler(item.text_pointer.name))
                render_post_num += 1
                handlers_restored = True

    # 5. 处理 Load Post (执行脚本)
    for item in prefs.text_manager_collection:
        if item.text_pointer and getattr(item, "run_in_load_post", False):
            start_time = time.perf_counter()
            run_text_block(item.text_pointer)
            item.load_post_flag = not item.load_post_flag
            item.updata_flag = not item.updata_flag
            item.load_post_run_time = (time.perf_counter() - start_time) * 1000
            load_post_exec_num += 1
            handlers_restored = True

    # 6. 恢复保存前 (Save Pre)
    for item in prefs.text_manager_collection:
        if item.text_pointer and getattr(item, "run_in_save_pre", False):
            has_handler = False
            for handler in bpy.app.handlers.save_pre:
                if hasattr(handler, "_ScriptManagerItem_SP_ID") and handler._ScriptManagerItem_SP_ID == item.text_pointer.name:
                    has_handler = True
                    break
            if not has_handler:
                bpy.app.handlers.save_pre.append(make_ScriptManager_save_pre_handler(item.text_pointer.name))
                save_pre_num += 1
                handlers_restored = True

    # 7. 恢复 MsgBus
    for i, item in enumerate(prefs.msgbus_collection):
        if item.RNA_path != "" and item.text_pointer and item.is_registered:
            valid_path, key = get_msgbus_key(item.RNA_path)
            if item.RNA_path and valid_path:
                bpy.msgbus.subscribe_rna(
                    key=key,
                    owner=sys.intern(str(item.RNA_path).strip()),
                    args=(),
                    notify=make_ScriptManagerMsgBus_update_callback(i),
                )
                msgbus_num += 1
                handlers_restored = True

    # 8. [新增] 恢复自动重载定时器 (Auto Reload Timer)
    if prefs.use_auto_reload_timer:
        # 调用之前的逻辑函数，self 传 None
        use_auto_reload_update(None, bpy.context)
        auto_reload_timer_status = "ON"
        handlers_restored = True

    # 更新后的 Log 信息
    if handlers_restored:
        # 获取状态的翻译
        timer_translated = translations("ON") if auto_reload_timer_status == "ON" else translations("OFF")

        # 获取整条消息的翻译并格式化
        msg = translations("ScriptManager: Restore complete. Registered: {f} Frame, {d} Deps, {rpre} R-Pre, {rpost} R-Post, {s} Save-Pre. Executed: {l} Load-Scripts. Monitors: {m} Trigger. Timer: {t}.")

        print(msg.format(f=frame_handlers_num, d=deps_handlers_num, rpre=render_pre_num, rpost=render_post_num, s=save_pre_num, l=load_post_exec_num, m=msgbus_num, t=timer_translated))
    else:
        print(translations("ScriptManager: No update to restore"))

    return handlers_restored


# ==============================================================================
# 注册/移除 Handler 的功能函数 (Update Callbacks)
# ==============================================================================


def use_render_pre_update(self, context):
    """在 PropertyGroup 的 update 回调中使用，用于切换渲染前执行"""
    prefs = context.scene.text_manager_prefs
    item = prefs.text_manager_collection[prefs.script_manager_index]

    # 假设 item 中有一个名为 run_in_render_pre 的 BoolProperty
    if item.run_in_render_pre:
        has_handler = False
        # 清理旧的同名 Handler
        for handler in bpy.app.handlers.render_pre:
            if hasattr(handler, "_ScriptManagerItem_RPRE_ID") and handler._ScriptManagerItem_RPRE_ID == item.text_pointer.name:
                bpy.app.handlers.render_pre.remove(handler)
                has_handler = True

        # 添加新的 Handler
        bpy.app.handlers.render_pre.append(make_ScriptManager_render_pre_handler(item.text_pointer.name))

        if not has_handler:
            print(translations("Add render_pre update"))
        else:
            print(translations("Render_pre update updated"))
    else:
        # 移除 Handler
        for handler in bpy.app.handlers.render_pre:
            if hasattr(handler, "_ScriptManagerItem_RPRE_ID"):
                if item.text_pointer.name == handler._ScriptManagerItem_RPRE_ID:
                    bpy.app.handlers.render_pre.remove(handler)
        print(translations("Remove render_pre update"))


def use_render_post_update(self, context):
    """在 PropertyGroup 的 update 回调中使用，用于切换渲染后执行"""
    prefs = context.scene.text_manager_prefs
    item = prefs.text_manager_collection[prefs.script_manager_index]

    # 假设 item 中有一个名为 run_in_render_post 的 BoolProperty
    if item.run_in_render_post:
        has_handler = False
        # 清理旧的同名 Handler
        for handler in bpy.app.handlers.render_post:
            if hasattr(handler, "_ScriptManagerItem_RPOST_ID") and handler._ScriptManagerItem_RPOST_ID == item.text_pointer.name:
                bpy.app.handlers.render_post.remove(handler)
                has_handler = True

        # 添加新的 Handler
        bpy.app.handlers.render_post.append(make_ScriptManager_render_post_handler(item.text_pointer.name))

        if not has_handler:
            print(translations("Add render_post update"))
        else:
            print(translations("Render_post update updated"))
    else:
        # 移除 Handler
        for handler in bpy.app.handlers.render_post:
            if hasattr(handler, "_ScriptManagerItem_RPOST_ID"):
                if item.text_pointer.name == handler._ScriptManagerItem_RPOST_ID:
                    bpy.app.handlers.render_post.remove(handler)
        print(translations("Remove render_post update"))


# ==============================================================================
# Handler 工厂函数 (Handler Factories)
# ==============================================================================


# NOTE Render Pre (渲染前) 回调
def make_ScriptManager_render_pre_handler(item_name):
    def ScriptManager_render_pre_handler(scene):
        start_time = time.perf_counter()
        prefs = scene.text_manager_prefs
        item = None
        # 遍历查找当前对应的 item
        for temp in prefs.text_manager_collection:
            if temp.run_in_render_pre and temp.text_pointer and temp.text_pointer.name == ScriptManager_render_pre_handler._ScriptManagerItem_RPRE_ID:
                item = temp

        if item:
            DebugPrint("Render Pre:", ScriptManager_render_pre_handler._ScriptManagerItem_RPRE_ID)
            run_text_block(item.text_pointer)

            # 更新 UI 标记 (假设有这些 flag)
            item.render_pre_flag = not item.render_pre_flag
            item.updata_flag = not item.updata_flag

            elapsed = (time.perf_counter() - start_time) * 1000
            item.render_pre_run_time = elapsed  # 假设有用于记录时间的属性

    # 设置唯一标识 ID
    ScriptManager_render_pre_handler._ScriptManagerItem_RPRE_ID = item_name
    return ScriptManager_render_pre_handler


# NOTE Render Post (渲染后) 回调
def make_ScriptManager_render_post_handler(item_name):
    def ScriptManager_render_post_handler(scene):
        start_time = time.perf_counter()
        prefs = scene.text_manager_prefs
        item = None
        # 遍历查找当前对应的 item
        for temp in prefs.text_manager_collection:
            if temp.run_in_render_post and temp.text_pointer and temp.text_pointer.name == ScriptManager_render_post_handler._ScriptManagerItem_RPOST_ID:
                item = temp

        if item:
            DebugPrint("Render Post:", ScriptManager_render_post_handler._ScriptManagerItem_RPOST_ID)
            run_text_block(item.text_pointer)

            # 更新 UI 标记 (假设有这些 flag)
            item.render_post_flag = not item.render_post_flag
            item.updata_flag = not item.updata_flag

            elapsed = (time.perf_counter() - start_time) * 1000
            item.render_post_run_time = elapsed  # 假设有用于记录时间的属性

    # 设置唯一标识 ID
    ScriptManager_render_post_handler._ScriptManagerItem_RPOST_ID = item_name
    return ScriptManager_render_post_handler


# ==============================================================================
# 2. Save Pre (文件保存前)
# ==============================================================================


def use_save_pre_update(self, context):
    prefs = context.scene.text_manager_prefs
    item = prefs.text_manager_collection[prefs.script_manager_index]

    # 假设 Item 中有 run_in_save_pre 属性
    if item.run_in_save_pre:
        has_handler = False
        # 清理旧的 Handler
        for handler in bpy.app.handlers.save_pre:
            if hasattr(handler, "_ScriptManagerItem_SP_ID") and handler._ScriptManagerItem_SP_ID == item.text_pointer.name:
                if item.text_pointer.name in handler._ScriptManagerItem_SP_ID:
                    bpy.app.handlers.save_pre.remove(handler)
                    has_handler = True

        # 添加新 Handler
        bpy.app.handlers.save_pre.append(make_ScriptManager_save_pre_handler(item.text_pointer.name))

        if not has_handler:
            print(translations("Add save_pre update"))
        else:
            print(translations("Save_pre update updated"))
    else:
        # 移除 Handler
        for handler in bpy.app.handlers.save_pre:
            if hasattr(handler, "_ScriptManagerItem_SP_ID"):
                if item.text_pointer.name in handler._ScriptManagerItem_SP_ID:
                    bpy.app.handlers.save_pre.remove(handler)
        print(translations("Remove save_pre update"))


# NOTE save_pre 回调
def make_ScriptManager_save_pre_handler(item_name):
    def ScriptManager_save_pre_handler(dummy):
        # 注意：save_pre 传入的是 dummy，不是 scene
        scene = bpy.context.scene
        if not scene:
            return

        start_time = time.perf_counter()
        prefs = scene.text_manager_prefs
        item = None

        for temp in prefs.text_manager_collection:
            # 假设属性名为 run_in_save_pre
            if temp.run_in_save_pre and temp.text_pointer and temp.text_pointer.name == ScriptManager_save_pre_handler._ScriptManagerItem_SP_ID:
                item = temp

        if item:
            DebugPrint("Save Pre:", ScriptManager_save_pre_handler._ScriptManagerItem_SP_ID)
            run_text_block(item.text_pointer)

            # 更新 Flag (假设有 save_pre_flag)
            item.save_pre_flag = not item.save_pre_flag
            item.updata_flag = not item.updata_flag

            elapsed = (time.perf_counter() - start_time) * 1000
            # 假设有 save_pre_run_time
            item.save_pre_run_time = elapsed

    ScriptManager_save_pre_handler._ScriptManagerItem_SP_ID = item_name
    return ScriptManager_save_pre_handler
