"""
自定义 Toggle Switch 控件，替代 QCheckBox 实现更现代的滑块开关。
"""

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QBrush
from PyQt6.QtWidgets import QWidget


class ToggleSwitch(QWidget):
    """iOS / Material 风格的滑块开关"""

    stateChanged = pyqtSignal(int)  # 0 or 2, compatible with QCheckBox

    def __init__(self, parent=None, checked=False):
        super().__init__(parent)
        self._checked = checked
        self._handle_position = 1.0 if checked else 0.0
        self._animation = QPropertyAnimation(self, b"handlePosition", self)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.setDuration(200)

        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self._animate(checked)

    def setCheckedNoSignal(self, checked: bool):
        """设置状态但不触发信号和动画"""
        self._checked = checked
        self._handle_position = 1.0 if checked else 0.0
        self.update()

    @pyqtProperty(float)
    def handlePosition(self):
        return self._handle_position

    @handlePosition.setter
    def handlePosition(self, pos):
        self._handle_position = pos
        self.update()

    def _animate(self, checked: bool):
        self._animation.stop()
        self._animation.setStartValue(self._handle_position)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._animate(self._checked)
            self.stateChanged.emit(2 if self._checked else 0)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = h / 2.0
        handle_radius = h / 2.0 - 3.0
        pos = self._handle_position

        # 背景轨道
        track_path = QPainterPath()
        track_path.addRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # 颜色插值
        off_color = QColor(40, 55, 80)
        on_color = QColor(74, 142, 224)
        r = int(off_color.red() + (on_color.red() - off_color.red()) * pos)
        g = int(off_color.green() + (on_color.green() - off_color.green()) * pos)
        b = int(off_color.blue() + (on_color.blue() - off_color.blue()) * pos)
        track_color = QColor(r, g, b)

        p.fillPath(track_path, QBrush(track_color))

        # 轨道边框
        border_alpha = int(60 + 40 * pos)
        p.setPen(QColor(100, 150, 210, border_alpha))
        p.drawPath(track_path)

        # 滑块手柄
        handle_x = 3.0 + pos * (w - 2 * 3.0 - 2 * handle_radius)
        handle_y = h / 2.0

        # 手柄阴影
        shadow_color = QColor(0, 0, 0, 40)
        p.setBrush(QBrush(shadow_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(handle_x + handle_radius + 0.5, handle_y + 0.5), handle_radius, handle_radius)

        # 手柄本体
        handle_color = QColor(220, 235, 255) if self._checked else QColor(180, 195, 215)
        p.setBrush(QBrush(handle_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(handle_x + handle_radius, handle_y), handle_radius, handle_radius)

        p.end()

    def sizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(44, 24)
