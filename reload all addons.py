bl_info = {
    "name": "Reload All Addons",
    "author": "Erisol3d",
    "version": (1, 5, 0),
    "blender": (4, 0, 0),
    "location": "File Menu & Preferences Panel",
    "description": "Reload all enabled addons except this one",
    "category": "Development",
}

import bpy
import addon_utils
from datetime import datetime


class RELOAD_AddonExcludeItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Addon Module Name",
        description="The module name of the addon to exclude"
    )


class RELOAD_UL_excluded_addons(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon='PLUGIN')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='PLUGIN')


def addon_search_callback(self, context, edit_text):
    this_addon = __name__.split('.')[0]
    items = []
    
    # Get all enabled addons except this one
    for mod in addon_utils.modules():
        name = mod.__name__
        if addon_utils.check(name)[1] and name != this_addon:
            if edit_text.lower() in name.lower():
                items.append(name)
    
    return items


class RELOAD_OT_exclude_add(bpy.types.Operator):
    bl_idname = "reload.exclude_add"
    bl_label = "Add to Exclude List"
    bl_description = "Add the selected addon to the exclusion list"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs = context.preferences.addons[__name__.split('.')[0]].preferences
        name = prefs.addon_to_exclude_search
        
        if not name:
            self.report({'WARNING'}, "Please select an addon first")
            return {'CANCELLED'}
            
        # Check if already in list
        if any(item.name == name for item in prefs.exclude_collection):
            self.report({'WARNING'}, f"'{name}' is already excluded")
            return {'CANCELLED'}
            
        item = prefs.exclude_collection.add()
        item.name = name
        prefs.addon_to_exclude_search = ""
        return {'FINISHED'}


class RELOAD_OT_exclude_remove(bpy.types.Operator):
    bl_idname = "reload.exclude_remove"
    bl_label = "Remove from Exclude List"
    bl_description = "Remove the selected addon from the exclusion list"
    bl_options = {'INTERNAL'}
    
    index: bpy.props.IntProperty()

    def execute(self, context):
        prefs = context.preferences.addons[__name__.split('.')[0]].preferences
        prefs.exclude_collection.remove(self.index)
        prefs.exclude_index = min(max(0, self.index - 1), len(prefs.exclude_collection) - 1)
        return {'FINISHED'}


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
        this_addon = __name__.split('.')[0]

        # Console header
        timestamp = datetime.now().strftime("%H:%M:%S")
        print("\n" + "="*70)
        print(f"RELOAD ALL ADDONS - {timestamp}")
        print("="*70)

        # Get excluded addons from preferences
        prefs = context.preferences.addons[__name__].preferences
        excluded_names = {item.name for item in prefs.exclude_collection}

        # Collect enabled addons
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
            print("="*70 + "\n")
            self.report({'INFO'}, "No addons to reload")
            return {'CANCELLED'}

        print(f"Found {len(enabled_addons)} enabled addon(s) to reload")
        if self.verbose:
            print("\nAddons to reload:")
            for i, name in enumerate(enabled_addons, 1):
                print(f"  {i}. {name}")
        print()

        # Reload addons
        reloaded_count = 0
        failed_addons = []

        for module_name in enabled_addons:
            try:
                bpy.ops.preferences.addon_disable(module=module_name)
                bpy.ops.preferences.addon_enable(module=module_name)
                reloaded_count += 1
                if self.verbose:
                    print(f"  [SUCCESS] {module_name}")
            except Exception as e:
                failed_addons.append((module_name, str(e)))
                print(f"  [FAILED] {module_name}: {str(e)}")

        # Summary
        print("\n" + "-"*70)
        print(f"SUMMARY:")
        print(f"  Successfully reloaded: {reloaded_count}")
        print(f"  Failed to reload: {len(failed_addons)}")

        if failed_addons:
            print("\nFAILED ADDONS:")
            for i, (name, error) in enumerate(failed_addons, 1):
                print(f"  {i}. {name}")
                print(f"     Error: {error}")

        print("="*70 + "\n")

        # User report
        message = f"Reloaded {reloaded_count}/{len(enabled_addons)} addon(s)"
        if failed_addons:
            message += f" ({len(failed_addons)} failed - see console)"
            self.report({'WARNING'}, message)
        else:
            self.report({'INFO'}, message)

        return {'FINISHED'}


class ReloadAddonsPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    # Hotkey settings
    hotkey_key: bpy.props.EnumProperty(
        name="Key",
        description="Key to use for the hotkey",
        items=[
            ('F1', "F1", ""),
            ('F2', "F2", ""),
            ('F3', "F3", ""),
            ('F4', "F4", ""),
            ('F5', "F5", ""),
            ('F6', "F6", ""),
            ('F7', "F7", ""),
            ('F8', "F8", ""),
            ('F9', "F9", ""),
            ('F10', "F10", ""),
            ('F11', "F11", ""),
            ('F12', "F12", ""),
            ('R', "R", ""),
        ],
        default='F3',
        update=lambda self, context: update_keymap()
    )

    hotkey_ctrl: bpy.props.BoolProperty(
        name="Ctrl",
        description="Use Ctrl modifier",
        default=True,
        update=lambda self, context: update_keymap()
    )

    hotkey_shift: bpy.props.BoolProperty(
        name="Shift",
        description="Use Shift modifier",
        default=True,
        update=lambda self, context: update_keymap()
    )

    hotkey_alt: bpy.props.BoolProperty(
        name="Alt",
        description="Use Alt modifier",
        default=False,
        update=lambda self, context: update_keymap()
    )

    # Advanced Exclusion Settings
    exclude_collection: bpy.props.CollectionProperty(type=RELOAD_AddonExcludeItem)
    exclude_index: bpy.props.IntProperty(name="Exclude Index", default=0)
    
    addon_to_exclude_search: bpy.props.StringProperty(
        name="Addon to Exclude",
        description="Search for an addon to exclude",
        search=addon_search_callback
    )

    verbose_console: bpy.props.BoolProperty(
        name="Verbose Console Output",
        description="Print detailed information to console during reload",
        default=True
    )

    def draw(self, context):
        layout = self.layout

        # Main action button
        box = layout.box()
        col = box.column(align=True)
        col.scale_y = 1.5
        col.operator("addons.reload_all", text="Reload All Addons Now", icon='FILE_REFRESH')

        layout.separator()

        # Hotkey settings
        box = layout.box()
        box.label(text="Keyboard Shortcut Settings:", icon='KEYINGSET')

        row = box.row(align=True)
        row.label(text="Modifiers:")
        row.prop(self, "hotkey_ctrl", toggle=True)
        row.prop(self, "hotkey_shift", toggle=True)
        row.prop(self, "hotkey_alt", toggle=True)

        row = box.row()
        row.label(text="Key:")
        row.prop(self, "hotkey_key", text="")

        # Display current hotkey
        hotkey_parts = []
        if self.hotkey_ctrl:
            hotkey_parts.append("Ctrl")
        if self.hotkey_shift:
            hotkey_parts.append("Shift")
        if self.hotkey_alt:
            hotkey_parts.append("Alt")
        hotkey_parts.append(self.hotkey_key)

        current_hotkey = "+".join(hotkey_parts)
        box.label(text=f"Current: {current_hotkey}", icon='HAND')

        layout.separator()

        # Console settings
        box = layout.box()
        box.label(text="Advanced Settings:", icon='SETTINGS')
        box.prop(self, "verbose_console")
        box.separator()
        
        # Refined Exclude UI
        box.label(text="Addons To Exclude:", icon='FILTER')
        
        row = box.row(align=True)
        row.prop(self, "addon_to_exclude_search", text="")
        row.operator("reload.exclude_add", text="", icon='ADD')
        
        row = box.row()
        row.template_list("RELOAD_UL_excluded_addons", "", self, "exclude_collection", self, "exclude_index")
        
        col = row.column(align=True)
        col.operator("reload.exclude_remove", icon='REMOVE', text="").index = self.exclude_index
        col.separator()
        col.operator("reload.exclude_add", icon='SORT_ASC', text="") # Placeholder for the sort icon in image if desired, but functionality is different. 
        # Actually the image has a sort/toggle icon. Blender's UIList has built-in sort. 
        # I'll stick to Add/Remove for now as requested. 
        
        layout.separator()

        # Features info
        box = layout.box()
        box.label(text="Features:", icon='INFO')
        col = box.column(align=True)
        col.label(text="• Reloads all enabled addons except this one")
        col.label(text="• Detailed console output with success/failure log")
        col.label(text="• Customizable keyboard shortcut")
        col.label(text="• Useful for development and testing")

        layout.separator()

        # Quick access info
        box = layout.box()
        box.label(text="Quick Access:", icon='VIEWZOOM')
        col = box.column(align=True)
        col.label(text=f"• Hotkey: {current_hotkey}")
        col.label(text="• File → Reload All Addons")
        col.label(text="• F3 Search → 'Reload All Addons'")


def draw_reload_in_file_menu(self, context):
    """Add to main File menu (near Restart)"""
    layout = self.layout
    layout.separator()
    layout.operator("addons.reload_all", text="Reload All Addons", icon='FILE_REFRESH')


classes = (
    RELOAD_AddonExcludeItem,
    RELOAD_UL_excluded_addons,
    RELOAD_OT_exclude_add,
    RELOAD_OT_exclude_remove,
    ADDONS_OT_reload_all,
    ReloadAddonsPreferences,
)

# Keymap storage
addon_keymaps = []


def update_keymap():
    """Update the keymap when preferences change"""
    # Get preferences
    prefs = bpy.context.preferences.addons[__name__].preferences

    # Remove old keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    # Add new keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Window', space_type='EMPTY')
        kmi = km.keymap_items.new(
            "addons.reload_all",
            prefs.hotkey_key,
            'PRESS',
            ctrl=prefs.hotkey_ctrl,
            shift=prefs.hotkey_shift,
            alt=prefs.hotkey_alt
        )
        addon_keymaps.append((km, kmi))

        # Build hotkey string for console
        hotkey_parts = []
        if prefs.hotkey_ctrl:
            hotkey_parts.append("Ctrl")
        if prefs.hotkey_shift:
            hotkey_parts.append("Shift")
        if prefs.hotkey_alt:
            hotkey_parts.append("Alt")
        hotkey_parts.append(prefs.hotkey_key)
        current_hotkey = "+".join(hotkey_parts)

        print(f"Reload All Addons: Hotkey updated to {current_hotkey}")


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # Add to main File menu (top bar)
    bpy.types.TOPBAR_MT_file.append(draw_reload_in_file_menu)

    # Register initial keymap
    update_keymap()

    print("Reload All Addons: Registered")


def unregister():
    # Unregister keymap
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

    # Run immediately when executed from script editor
    bpy.ops.addons.reload_all()
