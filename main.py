"""FilePie — select a file in Explorer, hit a hotkey, get a radial menu of
only the conversions that make sense for that file type.

Run this and it sits in the system tray. Add to your Windows startup
folder (shell:startup) if you want it always running — see README.md.
"""
import os
import sys

from PyQt5 import QtWidgets, QtCore
import keyboard

from explorer_utils import get_selected_path
from pie_menu import PieMenu
from conversions import load_config, get_options_for, run_conversion

APP_DIR = os.path.dirname(os.path.abspath(__file__))


class Bridge(QtCore.QObject):
    """keyboard's hotkey callback fires on its own background thread, not
    Qt's thread. Emitting a signal through a QObject that lives on the
    main thread lets Qt safely hand the call back over to the GUI thread."""
    trigger = QtCore.pyqtSignal()


class ConversionWorker(QtCore.QThread):
    done = QtCore.pyqtSignal(bool, str)

    def __init__(self, path, target, cfg):
        super().__init__()
        self.path, self.target, self.cfg = path, target, cfg

    def run(self):
        success, message = run_conversion(self.path, self.target, self.cfg)
        self.done.emit(success, message)


class FilePieApp:
    def __init__(self):
        self.cfg = load_config()
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.bridge = Bridge()
        self.bridge.trigger.connect(self.show_menu)

        self._active_menu = None
        self._active_worker = None

        self.tray = self._build_tray()
        self._register_hotkey()

    # ---- tray -----------------------------------------------------------
    def _build_tray(self):
        icon = self.app.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView)
        tray = QtWidgets.QSystemTrayIcon(icon)
        tray.setToolTip(f"FilePie — press {self.cfg.get('hotkey')} on a selected file")
        menu = QtWidgets.QMenu()
        shortcut_action = menu.addAction(f"Shortcut: {self.cfg.get('hotkey')}")
        shortcut_action.setEnabled(False)
        menu.addAction("Open config.json", self._open_config)
        menu.addAction("Reload config", self._reload_config)
        menu.addSeparator()
        menu.addAction("Exit", self.app.quit)
        tray.setContextMenu(menu)
        tray.show()
        tray.showMessage(
            "FilePie is running",
            f"Select a file in Explorer and press {self.cfg.get('hotkey')}.",
            QtWidgets.QSystemTrayIcon.Information,
            4000,
        )
        return tray

    def _open_config(self):
        os.startfile(os.path.join(APP_DIR, "config.json"))

    def _reload_config(self):
        self.cfg = load_config()
        self._notify("FilePie", "Config reloaded.")

    # ---- hotkey -----------------------------------------------------------
    def _register_hotkey(self):
        hotkey = self.cfg.get("hotkey", "ctrl+alt+space")
        keyboard.add_hotkey(hotkey, lambda: self.bridge.trigger.emit())

    # ---- menu / conversion -----------------------------------------------------------
    def show_menu(self):
        if self._active_menu is not None:
            return  # menu already open, ignore repeat presses

        path = get_selected_path()
        if not path:
            self._notify("FilePie", "No file selected in the active Explorer window.")
            return

        options = get_options_for(path, self.cfg)
        if not options:
            self._notify("FilePie", "No conversions configured for this file type.")
            return

        name = os.path.basename(path.rstrip("\\/"))
        label = (name[:14] + "…") if len(name) > 15 else name

        menu = PieMenu(options, label, lambda target: self._start_conversion(path, target))
        menu.destroyed.connect(lambda: setattr(self, "_active_menu", None))
        self._active_menu = menu

    def _start_conversion(self, path, target):
        self._notify("FilePie", f"Converting {os.path.basename(path)} …")
        worker = ConversionWorker(path, target, self.cfg)
        worker.done.connect(self._on_conversion_done)
        self._active_worker = worker
        worker.start()

    def _on_conversion_done(self, success, message):
        self._notify("FilePie — done" if success else "FilePie — failed", message)

    def _notify(self, title, message):
        self.tray.showMessage(title, message, QtWidgets.QSystemTrayIcon.Information, 4000)

    def run(self):
        sys.exit(self.app.exec_())


if __name__ == "__main__":
    FilePieApp().run()
