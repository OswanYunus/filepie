"""A Blender-Z-pie-menu-style radial popup.

Appears centered on the cursor as a frameless, translucent, always-on-top
window divided into wedges, one per option. Hovering highlights a wedge,
clicking it fires on_select(value), clicking outside or pressing Escape
cancels. Closes itself either way — the caller never has to manage its
lifetime beyond listening for its `destroyed` signal.
"""
import math
from PyQt5 import QtWidgets, QtGui, QtCore


class PieMenu(QtWidgets.QWidget):
    def __init__(self, options, center_label, on_select, radius=140, inner_radius=46):
        super().__init__()
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setMouseTracking(True)

        self.options = options  # [(label, value), ...]
        self.center_label = center_label
        self.on_select = on_select
        self.radius = radius
        self.inner_radius = inner_radius
        self.hover_index = -1

        size = radius * 2 + 40
        self.setFixedSize(size, size)
        pos = QtGui.QCursor.pos()
        self.move(pos.x() - size // 2, pos.y() - size // 2)

        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(QtCore.Qt.ActiveWindowFocusReason)

    # ---- geometry -----------------------------------------------------
    def _center(self):
        return QtCore.QPointF(self.width() / 2, self.height() / 2)

    def _wedge_at(self, pos):
        n = len(self.options)
        if n == 0:
            return -1
        c = self._center()
        dx, dy = pos.x() - c.x(), pos.y() - c.y()
        dist = math.hypot(dx, dy)
        if dist < self.inner_radius or dist > self.radius + 30:
            return -1
        angle = (math.degrees(math.atan2(dy, dx)) + 90) % 360  # 0deg = top
        step = 360 / n
        return int((angle + step / 2) // step) % n

    # ---- input -----------------------------------------------------
    def mouseMoveEvent(self, event):
        hovered = self._wedge_at(event.pos())
        if hovered != self.hover_index:
            self.hover_index = hovered
            self.update()

    def mousePressEvent(self, event):
        idx = self._wedge_at(event.pos())
        if idx >= 0:
            _, value = self.options[idx]
            self.close()
            self.on_select(value)
        else:
            self.close()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()

    def focusOutEvent(self, event):
        self.close()

    # ---- painting -----------------------------------------------------
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        c = self._center()
        n = len(self.options)
        if n == 0:
            return
        step = 360 / n

        for i, (text, _value) in enumerate(self.options):
            start_angle = i * step - step / 2 - 90
            rect = QtCore.QRectF(c.x() - self.radius, c.y() - self.radius,
                                  self.radius * 2, self.radius * 2)
            path = QtGui.QPainterPath()
            path.moveTo(c)
            path.arcTo(rect, -start_angle, -step)
            path.closeSubpath()

            is_hover = i == self.hover_index
            fill = QtGui.QColor(60, 130, 230, 235) if is_hover else QtGui.QColor(35, 38, 46, 215)
            painter.setBrush(fill)
            painter.setPen(QtGui.QPen(QtGui.QColor(15, 16, 20, 255), 2))
            painter.drawPath(path)

            mid = math.radians(start_angle + step / 2)
            label_r = self.inner_radius + (self.radius - self.inner_radius) / 2
            lx = c.x() + math.cos(mid) * label_r
            ly = c.y() + math.sin(mid) * label_r
            painter.setPen(QtGui.QColor(255, 255, 255))
            font = painter.font()
            font.setPointSize(10)
            font.setBold(is_hover)
            painter.setFont(font)
            painter.drawText(QtCore.QRectF(lx - 45, ly - 14, 90, 28),
                              QtCore.Qt.AlignCenter, text)

        painter.setBrush(QtGui.QColor(20, 22, 26, 240))
        painter.setPen(QtGui.QPen(QtGui.QColor(90, 150, 240), 2))
        painter.drawEllipse(c, self.inner_radius, self.inner_radius)
        painter.setPen(QtGui.QColor(230, 230, 230))
        font = painter.font()
        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(
            QtCore.QRectF(c.x() - self.inner_radius, c.y() - self.inner_radius,
                           self.inner_radius * 2, self.inner_radius * 2),
            QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
            self.center_label,
        )
