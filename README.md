# Reload All Addons

A Blender addon designed for developers to quickly reload all enabled addons. This is particularly useful for iterative development and testing.

## Features
- **Reload All**: Reloads all currently enabled addons with a single click or hotkey.
- **Customizable Hotkey**: Configure your preferred shortcut in the addon preferences (Default: `Ctrl + Shift + F3`).
- **Exclude List**: Exclude specific addons from the reload process by entering their module names.
- **Detailed Logs**: View success and failure reports in the Blender console.

## Release Notes

### v1.4.0 (January 27, 2026)
- **New Feature**: Added an **Exclude Addons** option in Preferences. You can now list addon module names (comma-separated) to prevent them from being reloaded.
- **Renamed**: Updated the script name to `reload all addons.py` for better clarity in the file system.
- **UI Improvement**: Organized settings into a new "Advanced Settings" section in the addon preferences.
- **Official Repository**: Initialized GitHub repository and uploaded the source code.

### v1.3.0
- Initial internal release with basic reload functionality and customizable hotkeys.

## Installation
1. Download `reload all addons.py`.
2. In Blender, go to `Edit > Preferences > Add-ons > Install...`.
3. Select the `.py` file and enable the addon.

## License
MIT
