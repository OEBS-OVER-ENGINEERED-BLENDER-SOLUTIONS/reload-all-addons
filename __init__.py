

import bpy
import addon_utils
import sys
import traceback
import json
import os
from datetime import datetime


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _get_prefs_file_path():
    return bpy.utils.user_resource('CONFIG', path="oebs_addon_reloader_prefs.json", create=True)

def _save_settings(self=None, context=None):
    prefs = _get_preferences()
    if not prefs:
        return
    data = {
        "hotkey_key": prefs.hotkey_key,
        "hotkey_ctrl": prefs.hotkey_ctrl,
        "hotkey_shift": prefs.hotkey_shift,
        "hotkey_alt": prefs.hotkey_alt,
        "hotkey_spec_key": prefs.hotkey_spec_key,
        "hotkey_spec_ctrl": prefs.hotkey_spec_ctrl,
        "hotkey_spec_shift": prefs.hotkey_spec_shift,
        "hotkey_spec_alt": prefs.hotkey_spec_alt,
        "verbose_console": prefs.verbose_console,
        "active_tab": prefs.active_tab,
        "exclude_collection": [item.name for item in prefs.exclude_collection],
        "select_collection": [{"name": item.name, "selected": item.selected} for item in prefs.select_collection]
    }
    filepath = _get_prefs_file_path()
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Reload All Addons: Failed to save preferences: {e}")

def _load_settings():
    filepath = _get_prefs_file_path()
    if not os.path.exists(filepath):
        return
    prefs = _get_preferences()
    if not prefs:
        return
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for key in ["hotkey_key", "hotkey_ctrl", "hotkey_shift", "hotkey_alt",
                    "hotkey_spec_key", "hotkey_spec_ctrl", "hotkey_spec_shift", "hotkey_spec_alt",
                    "verbose_console", "active_tab"]:
            if key in data:
                setattr(prefs, key, data[key])
        
        if "exclude_collection" in data:
            prefs.exclude_collection.clear()
            for name in data["exclude_collection"]:
                item = prefs.exclude_collection.add()
                item.name = name
                
        if "select_collection" in data:
            prefs.select_collection.clear()
            for item_data in data["select_collection"]:
                item = prefs.select_collection.add()
                item.name = item_data.get("name", "")
                item.selected = item_data.get("selected", True)
                
        update_keymap()
    except Exception as e:
        print(f"Reload All Addons: Failed to load preferences: {e}")

def _delayed_load_settings():
    _load_settings()
    return None

def _get_this_addon():
    return __package__ if __package__ else __name__


def _get_preferences(context=None):
    context = context or bpy.context
    addons = context.preferences.addons
    addon = addons.get(_get_this_addon()) or addons.get(__name__)
    return addon.preferences if addon else None


def _belongs_to_module(owner_name, module_name):
    return owner_name == module_name or owner_name.startswith(module_name + '.')


def _format_names(names, limit=8):
    names = [str(name) for name in names]
    if len(names) <= limit:
        return ', '.join(names) if names else 'none'
    return ', '.join(names[:limit]) + f" ... (+{len(names) - limit} more)"


def _get_loaded_module(module_name):
    return sys.modules.get(module_name)


def _call_optional_hook(module_name, hook_name, verbose=True, module=None):
    """Call an addon cooperation hook if the addon exposes it."""
    mod = module or _get_loaded_module(module_name)
    hook = getattr(mod, hook_name, None) if mod else None
    if not callable(hook):
        return False, ""

    try:
        hook()
        if verbose:
            print(f"  [HOOK]    {hook_name} OK")
        return True, ""
    except Exception:
        err = traceback.format_exc()
        if verbose:
            print(f"  [HOOK]    {hook_name} FAILED")
            print(err.rstrip())
        return False, err


def _find_bpy_classes(module_name):
    """Return currently registered bpy.types classes owned by the addon."""
    type_names = [name for name in dir(bpy.types) if not name.startswith('_')]
    classes_found = []
    for type_name in type_names:
        try:
            cls = getattr(bpy.types, type_name)
            cls_module = getattr(cls, '__module__', '') or ''
            if _belongs_to_module(cls_module, module_name):
                classes_found.append(cls)
        except Exception:
            pass
    return classes_found


def _operator_idnames(classes_found):
    return {
        getattr(cls, "bl_idname", "")
        for cls in classes_found
        if getattr(cls, "bl_idname", "")
    }


def _find_keymap_items(module_name, classes_found=None):
    """Find keymap items that can be safely attributed to addon operators."""
    classes_found = classes_found or _find_bpy_classes(module_name)
    idnames = _operator_idnames(classes_found)
    if not idnames:
        return []

    matches = []
    wm = getattr(bpy.context, "window_manager", None)
    keyconfigs = getattr(wm, "keyconfigs", None) if wm else None
    for config_name in ("addon", "user"):
        kc = getattr(keyconfigs, config_name, None) if keyconfigs else None
        if not kc:
            continue
        try:
            keymaps = list(kc.keymaps)
        except Exception:
            continue
        for km in keymaps:
            for kmi in list(getattr(km, "keymap_items", [])):
                if getattr(kmi, "idname", "") in idnames:
                    matches.append((km, kmi, config_name))
    return matches


def _iter_handler_lists():
    handlers = getattr(bpy.app, "handlers", None)
    if handlers is None:
        return
    for name in dir(handlers):
        if name.startswith("_"):
            continue
        try:
            value = getattr(handlers, name)
        except Exception:
            continue
        try:
            callbacks = list(value)
        except TypeError:
            continue
        except Exception:
            continue
        yield name, value, callbacks


def _find_handlers(module_name):
    """Find app handlers whose callback function is clearly owned by the addon."""
    matches = []
    for list_name, handler_list, callbacks in _iter_handler_lists() or ():
        for callback in callbacks:
            owner = getattr(callback, "__module__", "") or ""
            if _belongs_to_module(owner, module_name):
                callback_name = getattr(callback, "__name__", repr(callback))
                matches.append((list_name, handler_list, callback, callback_name))
    return matches


def _inspect_leftovers(module_name):
    classes_found = _find_bpy_classes(module_name)
    return {
        "classes": classes_found,
        "keymaps": _find_keymap_items(module_name, classes_found),
        "handlers": _find_handlers(module_name),
        "modules": [
            key for key in sys.modules
            if key == module_name or key.startswith(module_name + '.')
        ],
    }


def _leftover_count(leftovers, key):
    return len(leftovers.get(key, []))


def _print_leftover_report(module_name, leftovers, prefix="  [INSPECT]"):
    class_names = [getattr(cls, "__name__", str(cls)) for cls in leftovers["classes"]]
    keymap_names = [
        f"{config}:{getattr(km, 'name', '<keymap>')}:{getattr(kmi, 'idname', '<item>')}"
        for km, kmi, config in leftovers["keymaps"]
    ]
    handler_names = [
        f"{list_name}:{callback_name}"
        for list_name, _handler_list, _callback, callback_name in leftovers["handlers"]
    ]
    module_names = leftovers["modules"]

    print(f"{prefix} {module_name}")
    print(f"{prefix}   classes : {len(class_names)} [{_format_names(class_names)}]")
    print(f"{prefix}   keymaps : {len(keymap_names)} [{_format_names(keymap_names)}]")
    print(f"{prefix}   handlers: {len(handler_names)} [{_format_names(handler_names)}]")
    print(f"{prefix}   modules : {len(module_names)} [{_format_names(module_names)}]")


def _cleanup_leftovers(module_name, leftovers, verbose=True):
    """Conservatively clean only leftovers that can be attributed to the addon."""
    cleaned = {"classes": [], "keymaps": [], "handlers": []}
    errors = []

    for km, kmi, config_name in list(leftovers.get("keymaps", [])):
        try:
            km.keymap_items.remove(kmi)
            cleaned["keymaps"].append(f"{config_name}:{getattr(kmi, 'idname', '<item>')}")
        except Exception as exc:
            errors.append(f"keymap {getattr(kmi, 'idname', '<item>')}: {exc}")

    for list_name, handler_list, callback, callback_name in list(leftovers.get("handlers", [])):
        try:
            handler_list.remove(callback)
            cleaned["handlers"].append(f"{list_name}:{callback_name}")
        except Exception as exc:
            errors.append(f"handler {list_name}:{callback_name}: {exc}")

    for cls in reversed(leftovers.get("classes", [])):
        class_name = getattr(cls, "__name__", repr(cls))
        try:
            bpy.utils.unregister_class(cls)
            cleaned["classes"].append(class_name)
        except Exception as exc:
            errors.append(f"class {class_name}: {exc}")

    if verbose:
        print(f"  [CLEAN]   classes : {len(cleaned['classes'])} [{_format_names(cleaned['classes'])}]")
        print(f"  [CLEAN]   keymaps : {len(cleaned['keymaps'])} [{_format_names(cleaned['keymaps'])}]")
        print(f"  [CLEAN]   handlers: {len(cleaned['handlers'])} [{_format_names(cleaned['handlers'])}]")
        if errors:
            print(f"  [CLEAN]   errors  : {len(errors)} [{_format_names(errors, limit=4)}]")

    return cleaned, errors


def _purge_sys_modules(module_name):
    """
    Remove the addon and every sub-module from sys.modules so Python re-reads
    files from disk on the next import. Also clears any cached __spec__ refs.
    """
    keys_to_delete = [
        key for key in sys.modules
        if key == module_name or key.startswith(module_name + '.')
    ]
    for key in keys_to_delete:
        del sys.modules[key]
    return keys_to_delete


def _do_reload(module_name, verbose=True):
    """
    Staged reload of a single addon:
      1. Optional pre_reload_cleanup() hook
      2. Blender-level addon_disable
      3. Inspect leftover classes/keymaps/handlers/modules
      4. Targeted fallback cleanup for attributable leftovers
      5. Purge sys.modules late so the next enable reads from disk
      6. Optional pre_enable_cleanup() hook
      7. Blender-level addon_enable

    Returns a result dictionary for detailed batch reporting.
    """
    steps_log = []
    errors = []
    fallback_used = False

    if verbose:
        print(f"  [START]   {module_name}")

    hook_ok, hook_err = _call_optional_hook(module_name, "pre_reload_cleanup", verbose)
    if hook_ok:
        steps_log.append("pre_reload_cleanup OK")
    elif hook_err:
        errors.append(("pre_reload_cleanup", hook_err))

    try:
        bpy.ops.preferences.addon_disable(module=module_name)
        steps_log.append("addon_disable OK")
        if verbose:
            print("  [DISABLE] addon_disable OK")
    except Exception as e:
        err = traceback.format_exc()
        errors.append(("addon_disable", err))
        steps_log.append(f"addon_disable WARN: {e}")
        if verbose:
            print(f"  [DISABLE] addon_disable WARN: {e}")

    hook_ok, hook_err = _call_optional_hook(module_name, "post_disable_cleanup", verbose)
    if hook_ok:
        steps_log.append("post_disable_cleanup OK")
    elif hook_err:
        errors.append(("post_disable_cleanup", hook_err))

    leftovers = _inspect_leftovers(module_name)
    if verbose:
        _print_leftover_report(module_name, leftovers)

    if any(_leftover_count(leftovers, key) for key in ("classes", "keymaps", "handlers")):
        fallback_used = True
        _cleaned, cleanup_errors = _cleanup_leftovers(module_name, leftovers, verbose)
        errors.extend(("fallback_cleanup", err) for err in cleanup_errors)
        steps_log.append("fallback cleanup")

    disabled_module = _get_loaded_module(module_name)
    deleted_keys = _purge_sys_modules(module_name)
    steps_log.append(f"purged {len(deleted_keys)} module(s)")
    if verbose:
        print(f"  [PURGE]   Removed {len(deleted_keys)} sys.modules entry(s)")

    hook_ok, hook_err = _call_optional_hook(module_name, "pre_enable_cleanup", verbose, module=disabled_module)
    if hook_ok:
        steps_log.append("pre_enable_cleanup OK")
    elif hook_err:
        errors.append(("pre_enable_cleanup", hook_err))

    try:
        bpy.ops.preferences.addon_enable(module=module_name)
        status = "reloaded with fallback cleanup" if fallback_used else "clean reload"
        if verbose:
            print(f"  [SUCCESS] {module_name}: {status} ({' | '.join(steps_log)})")
        return {
            "ok": True,
            "module": module_name,
            "status": status,
            "steps": steps_log,
            "errors": errors,
            "fallback_used": fallback_used,
            "leftovers": leftovers,
        }
    except Exception as e:
        err = traceback.format_exc()
        errors.append(("addon_enable", err))
        if verbose:
            print(f"  [FAILED]  {module_name}: {err}")
            print(f"            Steps: {' | '.join(steps_log)}")
        return {
            "ok": False,
            "module": module_name,
            "status": "failed",
            "steps": steps_log,
            "errors": errors,
            "fallback_used": fallback_used,
            "leftovers": leftovers,
        }


# ---------------------------------------------------------------------------
# Property Groups
# ---------------------------------------------------------------------------

class RELOAD_AddonExcludeItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Addon Module Name",
        description="The module name of the addon to exclude"
    )


class RELOAD_AddonSelectItem(bpy.types.PropertyGroup):
    """One entry in the 'Reload Specific Addons' list."""
    name: bpy.props.StringProperty(
        name="Addon Module Name",
        description="Module name of this addon"
    )
    selected: bpy.props.BoolProperty(
        name="Selected",
        description="Include this addon in the batch reload",
        default=True
    )


# ---------------------------------------------------------------------------
# UI Lists
# ---------------------------------------------------------------------------

class RELOAD_UL_excluded_addons(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon='PLUGIN')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='PLUGIN')


class RELOAD_UL_select_addons(bpy.types.UIList):
    """UIList for the specific-reload list, with a checkbox, per-row reload, and per-row remove button."""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "selected", text="")
            row.label(text=item.name, icon='PLUGIN')
            
            # Per-item instant reload button
            op = row.operator("addons.reload_one", text="", icon='FILE_REFRESH', emboss=False)
            op.module_name = item.name

            # Per-item diagnostics button
            op_diag = row.operator("addons.reload_diagnostics", text="", icon='INFO', emboss=False)
            op_diag.module_name = item.name
            
            # Per-item remove button
            op_rem = row.operator("reload.select_remove_by_name", text="", icon='X', emboss=False)
            op_rem.module_name = item.name
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='PLUGIN')


# ---------------------------------------------------------------------------
# Search callbacks
# ---------------------------------------------------------------------------

def addon_search_callback(self, context, edit_text):
    """For the exclude list search."""
    this_addon = _get_this_addon()
    items = []
    for mod in addon_utils.modules():
        name = mod.__name__
        if addon_utils.check(name)[1] and name != this_addon:
            if edit_text.lower() in name.lower():
                items.append(name)
    return items


def addon_select_search_callback(self, context, edit_text):
    """For the specific-reload list search. Excludes already-added entries."""
    this_addon = _get_this_addon()
    prefs = _get_preferences(context)
    if prefs is None:
        return []
    already_added = {item.name for item in prefs.select_collection}
    items = []
    for mod in addon_utils.modules():
        name = mod.__name__
        if addon_utils.check(name)[1] and name != this_addon and name not in already_added:
            if edit_text.lower() in name.lower():
                items.append(name)
    return items


# ---------------------------------------------------------------------------
# Exclude list operators
# ---------------------------------------------------------------------------

class RELOAD_OT_exclude_add(bpy.types.Operator):
    bl_idname = "reload.exclude_add"
    bl_label = "Add to Exclude List"
    bl_description = "Add the selected addon to the exclusion list"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs = _get_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "Reload All Addons preferences are not available yet")
            return {'CANCELLED'}
        name = prefs.addon_to_exclude_search

        if not name:
            self.report({'WARNING'}, "Please select an addon first")
            return {'CANCELLED'}

        if any(item.name == name for item in prefs.exclude_collection):
            self.report({'WARNING'}, f"'{name}' is already excluded")
            return {'CANCELLED'}

        item = prefs.exclude_collection.add()
        item.name = name
        prefs.addon_to_exclude_search = ""
        _save_settings()
        return {'FINISHED'}


class RELOAD_OT_exclude_remove(bpy.types.Operator):
    bl_idname = "reload.exclude_remove"
    bl_label = "Remove from Exclude List"
    bl_description = "Remove the selected addon from the exclusion list"
    bl_options = {'INTERNAL'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        prefs = _get_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "Reload All Addons preferences are not available yet")
            return {'CANCELLED'}
        prefs.exclude_collection.remove(self.index)
        prefs.exclude_index = min(max(0, self.index - 1), len(prefs.exclude_collection) - 1)
        _save_settings()
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Specific-reload list operators
# ---------------------------------------------------------------------------

class RELOAD_OT_select_add(bpy.types.Operator):
    bl_idname = "reload.select_add"
    bl_label = "Add Addon to Reload List"
    bl_description = "Add the searched addon to the specific-reload list"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs = _get_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "Reload All Addons preferences are not available yet")
            return {'CANCELLED'}
        name = prefs.addon_to_select_search

        if not name:
            self.report({'WARNING'}, "Please select an addon first")
            return {'CANCELLED'}

        if any(item.name == name for item in prefs.select_collection):
            self.report({'WARNING'}, f"'{name}' is already in the list")
            return {'CANCELLED'}

        item = prefs.select_collection.add()
        item.name = name
        item.selected = True
        prefs.addon_to_select_search = ""
        _save_settings()
        return {'FINISHED'}


class RELOAD_OT_select_remove(bpy.types.Operator):
    bl_idname = "reload.select_remove"
    bl_label = "Remove from Reload List"
    bl_description = "Remove the selected addon from the specific-reload list"
    bl_options = {'INTERNAL'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        prefs = _get_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "Reload All Addons preferences are not available yet")
            return {'CANCELLED'}
        prefs.select_collection.remove(self.index)
        prefs.select_index = min(max(0, self.index - 1), len(prefs.select_collection) - 1)
        _save_settings()
        return {'FINISHED'}


class RELOAD_OT_select_remove_by_name(bpy.types.Operator):
    bl_idname = "reload.select_remove_by_name"
    bl_label = "Remove Addon"
    bl_description = "Remove this addon from the list"
    bl_options = {'INTERNAL'}

    module_name: bpy.props.StringProperty()

    def execute(self, context):
        prefs = _get_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "Reload All Addons preferences are not available yet")
            return {'CANCELLED'}
        for idx, item in enumerate(prefs.select_collection):
            if item.name == self.module_name:
                prefs.select_collection.remove(idx)
                prefs.select_index = min(max(0, idx - 1), len(prefs.select_collection) - 1)
                break
        _save_settings()
        return {'FINISHED'}



class RELOAD_OT_select_remove_checked(bpy.types.Operator):
    """Remove checked addons from the list"""
    bl_idname = "reload.select_remove_checked"
    bl_label = "Remove Checked"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        prefs = _get_preferences(context)
        if not prefs: return {'CANCELLED'}
        # Iterate backwards
        for i in range(len(prefs.select_collection)-1, -1, -1):
            if prefs.select_collection[i].selected:
                prefs.select_collection.remove(i)
        
        # Adjust index safely
        if prefs.select_index >= len(prefs.select_collection):
            prefs.select_index = max(0, len(prefs.select_collection) - 1)
            
        _save_settings()
        if context.area:
            context.area.tag_redraw()
        return {'FINISHED'}

class RELOAD_OT_select_clear(bpy.types.Operator):
    bl_idname = "reload.select_clear"
    bl_label = "Clear List"
    bl_description = "Remove all addons from this list"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs = _get_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "Reload All Addons preferences are not available yet")
            return {'CANCELLED'}
        prefs.select_collection.clear()
        prefs.select_index = 0
        _save_settings()
        return {'FINISHED'}


class RELOAD_OT_select_all(bpy.types.Operator):
    bl_idname = "reload.select_all"
    bl_label = "Select All"
    bl_description = "Check all addons in the list"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs = _get_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "Reload All Addons preferences are not available yet")
            return {'CANCELLED'}
        for item in prefs.select_collection:
            item.selected = True
        _save_settings()
        return {'FINISHED'}


class RELOAD_OT_select_none(bpy.types.Operator):
    bl_idname = "reload.select_none"
    bl_label = "Select None"
    bl_description = "Uncheck all addons in the list"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs = _get_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "Reload All Addons preferences are not available yet")
            return {'CANCELLED'}
        for item in prefs.select_collection:
            item.selected = False
        _save_settings()
        return {'FINISHED'}


class RELOAD_OT_select_add_enabled(bpy.types.Operator):
    bl_idname = "reload.select_add_enabled"
    bl_label = "Populate with All Enabled Addons"
    bl_description = "Add every currently-enabled addon (except this one) to the list"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs = _get_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "Reload All Addons preferences are not available yet")
            return {'CANCELLED'}
        this_addon = _get_this_addon()
        already = {item.name for item in prefs.select_collection}
        added = 0
        for mod in addon_utils.modules():
            name = mod.__name__
            if addon_utils.check(name)[1] and name != this_addon and name not in already:
                item = prefs.select_collection.add()
                item.name = name
                item.selected = True
                added += 1
        self.report({'INFO'}, f"Added {added} addon(s) to the list")
        _save_settings()
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Core Reload Operators
# ---------------------------------------------------------------------------

class ADDONS_OT_reload_all(bpy.types.Operator):
    """Reload all enabled addons except this one"""
    bl_idname = "addons.reload_all"
    bl_label = "Reload All Addons"
    bl_options = {'REGISTER'}

    verbose: bpy.props.BoolProperty(
        name="Verbose Output",
        description="Print detailed information to console",
        default=True
    )

    def execute(self, context):
        this_addon = _get_this_addon()

        timestamp = datetime.now().strftime("%H:%M:%S")
        print("\n" + "=" * 70)
        print(f"RELOAD ALL ADDONS - {timestamp}")
        print("=" * 70)

        prefs = _get_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "Reload All Addons preferences are not available yet")
            return {'CANCELLED'}
        self.verbose = prefs.verbose_console
        excluded_names = {item.name for item in prefs.exclude_collection}

        enabled_addons = []
        for mod in addon_utils.modules():
            module_name = mod.__name__
            is_enabled = addon_utils.check(module_name)[1]
            if is_enabled and module_name != this_addon:
                if module_name not in excluded_names:
                    enabled_addons.append(module_name)
                elif self.verbose:
                    print(f"Skipping excluded addon: {module_name}")

        if not enabled_addons:
            print("WARNING: No other addons are currently enabled")
            print("=" * 70 + "\n")
            self.report({'INFO'}, "No addons to reload")
            return {'CANCELLED'}

        print(f"Found {len(enabled_addons)} enabled addon(s) to reload")
        if self.verbose:
            print("\nAddons to reload:")
            for i, name in enumerate(enabled_addons, 1):
                print(f"  {i}. {name}")
        print()

        results = []

        for module_name in enabled_addons:
            results.append(_do_reload(module_name, self.verbose))

        reloaded_count = sum(1 for result in results if result["ok"])
        failed_addons = [result for result in results if not result["ok"]]
        fallback_count = sum(1 for result in results if result["fallback_used"])

        print("\n" + "-" * 70)
        print("SUMMARY:")
        print(f"  Successfully reloaded: {reloaded_count}")
        print(f"  Used fallback cleanup: {fallback_count}")
        print(f"  Failed to reload:      {len(failed_addons)}")

        print("\nRESULTS:")
        for result in results:
            print(f"  {result['module']}: {result['status']}")

        if failed_addons:
            print("\nFAILED ADDONS:")
            for i, result in enumerate(failed_addons, 1):
                print(f"  {i}. {result['module']}")
                if result["errors"]:
                    stage, error = result["errors"][-1]
                    print(f"     Stage: {stage}")
                    print(f"     Error: {error.rstrip()}")

        print("=" * 70 + "\n")

        message = f"Reloaded {reloaded_count}/{len(enabled_addons)} addon(s)"
        if failed_addons:
            message += f" ({len(failed_addons)} failed – see console)"
            self.report({'WARNING'}, message)
        else:
            self.report({'INFO'}, message)

        return {'FINISHED'}


class ADDONS_OT_reload_one(bpy.types.Operator):
    """Reload a single addon by module name"""
    bl_idname = "addons.reload_one"
    bl_label = "Reload Addon"
    bl_description = "Reload this specific addon"
    bl_options = {'REGISTER', 'INTERNAL'}

    module_name: bpy.props.StringProperty(
        name="Module Name",
        description="Module name of the addon to reload"
    )

    def execute(self, context):
        if not self.module_name:
            self.report({'ERROR'}, "No module name provided")
            return {'CANCELLED'}

        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] Reloading: {self.module_name}")

        result = _do_reload(self.module_name, verbose=True)
        if result["ok"]:
            self.report({'INFO'}, f"{self.module_name}: {result['status']}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"Failed to reload '{self.module_name}'")
            return {'CANCELLED'}


class ADDONS_OT_reload_checked(bpy.types.Operator):
    """Reload all checked addons in the specific-reload list"""
    bl_idname = "addons.reload_checked"
    bl_label = "Reload Checked Addons"
    bl_description = "Reload all addons that are checked in the list below"
    bl_options = {'REGISTER'}

    def execute(self, context):
        prefs = _get_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "Reload All Addons preferences are not available yet")
            return {'CANCELLED'}
        targets = [item.name for item in prefs.select_collection if item.selected]

        if not targets:
            self.report({'INFO'}, "Reload list is empty. Opening selection popup.")
            # Call the popup operator to let the user add some addons
            bpy.ops.addons.reload_popup('INVOKE_DEFAULT')
            return {'FINISHED'}

        timestamp = datetime.now().strftime("%H:%M:%S")
        print("\n" + "=" * 70)
        print(f"RELOAD SPECIFIC ADDONS - {timestamp}")
        print("=" * 70)
        print(f"Targets: {targets}\n")

        results = []

        for module_name in targets:
            results.append(_do_reload(module_name, verbose=prefs.verbose_console))

        reloaded_count = sum(1 for result in results if result["ok"])
        failed_addons = [result for result in results if not result["ok"]]
        fallback_count = sum(1 for result in results if result["fallback_used"])

        print("\n" + "-" * 70)
        print(f"SUMMARY: {reloaded_count}/{len(targets)} reloaded")
        print(f"FALLBACK CLEANUP: {fallback_count}")
        print("RESULTS:")
        for result in results:
            print(f"  {result['module']}: {result['status']}")
        if failed_addons:
            print("FAILED:")
            for result in failed_addons:
                print(f"  {result['module']}: {result['status']}")
                if result["errors"]:
                    stage, error = result["errors"][-1]
                    print(f"    {stage}: {error.rstrip()}")
        print("=" * 70 + "\n")

        message = f"Reloaded {reloaded_count}/{len(targets)} addon(s)"
        if failed_addons:
            message += f" ({len(failed_addons)} failed – see console)"
            self.report({'WARNING'}, message)
        else:
            self.report({'INFO'}, message)

        return {'FINISHED'}


class ADDONS_OT_reload_diagnostics(bpy.types.Operator):
    """Inspect reload leftovers for one addon without disabling or reloading it"""
    bl_idname = "addons.reload_diagnostics"
    bl_label = "Inspect Addon Reload State"
    bl_description = "Print registered classes, keymaps, handlers, and modules attributed to this addon"
    bl_options = {'REGISTER', 'INTERNAL'}

    module_name: bpy.props.StringProperty(
        name="Module Name",
        description="Module name of the addon to inspect"
    )

    def execute(self, context):
        if not self.module_name:
            self.report({'ERROR'}, "No module name provided")
            return {'CANCELLED'}

        timestamp = datetime.now().strftime("%H:%M:%S")
        print("\n" + "=" * 70)
        print(f"RELOAD DIAGNOSTICS - {timestamp}")
        print("=" * 70)
        leftovers = _inspect_leftovers(self.module_name)
        _print_leftover_report(self.module_name, leftovers, prefix="  [DIAG]")
        print("=" * 70 + "\n")
        self.report({'INFO'}, f"Diagnostics printed for {self.module_name}")
        return {'FINISHED'}


class ADDONS_OT_reload_popup(bpy.types.Operator):
    """Open a popup to reload specific addons"""
    bl_idname = "addons.reload_popup"
    bl_label = "Reload Specific Addons"
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        layout = self.layout
        prefs = _get_preferences(context)
        if prefs is None:
            layout.label(text="Reload All Addons preferences are not available yet", icon='ERROR')
            return

        layout.label(text="Select addons to reload:", icon='PLUGIN')
        
        # Row 1: selection toggles
        row = layout.row(align=True)
        row.operator("reload.select_all", text="Select All", icon='CHECKBOX_HLT')
        row.operator("reload.select_none", text="Select None", icon='CHECKBOX_DEHLT')
        
        # Row 2: list population/clearing
        row2 = layout.row(align=True)
        row2.operator("reload.select_add_enabled", text="Sync Enabled", icon='FILE_REFRESH')
        row2.operator("reload.select_clear", text="Clear List", icon='TRASH')

        layout.separator()

        # Display the checkboxes using the UI list with sidebar remove button
        row_list = layout.row()
        row_list.template_list(
            "RELOAD_UL_select_addons", "",
            prefs, "select_collection",
            prefs, "select_index",
            rows=8
        )
        col = row_list.column(align=True)
        col.operator("reload.select_remove", icon='REMOVE', text="").index = prefs.select_index
        
        # Add search bar inside popup to quickly add new ones
        row_search = layout.row(align=True)
        row_search.prop(prefs, "addon_to_select_search", text="", icon='VIEWZOOM')
        row_search.operator("reload.select_add", text="", icon='ADD')

    def execute(self, context):
        # Delegate to the batch reload operator
        bpy.ops.addons.reload_checked()
        return {'FINISHED'}

    def invoke(self, context, event):
        prefs = _get_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "Reload All Addons preferences are not available yet")
            return {'CANCELLED'}
        # Auto-populate if empty
        if not prefs.select_collection:
            bpy.ops.reload.select_add_enabled()
        # Open dialog
        return context.window_manager.invoke_props_dialog(self, width=380)



class ADDONS_OT_restore_hotkeys(bpy.types.Operator):
    """Restore hotkeys to default"""
    bl_idname = "addons.restore_hotkeys"
    bl_label = "Restore Default Hotkeys"
    bl_options = {'REGISTER'}

    target: bpy.props.EnumProperty(
        name="Target Key",
        items=[
            ('ALL', "Reload All", ""),
            ('SPECIFIC', "Reload Specific", ""),
        ]
    )

    def execute(self, context):
        prefs = _get_preferences(context)
        if prefs is None: return {'CANCELLED'}
        if self.target == 'ALL':
            prefs.hotkey_ctrl = True
            prefs.hotkey_shift = True
            prefs.hotkey_alt = True
            prefs.hotkey_key = 'R'
        else:
            prefs.hotkey_spec_ctrl = True
            prefs.hotkey_spec_shift = True
            prefs.hotkey_spec_alt = False
            prefs.hotkey_spec_key = 'R'
        update_keymap()
        self.report({'INFO'}, "Hotkeys restored to defaults")
        return {'FINISHED'}

class ADDONS_OT_capture_key(bpy.types.Operator):
    """Click to capture the next keyboard key press"""
    bl_idname = "addons.capture_key"
    bl_label = "Click to Bind Key"
    bl_description = "Click this button, then press the key combo you want to bind (e.g. Ctrl+Shift+A). Press Esc to cancel"
    bl_options = {'REGISTER'}

    target: bpy.props.EnumProperty(
        name="Target Key",
        items=[
            ('ALL', "Reload All", ""),
            ('SPECIFIC', "Reload Specific", ""),
        ]
    )

    def invoke(self, context, event):
        prefs = _get_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "Reload All Addons preferences are not available yet")
            return {'CANCELLED'}
        prefs.capturing_target = self.target
        context.window_manager.modal_handler_add(self)
        if context.area:
            context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        prefs = _get_preferences(context)
        if prefs is None:
            return {'CANCELLED'}

        # Cancel keys
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            prefs.capturing_target = ""
            if context.area:
                context.area.tag_redraw()
            self.report({'INFO'}, "Key binding cancelled")
            return {'CANCELLED'}

        # Capture key presses (ignore modifiers alone)
        modifier_types = {
            'LEFT_CTRL', 'RIGHT_CTRL', 'LEFT_SHIFT', 'RIGHT_SHIFT',
            'LEFT_ALT', 'RIGHT_ALT', 'OSKEY', 'NONE'
        }

        if event.value == 'PRESS' and event.type not in modifier_types:
            key_code = event.type
            ctrl = event.ctrl
            shift = event.shift
            alt = event.alt

            if self.target == 'ALL':
                prefs.hotkey_key = key_code
                prefs.hotkey_ctrl = ctrl
                prefs.hotkey_shift = shift
                prefs.hotkey_alt = alt
            else:
                prefs.hotkey_spec_key = key_code
                prefs.hotkey_spec_ctrl = ctrl
                prefs.hotkey_spec_shift = shift
                prefs.hotkey_spec_alt = alt

            prefs.capturing_target = ""
            if context.area:
                context.area.tag_redraw()

            # Force update keymap
            update_keymap()

            # Format status message
            mods = []
            if ctrl: mods.append("Ctrl")
            if shift: mods.append("Shift")
            if alt: mods.append("Alt")
            mods.append(key_code)
            self.report({'INFO'}, f"Bound to: {'+'.join(mods)}")
            return {'FINISHED'}

        return {'RUNNING_MODAL'}


# ---------------------------------------------------------------------------
# Preferences Panel
# ---------------------------------------------------------------------------

class ReloadAddonsPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    # --- Hotkey settings ---
    hotkey_key: bpy.props.StringProperty(
        name="Key",
        description="Key to use for the hotkey (e.g. F3, R, A, SPACE, NUMPAD_1)",
        default='R',
        update=lambda self, context: update_keymap()
    )
    hotkey_ctrl: bpy.props.BoolProperty(
        name="Ctrl", default=True, update=lambda self, context: update_keymap()
    )
    hotkey_shift: bpy.props.BoolProperty(
        name="Shift", default=True, update=lambda self, context: update_keymap()
    )
    hotkey_alt: bpy.props.BoolProperty(
        name="Alt", default=True, update=lambda self, context: update_keymap()
    )

    # --- Hotkey settings (Specific Reload) ---
    hotkey_spec_key: bpy.props.StringProperty(
        name="Key",
        description="Key to use for the specific reload hotkey (e.g. F4, R, A, SPACE, NUMPAD_1)",
        default='R',
        update=lambda self, context: update_keymap()
    )
    hotkey_spec_ctrl: bpy.props.BoolProperty(
        name="Ctrl", default=True, update=lambda self, context: update_keymap()
    )
    hotkey_spec_shift: bpy.props.BoolProperty(
        name="Shift", default=True, update=lambda self, context: update_keymap()
    )
    hotkey_spec_alt: bpy.props.BoolProperty(
        name="Alt", default=False, update=lambda self, context: update_keymap()
    )

    # --- Capture status tracker ---
    capturing_target: bpy.props.StringProperty(default="")

    # --- Exclude list ---
    exclude_collection: bpy.props.CollectionProperty(type=RELOAD_AddonExcludeItem)
    exclude_index: bpy.props.IntProperty(name="Exclude Index", default=0)
    addon_to_exclude_search: bpy.props.StringProperty(
        name="Addon to Exclude",
        description="Search for an addon to exclude from Reload All",
        search=addon_search_callback
    )

    # --- Specific-reload list ---
    select_collection: bpy.props.CollectionProperty(type=RELOAD_AddonSelectItem)
    select_index: bpy.props.IntProperty(name="Select Index", default=0)
    addon_to_select_search: bpy.props.StringProperty(
        name="Addon to Add",
        description="Search for an addon to add to the specific-reload list",
        search=addon_select_search_callback
    )

    verbose_console: bpy.props.BoolProperty(
        name="Verbose Console Output",
        description="Print detailed information to console during reload",
        default=True
    )

    # --- Panel tab toggle ---
    active_tab: bpy.props.EnumProperty(
        name="Active Tab",
        items=[
            ('ALL', "Reload All", "Reload every enabled addon at once"),
            ('SPECIFIC', "Reload Specific", "Pick individual addons to reload"),
        ],
        default='ALL'
    )

    def draw(self, context):
        layout = self.layout

        # ── Tab bar ──────────────────────────────────────────────────────────
        row = layout.row(align=True)
        row.prop_tabs_enum(self, "active_tab")
        layout.separator(factor=0.5)

        # ── RELOAD ALL tab ───────────────────────────────────────────────────
        if self.active_tab == 'ALL':
            box = layout.box()
            col = box.column(align=True)
            col.scale_y = 1.5
            op = col.operator("addons.reload_all", text="Reload All Addons", icon='FILE_REFRESH')
            op.verbose = self.verbose_console

            layout.separator()

            # Hotkey
            box = layout.box()
            box.label(text="Keyboard Shortcut:", icon='KEYINGSET')
            
            if self.capturing_target == 'ALL':
                row = box.row()
                row.scale_y = 1.2
                row.label(text="Press any key combo... (Esc to cancel)", icon='ADD')
            else:
                row = box.row(align=True)
                row.prop(self, "hotkey_ctrl", toggle=True)
                row.prop(self, "hotkey_shift", toggle=True)
                row.prop(self, "hotkey_alt", toggle=True)
                row.prop(self, "hotkey_key", text="")
                op = row.operator("addons.capture_key", text="Record", icon='REC')
                op.target = 'ALL'
                
                hotkey_parts = []
                if self.hotkey_ctrl:   hotkey_parts.append("Ctrl")
                if self.hotkey_shift:  hotkey_parts.append("Shift")
                if self.hotkey_alt:    hotkey_parts.append("Alt")
                hotkey_parts.append(self.hotkey_key.upper().strip())
                current_hotkey = "+".join(hotkey_parts)
                box.label(text=f"Current: {current_hotkey}", icon='HAND')

            layout.separator()

            # Advanced / exclusions
            box = layout.box()
            box.label(text="Advanced Settings:", icon='SETTINGS')
            box.prop(self, "verbose_console")
            box.separator()
            box.label(text="Addons To Exclude:", icon='FILTER')
            row = box.row(align=True)
            row.prop(self, "addon_to_exclude_search", text="")
            row.operator("reload.exclude_add", text="", icon='ADD')
            row = box.row()
            row.template_list(
                "RELOAD_UL_excluded_addons", "",
                self, "exclude_collection",
                self, "exclude_index"
            )
            col = row.column(align=True)
            col.operator("reload.exclude_remove", icon='REMOVE', text="").index = self.exclude_index

            layout.separator()

            # Info
            box = layout.box()
            box.label(text="Quick Access:", icon='VIEWZOOM')
            col = box.column(align=True)
            col.label(text=f"• Hotkey: {current_hotkey}")
            col.label(text="• File → Reload All Addons")

        # ── RELOAD SPECIFIC tab ──────────────────────────────────────────────
        elif self.active_tab == 'SPECIFIC':
            # Batch reload button (prominent)
            box = layout.box()
            col = box.column(align=True)
            col.scale_y = 1.5
            checked_count = sum(1 for i in self.select_collection if i.selected)
            label = f"Reload Checked Addons  ({checked_count} selected)" if self.select_collection else "Reload Checked Addons"
            col.operator("addons.reload_checked", text=label, icon='FILE_REFRESH')

            layout.separator()

            # Hotkey settings for Specific Reload
            box_hk = layout.box()
            box_hk.label(text="Keyboard Shortcut (Reload Specific):", icon='KEYINGSET')
            
            if self.capturing_target == 'SPECIFIC':
                row = box_hk.row()
                row.scale_y = 1.2
                row.label(text="Press any key combo... (Esc to cancel)", icon='ADD')
            else:
                row = box_hk.row(align=True)
                row.prop(self, "hotkey_spec_ctrl", toggle=True)
                row.prop(self, "hotkey_spec_shift", toggle=True)
                row.prop(self, "hotkey_spec_alt", toggle=True)
                row.prop(self, "hotkey_spec_key", text="")
                op = row.operator("addons.capture_key", text="Record", icon='REC')
                op.target = 'SPECIFIC'
                
                hotkey_parts = []
                if self.hotkey_spec_ctrl:   hotkey_parts.append("Ctrl")
                if self.hotkey_spec_shift:  hotkey_parts.append("Shift")
                if self.hotkey_spec_alt:    hotkey_parts.append("Alt")
                hotkey_parts.append(self.hotkey_spec_key.upper().strip())
                current_hotkey = "+".join(hotkey_parts)
                box_hk.label(text=f"Current: {current_hotkey}", icon='HAND')

            layout.separator()

            # Add addon row
            box = layout.box()
            box.label(text="Manage Addon List:", icon='PLUGIN')

            row = box.row(align=True)
            row.prop(self, "addon_to_select_search", text="", icon='VIEWZOOM')
            row.operator("reload.select_add", text="", icon='ADD')

            # Populate / Select All / None row
            row = box.row(align=True)
            row.operator("reload.select_add_enabled", text="Populate All Enabled", icon='PRESET')
            row.operator("reload.select_all", text="", icon='CHECKBOX_HLT')
            row.operator("reload.select_none", text="", icon='CHECKBOX_DEHLT')

            # The list
            row = box.row()
            row.template_list(
                "RELOAD_UL_select_addons", "",
                self, "select_collection",
                self, "select_index",
                rows=6
            )
            col = row.column(align=True)
            col.operator("reload.select_remove", icon='REMOVE', text="").index = self.select_index

            layout.separator()

            # Legend / tips
            box = layout.box()
            box.label(text="Tips:", icon='INFO')
            col = box.column(align=True)
            col.label(text="• Check/uncheck addons with the toggle on the left")
            col.label(text="• Use the reload button on each row for a single-addon reload")
            col.label(text="• Use the info button on each row for diagnostics")
            col.label(text="• 'Populate All Enabled' auto-fills the list")
            col.label(text="• The list persists between sessions")


# ---------------------------------------------------------------------------
# File-menu entries
# ---------------------------------------------------------------------------

def draw_reload_in_file_menu(self, context):
    layout = self.layout
    layout.separator()
    layout.operator("addons.reload_all", text="Reload All Addons", icon='FILE_REFRESH')
    layout.operator("addons.reload_popup", text="Reload Specific Addons…", icon='PLUGIN')


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    ADDONS_OT_restore_hotkeys,
    RELOAD_OT_select_remove_checked,
    RELOAD_AddonExcludeItem,
    RELOAD_AddonSelectItem,
    RELOAD_UL_excluded_addons,
    RELOAD_UL_select_addons,
    RELOAD_OT_exclude_add,
    RELOAD_OT_exclude_remove,
    RELOAD_OT_select_add,
    RELOAD_OT_select_remove,
    RELOAD_OT_select_remove_by_name,
    RELOAD_OT_select_clear,
    RELOAD_OT_select_all,
    RELOAD_OT_select_none,
    RELOAD_OT_select_add_enabled,
    ADDONS_OT_reload_all,
    ADDONS_OT_reload_one,
    ADDONS_OT_reload_checked,
    ADDONS_OT_reload_diagnostics,
    ADDONS_OT_reload_popup,
    ADDONS_OT_capture_key,
    ReloadAddonsPreferences,
)

addon_keymaps = []


def update_keymap():
    prefs = _get_preferences()
    if prefs is None:
        return

    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    addon_keymaps.clear()

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Window', space_type='EMPTY')
        
        # 1. Reload All keymap
        key_all = prefs.hotkey_key.upper().strip()
        if key_all:
            try:
                kmi_all = km.keymap_items.new(
                    "addons.reload_all",
                    key_all,
                    'PRESS',
                    ctrl=prefs.hotkey_ctrl,
                    shift=prefs.hotkey_shift,
                    alt=prefs.hotkey_alt
                )
                addon_keymaps.append((km, kmi_all))
            except Exception as e:
                print(f"Reload All Addons: Could not assign '{key_all}' as key: {e}")

        # 2. Reload Specific keymap
        key_spec = prefs.hotkey_spec_key.upper().strip()
        if key_spec:
            try:
                kmi_spec = km.keymap_items.new(
                    "addons.reload_checked",
                    key_spec,
                    'PRESS',
                    ctrl=prefs.hotkey_spec_ctrl,
                    shift=prefs.hotkey_spec_shift,
                    alt=prefs.hotkey_spec_alt
                )
                addon_keymaps.append((km, kmi_spec))
            except Exception as e:
                print(f"Reload All Addons: Could not assign '{key_spec}' as key: {e}")

        _save_settings()

        # Helper to format keymap string
        def format_hk(ctrl, shift, alt, key):
            parts = []
            if ctrl:  parts.append("Ctrl")
            if shift: parts.append("Shift")
            if alt:   parts.append("Alt")
            parts.append(key.upper().strip())
            return "+".join(parts)

        print(f"Reload All Addons: Hotkeys updated - All: {format_hk(prefs.hotkey_ctrl, prefs.hotkey_shift, prefs.hotkey_alt, prefs.hotkey_key)} | Specific: {format_hk(prefs.hotkey_spec_ctrl, prefs.hotkey_spec_shift, prefs.hotkey_spec_alt, prefs.hotkey_spec_key)}")


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file.append(draw_reload_in_file_menu)
    update_keymap()
    bpy.app.timers.register(_delayed_load_settings, first_interval=0.1)
    print("Reload All Addons: Registered")


def unregister():
    _save_settings()
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    bpy.types.TOPBAR_MT_file.remove(draw_reload_in_file_menu)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("Reload All Addons: Unregistered")


if __name__ == "__main__":
    try:
        unregister()
    except Exception:
        pass
    register()
