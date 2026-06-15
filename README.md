# Reload All Addons

A Blender addon designed for developers to quickly reload all enabled addons or selectively reload specific ones. It features a deep memory purge system to prevent "already registered" class and import errors.

## Features
- **Reload All**: Reloads all currently enabled addons with a single click or hotkey.
- **Reload Specific**: Open an interactive selection popup to reload only checked addons.
- **Deep Memory Purge**: Automatically unregisters stale classes from `bpy.types` and cleans reloaded packages from `sys.modules` to force Python to re-read files from disk.
- **Customizable Hotkeys**: Configure preferred shortcuts in the addon preferences or record them interactively.
  - **Reload All Default**: `Ctrl + Shift + Alt + R`
  - **Reload Specific Default**: `Ctrl + Shift + R`
- **Exclude List**: Advanced searchable list to exclude specific addons from the main reload process.
- **Interactive Key Recorder**: Bind hotkeys dynamically by clicking "Record" and pressing the desired key combo.

## Release Notes

### v2.3.0 (June 15, 2026)
- **New Default Hotkeys**: Updated defaults to `Ctrl + Shift + Alt + R` for Reload All, and `Ctrl + Shift + R` for Reload Specific.

### v2.2.0 (June 15, 2026)
- **Interactive Hotkey Recorder**: Added a "Record" button to bind hotkeys by simply pressing them (automatically captures modifiers and key codes).

### v2.1.0 (June 15, 2026)
- **Fully Custom Key Binding**: Converted dropdown enums to string inputs, allowing any valid Blender key code (e.g. `SPACE`, `NUMPAD_1`). Added safe try/except fallback logic.

### v2.0.0 (June 15, 2026)
- **Specific Hotkey & Auto-Popup**: Added customizable shortcut settings for the specific reload operator. If the selection list is empty, triggering the hotkey automatically opens the popup.

### v1.9.0 (June 15, 2026)
- **List Management Tools**: Added an individual delete (`X`) button next to each addon row, a minus (`-`) sidebar button, and a "Clear List" button to empty selection collections quickly.

### v1.8.0 (June 15, 2026)
- **Interactive Popup Selection**: Created `ADDONS_OT_reload_popup` allowing users to configure target selections and launch batch reloads from a popup modal in the File menu.

### v1.7.0 (June 15, 2026)
- **Deep Memory Purge System**: Added automatic stale class unregistration from `bpy.types` and sub-module purging from `sys.modules` to eliminate the root cause of "already registered" errors.

### v1.6.0 (June 15, 2026)
- **Selective Reloads**: Introduced a managed check-list with checkboxes and individual reload buttons per addon in the preferences tab.

### v1.5.0 (January 27, 2026)
- **New Advanced Exclude UI**: Upgraded the exclusion feature to a searchable list with add/remove buttons.
- **Improved Search**: Added autocomplete search to quickly find and add enabled addons to the exclusion list.
- **UI Refresh**: Modernized the Addon Preferences layout with a `UIList` for better management of excluded items.

### v1.4.0 (January 27, 2026)
- **New Feature**: Added an **Exclude Addons** option in Preferences.
- **Renamed**: Updated the script name to `reload all addons.py` for better clarity.
- **UI Improvement**: Organized settings into a new "Advanced Settings" section.
- **Official Repository**: Initialized GitHub repository under the OEBS organization.

### v1.3.0
- Initial internal release with basic reload functionality and customizable hotkeys.

## Installation
1. Download `reload all addons.py`.
2. In Blender, go to `Edit > Preferences > Add-ons > Install...`.
3. Select the `.py` file and enable the addon.

## License
MIT
