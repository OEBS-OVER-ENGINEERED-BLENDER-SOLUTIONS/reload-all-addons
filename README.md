# Reload All Addons

A Blender addon designed for developers to quickly reload all enabled addons or selectively reload specific ones. It now uses a staged reload pipeline that prefers Blender's normal disable/enable lifecycle first, then escalates into targeted cleanup only for leftovers that can still be attributed to the addon.

## Features
- **Reload All**: Reloads all currently enabled addons with a single click or hotkey.
- **Reload Specific**: Open an interactive selection popup to reload only checked addons.
- **Staged Reload Pipeline**: Runs `addon_disable` first, inspects leftovers, applies targeted fallback cleanup, then purges `sys.modules` late before re-enabling.
- **Optional Addon Hooks**: Supports `pre_reload_cleanup()`, `post_disable_cleanup()`, and `pre_enable_cleanup()` for complex addons that need to cooperate with the reloader.
- **Selected Addon Diagnostics**: Each row in the specific-reload list includes an info button that prints a leftover inspection report without reloading the addon.
- **Leftover Inspection Report**: Reports surviving addon-owned classes, attributable keymaps, safely attributable handlers, and `sys.modules` entries.
- **Per-Addon Result Status**: Batch reloads print whether each addon was a `clean reload`, `reloaded with fallback cleanup`, or `failed`.
- **Batch Failure Isolation**: One addon failure is reported clearly without stopping the rest of the batch.
- **Conservative Cleanup**: Only removes handlers when ownership can be safely attributed to the addon. Global Blender handlers are left alone unless clearly owned.
- **Verbose Debug Logging**: Console output includes timestamps, stages used, leftover inspection details, cleanup actions, and failure reasons.
- **Customizable Hotkeys**: Configure preferred shortcuts in the addon preferences or record them interactively.
  - **Reload All Default**: `Ctrl + Shift + Alt + R`
  - **Reload Specific Default**: `Ctrl + Shift + R`
- **Exclude List**: Advanced searchable list to exclude specific addons from the main reload process.
- **Interactive Key Recorder**: Bind hotkeys dynamically by clicking "Record" and pressing the desired key combo.

## Reload Flow
For each addon, the reloader uses this internal ladder:

1. Call `pre_reload_cleanup()` if the addon exposes it.
2. Run Blender's normal `addon_disable`.
3. Call `post_disable_cleanup()` if present.
4. Inspect leftover classes, keymaps, handlers, and modules.
5. Apply targeted fallback cleanup only to leftovers that can be safely attributed.
6. Purge the addon's `sys.modules` entries.
7. Call `pre_enable_cleanup()` if present.
8. Run Blender's normal `addon_enable`.

This keeps the addon generic while still helping with stale UI, stale classes, and old module state.

## Release Notes

### v2.4.0 (July 6, 2026)
- **Staged Reload Pipeline**: Reworked reload order to prefer Blender's normal disable/enable lifecycle first, then escalate into targeted leftover cleanup only when needed.
- **Addon Cooperation Hooks**: Added optional `pre_reload_cleanup()`, `post_disable_cleanup()`, and `pre_enable_cleanup()` hook support for complex addons.
- **Selected Addon Diagnostics**: Added an info button in the specific-reload list that inspects one addon without reloading it.
- **Leftover Inspection Reporting**: Console diagnostics now report addon-attributed classes, keymaps, safely attributable handlers, and loaded `sys.modules` entries.
- **Per-Addon Batch Status**: Batch runs now report `clean reload`, `reloaded with fallback cleanup`, or `failed` for each addon.
- **Batch Failure Isolation**: A single failed addon no longer stops the rest of the reload batch.
- **Verbose Reload History**: Console output now includes timestamps, stages used, fallback usage, and failure reasons for easier troubleshooting and bug reports.
- **Registration Hardening**: Preferences and keymap setup now fail gracefully in clean/headless Blender sessions instead of partially breaking addon registration.

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

## Diagnostics
- Use the info button in the **Reload Specific** list to inspect one addon without reloading it.
- The console report shows:
  - registered classes attributed to the addon
  - addon-owned keymaps
  - safely attributable handlers
  - loaded `sys.modules` entries
- Batch reloads also log timestamps, stages used, fallback cleanup usage, and failure reasons so the output can be copied into bug reports.

## License
MIT
