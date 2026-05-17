from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsPathItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath, QPainter


class CanvasView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setStyleSheet("""
            QGraphicsView {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
            }
        """)
        self.setMinimumSize(800, 600)
        self.setSceneRect(0, 0, 900, 700)
        self.manual_mode = False
        self.on_click_callback = None

    def set_manual_mode(self, enabled):
        self.manual_mode = enabled
        self.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        if self.manual_mode and event.button() == Qt.MouseButton.LeftButton:
            pos = self.mapToScene(event.pos())
            if self.on_click_callback:
                self.on_click_callback(pos.x(), pos.y())
        super().mousePressEvent(event)

    def clear_canvas(self):
        self.scene.clear()

    def draw_point(self, x, y, radius=3, color=QColor("#cdd6f4")):
        ellipse = QGraphicsEllipseItem(x - radius, y - radius, radius * 2, radius * 2)
        ellipse.setBrush(QBrush(color))
        ellipse.setPen(QPen(Qt.PenStyle.NoPen))
        self.scene.addItem(ellipse)

    def draw_triangle(self, p1, p2, p3, color=QColor("#89b4fa"), width=1):
        path = QPainterPath()
        path.moveTo(p1.x, p1.y)
        path.lineTo(p2.x, p2.y)
        path.lineTo(p3.x, p3.y)
        path.closeSubpath()
        item = QGraphicsPathItem(path)
        item.setPen(QPen(color, width))
        self.scene.addItem(item)

    def draw_circle(self, cx, cy, radius, fill_color=None, stroke_color=QColor("#a6e3a1"), stroke_width=2):
        ellipse = QGraphicsEllipseItem(cx - radius, cy - radius, radius * 2, radius * 2)
        if fill_color:
            ellipse.setBrush(QBrush(fill_color))
        ellipse.setPen(QPen(stroke_color, stroke_width))
        self.scene.addItem(ellipse)