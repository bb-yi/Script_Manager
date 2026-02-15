import bpy

translations_dict = {
    "zh_CN": {
        # --- 基础 UI 与 设置 ---
        ("*", "New Text"): "新文本",
        ("*", "Use Auto Reload Timer"): "使用自动重载定时器",
        ("*", "VSCode Path"): "VSCode 路径",
        ("*", "Print debug info"): "打印调试信息",
        ("*", "No text selected"): "没有选择文本",
        ("*", "Text not saved"): "文本没有保存",
        ("*", "Auto-reload timer interval"): "自动重载定时器间隔",
        ("*", "No text data block specified"): "未指定文本数据块",
        ("*", "No available text data block"): "没有可用的文本数据块",
        # --- Handler 核心功能描述 ---
        ("*", "Run In Frame Update"): "帧更新时执行",
        ("*", "Run In Depsgraph Update"): "依赖图更新时执行",
        ("*", "Run In Render Pre"): "渲染开始前执行",
        ("*", "Run In Render Post"): "渲染结束后执行",
        ("*", "Run In Load Post"): "文件加载后执行",
        ("*", "Run In Save Pre"): "文件保存前执行",
        # --- 注册/移除 操作反馈 (用于 print 或 report) ---
        ("*", "Add frame update"): "已开启帧更新回调",
        ("*", "Frame update updated"): "帧更新回调已更新",
        ("*", "Remove frame update"): "已移除帧更新回调",
        ("*", "Add depsgraph update"): "已开启依赖图回调",
        ("*", "Depsgraph update updated"): "依赖图回调已更新",
        ("*", "Remove depsgraph update"): "已移除依赖图回调",
        ("*", "Add render_pre update"): "已开启渲染前回调",
        ("*", "Render_pre update updated"): "渲染前回调已更新",
        ("*", "Remove render_pre update"): "已移除渲染前回调",
        ("*", "Add render_post update"): "已开启渲染后回调",
        ("*", "Render_post update updated"): "渲染后回调已更新",
        ("*", "Remove render_post update"): "已移除渲染后回调",
        ("*", "Add load_post update"): "已开启加载后执行",
        ("*", "Remove load_post update"): "已关闭加载后执行",
        ("*", "Script set to run on next file load"): "脚本将在下次加载文件时运行",
        ("*", "Load-run disabled"): "已禁用加载时运行",
        ("*", "Add save_pre update"): "已开启保存前回调",
        ("*", "Remove save_pre update"): "已移除保存前回调",
        ("*", "Handler removed: {str}"): "移除 Handler：{str}",
        ("*", "Handler not found: {str}"): "未找到 Handler：{str}",
        ("*", "Remove plugin handler"): "移除插件 Handler",
        ("*", "Plugin handler"): "插件 Handler",
        ("*", "Remove all handlers"): "移除所有 Handler",
        ("*", "Remove specified handler"): "移除指定的 Handler",
        ("*", "Target Handler"): "目标 Handler",
        ("*", "All handlers"): "所有 Handler",
        ("*", "Restore handlers and triggers when opening file"): "打开文件时恢复 Handler 和 Trigger",
        # --- MsgBus (Trigger) 相关 ---
        ("*", "Use msgbus to monitor property changes and trigger specified scripts"): "使用 msgbus 监控属性变化，触发指定脚本",
        ("*", "Only works for RNA properties; view updates and animation updates have no effect"): "仅适用于 RNA 属性；视图更新和动画更新无效",
        ("*", "Geometry node socket properties are not supported"): "不支持几何节点插口属性",
        ("*", "Item content:   Note   |   Monitored property path    |   Script to execute   |   Is active    |   Last execution time"): "条目内容:   备注   |   监控属性路径    |   执行脚本   |   是否激活    |   上次运行耗时",
        ("*", "No property path"): "没有属性路径",
        ("*", "[Not iterable]"): "[不可遍历]",
        ("*", "Register Trigger monitoring: {str}"): "注册触发器监控：{str}",
        # --- 自动重载定时器 ---
        ("*", "Auto-reload timer started"): "自动重载定时器已启动",
        ("*", "Auto-reload timer restarted"): "自动重载定时器已重新启动",
        ("*", "Auto-reload timer stopped"): "自动重载定时器已停止",
        ("*", "Auto-reload timer not started"): "自动重载定时器未启动",
        # --- 错误与警告 ---
        ("*", "Current text is used by another item"): "当前文本已被其他条目占用",
        ("*", "This item is not unregistered. Please unregister it before deleting."): "该条目尚未注销，请在删除前先注销。",
        ("*", "ScriptManager: Context not ready"): "脚本管理器：上下文未就绪",
        ("*", "ScriptManager: Preferences not ready"): "脚本管理器：偏好设置未就绪",
        # --- Restore Handlers 完整日志 ---
        (
            "*",
            "ScriptManager: Restore complete. Registered: {f} Frame, {d} Deps, {rpre} R-Pre, {rpost} R-Post, {s} Save-Pre. Executed: {l} Load-Scripts. Monitors: {m} Trigger. Timer: {t}.",
        ): "脚本管理器：恢复完成。已注册：{f} 帧更新, {d} 依赖图, {rpre} 渲染前, {rpost} 渲染后, {s} 保存前。已执行：{l} 加载脚本。监控：{m} 触发器。定时器：{t}。",
        ("*", "ScriptManager: No update to restore"): "脚本管理器：没有需要恢复的更新项",
    },
}


def translations(text):
    return bpy.app.translations.pgettext(text)
