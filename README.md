# Reload All Addons

A Blender addon designed for developers to quickly reload all enabled addons. This is particularly useful for iterative development and testing.

## Features
- **Reload All**: Reloads all currently enabled addons with a single click or hotkey.
- **Customizable Hotkey**: Configure your preferred shortcut in the addon preferences (Default: `Ctrl + Shift + F3`).
- **Exclude List**: Advanced searchable list to exclude specific addons from the reload process.

## Release Notes

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
