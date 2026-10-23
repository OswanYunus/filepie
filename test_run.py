"""FilePie test launcher — runs with console output so we can see what's happening."""
import os
import sys

from PyQt5 import QtWidgets, QtCore
import keyboard

from explorer_utils import get_selected_path
from pie_menu import PieMenu
from conversions import load_config, get_options_for, run_conversion

APP_DIR = os.path.dirname(os.path.abspath(__file__))


class Bridge(QtCore.QObject):
    trigger = QtCore.pyqtSignal()


class FilePieApp:
    def __init__(self):
        self.cfg = load_config()
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.bridge = Bridge()
        self.bridge.trigger.connect(self.show_menu)

        self._active_menu = None

        self.tray = self._build_tray()
        self._register_hotkey()

    def _build_tray(self):
        icon = self.app.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView)
        tray = QtWidgets.QSystemTrayIcon(icon)
        tray.setToolTip(f"FilePie — press {self.cfg.get('hotkey')} on a selected file")
        menu = QtWidgets.QMenu()
        menu.addAction("Exit", self.app.quit)
        tray.setContextMenu(menu)
        tray.show()
        print(f"[OK] Tray icon shown. Hotkey is: {self.cfg.get('hotkey')}")
        return tray

    def _register_hotkey(self):
        hotkey = self.cfg.get("hotkey", "ctrl+shift+q")
        keyboard.add_hotkey(hotkey, lambda: self._on_hotkey_pressed())
        print(f"[OK] Hotkey '{hotkey}' registered. Waiting for keypresses...")

    def _on_hotkey_pressed(self):
        print(f"[HOTKEY] Hotkey pressed!")
        self.bridge.trigger.emit()

    def show_menu(self):
        print("[MENU] show_menu() called on Qt thread")
        if self._active_menu is not None:
            print("[MENU] Menu already open, ignoring")
            return

        path = get_selected_path()
        print(f"[MENU] Selected path: {path}")
        if not path:
            print("[MENU] No file selected in Explorer — is Explorer the focused window?")
            self.tray.showMessage("FilePie", "No file selected in the active Explorer window.",
                                  QtWidgets.QSystemTrayIcon.Warning, 3000)
            return

        options = get_options_for(path, self.cfg)
        print(f"[MENU] Options: {options}")
        if not options:
            print("[MENU] No conversions for this file type")
            self.tray.showMessage("FilePie", "No conversions configured for this file type.",
                                  QtWidgets.QSystemTrayIcon.Warning, 3000)
            return

        name = os.path.basename(path.rstrip("\\/"))
        label = (name[:14] + "…") if len(name) > 15 else name
        print(f"[MENU] Showing pie menu for: {name}")
        menu = PieMenu(options, label, lambda target: print(f"[SELECTED] {target}"))
        menu.destroyed.connect(lambda: setattr(self, "_active_menu", None))
        self._active_menu = menu

    def run(self):
        print("[OK] FilePie running. Press the hotkey while a file is selected in Explorer.")
        print("[OK] Check tray icon (bottom-right). Press Ctrl+C here to stop.")
        sys.exit(self.app.exec_())


if __name__ == "__main__":
    FilePieApp().run()
