"""FilePie — right-click a file in Explorer, pick "Convert with FilePie",
and a radial pie menu pops up with only the conversions that make sense
for that file type.

Two modes:
  python main.py                     → installs context menu + sits in tray
  python main.py --convert "C:\f.jpg" → shows pie menu for that file, then exits
"""
import os
import sys

from PyQt5 import QtWidgets, QtCore, QtGui

from pie_menu import PieMenu
from conversions import load_config, get_options_for, run_conversion

APP_DIR = os.path.dirname(os.path.abspath(__file__))


class ConversionWorker(QtCore.QThread):
    done = QtCore.pyqtSignal(bool, str)

    def __init__(self, path, target, cfg):
        super().__init__()
        self.path, self.target, self.cfg = path, target, cfg

    def run(self):
        success, message = run_conversion(self.path, self.target, self.cfg)
        self.done.emit(success, message)


class FilePieApp:
    """Tray-resident mode: installs the context menu and stays alive to show
    notifications when conversions finish."""

    def __init__(self):
        self.cfg = load_config()
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self._active_menu = None
        self._active_worker = None

        self.tray = self._build_tray()

    # ---- tray -----------------------------------------------------------
    def _build_tray(self):
        icon = self.app.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView)
        tray = QtWidgets.QSystemTrayIcon(icon)
        tray.setToolTip("FilePie — right-click any file → Convert with FilePie")
        menu = QtWidgets.QMenu()
        menu.addAction("Install context menu", self._install_menu)
        menu.addAction("Uninstall context menu", self._uninstall_menu)
        menu.addSeparator()
        menu.addAction("Open config.json", self._open_config)
        menu.addAction("Reload config", self._reload_config)
        menu.addSeparator()
        menu.addAction("Exit", self.app.quit)
        tray.setContextMenu(menu)
        tray.show()
        tray.showMessage(
            "FilePie is running",
            "Right-click any file in Explorer → 'Convert with FilePie'",
            QtWidgets.QSystemTrayIcon.Information,
            4000,
        )
        return tray

    def _open_config(self):
        os.startfile(os.path.join(APP_DIR, "config.json"))

    def _reload_config(self):
        self.cfg = load_config()
        self._notify("FilePie", "Config reloaded.")

    def _install_menu(self):
        try:
            _install_context_menu()
            self._notify("FilePie", "Context menu installed! Right-click any file to use.")
        except Exception as e:
            self._notify("FilePie — error", str(e))

    def _uninstall_menu(self):
        try:
            _uninstall_context_menu()
            self._notify("FilePie", "Context menu removed.")
        except Exception as e:
            self._notify("FilePie — error", str(e))

    def _notify(self, title, message):
        self.tray.showMessage(title, message, QtWidgets.QSystemTrayIcon.Information, 4000)

    def run(self):
        sys.exit(self.app.exec_())


class FilePieConvert:
    """One-shot mode: show the pie menu for a specific file path, run the
    conversion, show a notification, then exit."""

    def __init__(self, file_path):
        self.cfg = load_config()
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.file_path = os.path.abspath(file_path)

        self._active_worker = None

        # Tray icon for notifications
        icon = self.app.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView)
        self.tray = QtWidgets.QSystemTrayIcon(icon)
        self.tray.show()

        # Show menu after event loop starts
        QtCore.QTimer.singleShot(50, self._show_menu)

    def _show_menu(self):
        path = self.file_path

        if not os.path.exists(path):
            self._notify("FilePie", f"File not found: {path}")
            QtCore.QTimer.singleShot(2000, self.app.quit)
            return

        options = get_options_for(path, self.cfg)
        if not options:
            self._notify("FilePie", "No conversions configured for this file type.")
            QtCore.QTimer.singleShot(2000, self.app.quit)
            return

        name = os.path.basename(path.rstrip("\\/"))
        label = (name[:14] + "…") if len(name) > 15 else name

        self.menu = PieMenu(options, label, lambda target: self._start_conversion(path, target))
        self.menu.destroyed.connect(self._on_menu_closed)

    def _on_menu_closed(self):
        # If no conversion was started, just exit
        if self._active_worker is None:
            self.app.quit()

    def _start_conversion(self, path, target):
        self._notify("FilePie", f"Converting {os.path.basename(path)} …")
        worker = ConversionWorker(path, target, self.cfg)
        worker.done.connect(self._on_done)
        self._active_worker = worker
        worker.start()

    def _on_done(self, success, message):
        self._notify("FilePie — done" if success else "FilePie — failed", message)
        # Keep alive briefly so the notification is visible
        QtCore.QTimer.singleShot(3000, self.app.quit)

    def _notify(self, title, message):
        self.tray.showMessage(title, message, QtWidgets.QSystemTrayIcon.Information, 4000)

    def run(self):
        sys.exit(self.app.exec_())


# ---- Windows context menu registration --------------------------------

def _get_python_path():
    """Get the path to pythonw.exe (windowless) for the context menu command."""
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if os.path.exists(pythonw):
        return pythonw
    return sys.executable  # fall back to python.exe


def _install_context_menu():
    """Add 'Convert with FilePie' to the Windows right-click menu for all
    files and folders. Uses HKCU so no admin is needed."""
    import winreg

    if getattr(sys, "frozen", False):
        exe_path = sys.executable
        icon_path = f'"{exe_path}",0'
        command = f'"{exe_path}" --convert "%V"'
    else:
        pythonw = _get_python_path()
        main_py = os.path.join(APP_DIR, "main.py")
        icon_path = f'"{pythonw}",0'
        command = f'"{pythonw}" "{main_py}" --convert "%V"'

    # For all file types
    keys = [
        r"Software\Classes\*\shell\FilePie",
        r"Software\Classes\Directory\shell\FilePie",
        r"Software\Classes\Directory\Background\shell\FilePie",
    ]

    for key_path in keys:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Convert with FilePie")
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon_path)
        winreg.CloseKey(key)

        cmd_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r"\command")
        winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, command)
        winreg.CloseKey(cmd_key)


def _uninstall_context_menu():
    """Remove the FilePie context menu entries."""
    import winreg

    keys = [
        r"Software\Classes\*\shell\FilePie",
        r"Software\Classes\Directory\shell\FilePie",
        r"Software\Classes\Directory\Background\shell\FilePie",
    ]

    for key_path in keys:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path + r"\command")
        except FileNotFoundError:
            pass
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        except FileNotFoundError:
            pass


# ---- entry point -------------------------------------------------------

if __name__ == "__main__":
    if "--convert" in sys.argv:
        idx = sys.argv.index("--convert")
        if idx + 1 < len(sys.argv):
            file_path = sys.argv[idx + 1]
            FilePieConvert(file_path).run()
    else:
        # Install context menu automatically on first run, then sit in tray
        _install_context_menu()
        FilePieApp().run()
