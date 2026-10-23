"""Find the item currently selected in the foreground Windows Explorer window.

Uses the Shell.Application COM object, which exposes every open Explorer
window and lets us read its current selection. We match on window handle
(HWND) against the foreground window so we only ever look at the Explorer
window the user is actually looking at.
"""
import win32com.client
import win32gui


def get_selected_path():
    """Return the filesystem path of the single selected item in the
    active Explorer window, or None if nothing usable is selected
    (e.g. focus is on some other app, or nothing is selected)."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        shell = win32com.client.Dispatch("Shell.Application")
        for window in shell.Windows():
            try:
                # Shell.Application.Windows() also lists non-Explorer shell
                # windows on some systems; HWND + a Document check filters
                # those out safely.
                if window.HWND != hwnd:
                    continue
                items = window.Document.SelectedItems()
                if items.Count >= 1:
                    return items.Item(0).Path
            except Exception:
                continue
    except Exception:
        pass
    return None
