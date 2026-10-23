"""Quick diagnostic to check what's happening with FilePie."""
import sys
import os

print("=== FilePie Diagnostic ===")
print(f"Python: {sys.version}")
print(f"CWD: {os.getcwd()}")
print()

# 1. Check imports
print("[1] Checking imports...")
try:
    from PyQt5 import QtWidgets, QtCore
    print("    PyQt5: OK")
except Exception as e:
    print(f"    PyQt5: FAILED - {e}")

try:
    import keyboard
    print("    keyboard: OK")
except Exception as e:
    print(f"    keyboard: FAILED - {e}")

try:
    import win32com.client
    import win32gui
    print("    pywin32: OK")
except Exception as e:
    print(f"    pywin32: FAILED - {e}")

try:
    from PIL import Image
    print("    Pillow: OK")
except Exception as e:
    print(f"    Pillow: FAILED - {e}")

# 2. Check config
print()
print("[2] Checking config.json...")
try:
    from conversions import load_config
    cfg = load_config()
    print(f"    Hotkey: {cfg.get('hotkey')}")
    print(f"    Categories: {list(cfg['categories'].keys())}")
except Exception as e:
    print(f"    Config FAILED: {e}")

# 3. Check Explorer detection
print()
print("[3] Checking Explorer file detection...")
try:
    from explorer_utils import get_selected_path
    path = get_selected_path()
    if path:
        print(f"    Detected selected file: {path}")
    else:
        print("    No file detected (this is normal if Explorer isn't focused)")
except Exception as e:
    print(f"    Explorer detection FAILED: {e}")

# 4. Test keyboard hook registration
print()
print("[4] Testing keyboard hotkey registration...")
try:
    hotkey = cfg.get("hotkey", "ctrl+shift+q")
    fired = []
    keyboard.add_hotkey(hotkey, lambda: fired.append(True))
    print(f"    Hotkey '{hotkey}' registered successfully")
    keyboard.remove_all_hotkeys()
except Exception as e:
    print(f"    Hotkey registration FAILED: {e}")

# 5. Test Qt app creation
print()
print("[5] Testing Qt app creation...")
try:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    print("    QApplication: OK")
except Exception as e:
    print(f"    QApplication FAILED: {e}")

print()
print("=== Diagnostic complete ===")
