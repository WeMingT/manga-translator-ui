from main_view_parts.theme import get_current_theme, get_theme_colors
from PIL.ImageQt import ImageQt
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPixmap, QTransform
from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView


class OriginalCompareView(QGraphicsView):
    """只读原图预览视图，用于和当前编辑画布做左右对比。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self._image_item: QGraphicsPixmapItem | None = None
        self._q_image_ref = None
        self._last_center_scene: QPointF | None = None
        self._last_transform = QTransform()

        self._setup_view()

    def _setup_view(self):
        self.setInteractive(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.apply_theme()

    def apply_theme(self, theme: str | None = None):
        colors = get_theme_colors(theme or get_current_theme())
        canvas_color = QColor(colors["bg_canvas"])
        self.scene.setBackgroundBrush(canvas_color)
        self.setBackgroundBrush(canvas_color)
        self.scene.update()
        self.viewport().update()

    def set_image(self, image):
        self.scene.clear()
        self._image_item = None
        self._q_image_ref = None

        if image is None:
            return

        if image.mode not in ("1", "L", "P", "RGB", "RGBA"):
            if image.mode == "LA" or "A" in image.mode:
                image = image.convert("RGBA")
            else:
                image = image.convert("RGB")

        self._q_image_ref = ImageQt(image)
        pixmap = QPixmap.fromImage(self._q_image_ref)
        self._image_item = self.scene.addPixmap(pixmap)

        if self._last_center_scene is not None:
            self.sync_view_state(self._last_transform, self._last_center_scene)
        else:
            self.fitInView(self._image_item, Qt.AspectRatioMode.KeepAspectRatio)

    def sync_view_state(self, transform, center_scene):
        if transform is None or center_scene is None:
            return

        self._last_transform = QTransform(transform)
        self._last_center_scene = QPointF(center_scene)

        if self._image_item is None:
            return

        self.setTransform(QTransform(transform))
        self.centerOn(center_scene)
        self.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._image_item is not None and self._last_center_scene is not None:
            self.centerOn(self._last_center_scene)
