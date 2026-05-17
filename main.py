import sys
import random
import os
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QFileDialog,
    QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsPathItem, QGraphicsItem
)
from PyQt6.QtCore import Qt, QPointF, QTimer
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath, QFont, QPainter

from models.models import Point
from logic.triangulation import triangulate
from logic.db_manager import init_db, save_session, get_recent_sessions, get_session_data_by_id, DB_NAME


class CanvasView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 5px;")
        self.setMinimumSize(800, 600)
        self.setSceneRect(0, 0, 900, 700)
        self.manual_mode = False
        self.user_points = []
        self.selected_triangle = None
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

    def draw_point(self, x, y, radius=3, color=Qt.GlobalColor.black):
        ellipse = QGraphicsEllipseItem(x - radius, y - radius, radius * 2, radius * 2)
        ellipse.setBrush(QBrush(color))
        ellipse.setPen(QPen(Qt.PenStyle.NoPen))
        self.scene.addItem(ellipse)

    def draw_triangle(self, p1, p2, p3, color=QColor("#42A5F5"), width=1):
        path = QPainterPath()
        path.moveTo(p1.x, p1.y)
        path.lineTo(p2.x, p2.y)
        path.lineTo(p3.x, p3.y)
        path.closeSubpath()
        item = QGraphicsPathItem(path)
        item.setPen(QPen(color, width))
        self.scene.addItem(item)

    def draw_circle(self, cx, cy, radius, fill_color=None, stroke_color=Qt.GlobalColor.green, stroke_width=2):
        ellipse = QGraphicsEllipseItem(cx - radius, cy - radius, radius * 2, radius * 2)
        if fill_color:
            ellipse.setBrush(QBrush(fill_color))
        ellipse.setPen(QPen(stroke_color, stroke_width))
        self.scene.addItem(ellipse)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Delaunay: SQLite System")
        self.setMinimumSize(1100, 900)

        init_db()

        self.user_points = []
        self.selected_triangle = None
        self.manual_mode = False

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)

        # === Верхняя панель ===
        top_row = QHBoxLayout()

        title = QLabel("Триангуляция Делоне + БД")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        top_row.addWidget(title)

        top_row.addStretch()

        self.points_input = QLineEdit("15")
        self.points_input.setFixedWidth(120)
        self.points_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.points_input.setPlaceholderText("Кол-во точек")
        top_row.addWidget(QLabel("Кол-во точек:"))
        top_row.addWidget(self.points_input)

        self.btn_generate = QPushButton("▶ Генерировать")
        self.btn_generate.setStyleSheet("background-color: #1976D2; color: white; padding: 6px 12px;")
        self.btn_generate.clicked.connect(self.run_demo)
        top_row.addWidget(self.btn_generate)

        self.btn_save = QPushButton("💾 Очистить и сохранить")
        self.btn_save.setStyleSheet("padding: 6px 12px;")
        self.btn_save.clicked.connect(self.save_and_clear)
        top_row.addWidget(self.btn_save)

        self.btn_mode = QPushButton("Режим: Генерация")
        self.btn_mode.setCheckable(True)
        self.btn_mode.setStyleSheet("padding: 6px 12px;")
        self.btn_mode.clicked.connect(self.toggle_mode)
        top_row.addWidget(self.btn_mode)

        layout.addLayout(top_row)

        # === Панель БД ===
        db_row = QHBoxLayout()

        db_row.addWidget(QLabel("База данных:"))

        self.history_combo = QComboBox()
        self.history_combo.setFixedWidth(400)
        self.history_combo.currentIndexChanged.connect(self.on_history_select)
        db_row.addWidget(self.history_combo)

        self.btn_load = QPushButton("⬇ Загрузить")
        self.btn_load.setStyleSheet("padding: 6px 12px;")
        self.btn_load.clicked.connect(self.load_selected_session)
        db_row.addWidget(self.btn_load)

        self.btn_check = QPushButton("✓ Проверить сферу")
        self.btn_check.setStyleSheet("background-color: #388E3C; color: white; padding: 6px 12px;")
        self.btn_check.clicked.connect(self.check_sphere)
        db_row.addWidget(self.btn_check)

        db_row.addStretch()
        layout.addLayout(db_row)

        # === Панель экспорта ===
        export_row = QHBoxLayout()

        export_row.addWidget(QLabel("Экспорт сессии:"))

        self.btn_export_txt = QPushButton("Экспорт TXT")
        self.btn_export_txt.clicked.connect(lambda: self.export_data("txt"))
        export_row.addWidget(self.btn_export_txt)

        self.btn_export_csv = QPushButton("Экспорт CSV")
        self.btn_export_csv.clicked.connect(lambda: self.export_data("csv"))
        export_row.addWidget(self.btn_export_csv)

        self.btn_export_db = QPushButton("📋 ПОЛНЫЙ ОТЧЕТ (ВСЯ БД)")
        self.btn_export_db.setStyleSheet("background-color: #5C6BC0; color: white; padding: 6px 12px;")
        self.btn_export_db.clicked.connect(lambda: self.export_data("full_db"))
        export_row.addWidget(self.btn_export_db)

        export_row.addStretch()
        layout.addLayout(export_row)

        # === Canvas ===
        self.canvas = CanvasView()
        self.canvas.on_click_callback = self.on_canvas_click
        layout.addWidget(self.canvas)

        self.update_history_dropdown()

    def render(self):
        self.canvas.clear_canvas()

        if self.selected_triangle is not None:
            tri = self.selected_triangle
            self.canvas.draw_circle(
                tri.center[0], tri.center[1], tri.radius,
                fill_color=QColor(0, 255, 0, 25),
                stroke_color=Qt.GlobalColor.green,
                stroke_width=2
            )

        if len(self.user_points) >= 3:
            try:
                current_tris = triangulate(list(self.user_points))
                for tri in current_tris:
                    self.canvas.draw_triangle(tri.p1, tri.p2, tri.p3)
            except Exception as e:
                print(f"Render error: {e}")

        for p in self.user_points:
            self.canvas.draw_point(p.x, p.y)

    def on_canvas_click(self, x, y):
        if not self.manual_mode:
            return
        self.user_points.append(Point(x=x, y=y, is_real=True))
        self.render()

    def run_demo(self):
        self.user_points.clear()
        self.selected_triangle = None
        self.btn_generate.setEnabled(False)

        val = self.points_input.text().strip()
        count = int(val) if val.isdigit() else 15

        def add_point(i=0):
            if i >= count:
                self.btn_generate.setEnabled(True)
                return
            self.user_points.append(Point(
                x=random.randint(100, 900),
                y=random.randint(100, 700),
                is_real=True
            ))
            self.render()
            QTimer.singleShot(50, lambda: add_point(i + 1))

        add_point()

    def toggle_mode(self):
        self.manual_mode = not self.manual_mode
        self.canvas.set_manual_mode(self.manual_mode)
        if self.manual_mode:
            self.btn_mode.setText("Режим: Ручной ввод")
            self.btn_mode.setStyleSheet("background-color: #C8E6C9; padding: 6px 12px;")
            self.points_input.setEnabled(False)
            self.btn_generate.setEnabled(False)
        else:
            self.btn_mode.setText("Режим: Генерация")
            self.btn_mode.setStyleSheet("padding: 6px 12px;")
            self.points_input.setEnabled(True)
            self.btn_generate.setEnabled(True)

    def check_sphere(self):
        if len(self.user_points) >= 3:
            self.selected_triangle = random.choice(triangulate(list(self.user_points)))
            self.render()

    def update_history_dropdown(self):
        self.history_combo.clear()
        recent = get_recent_sessions(15)
        self.history_combo.addItem("— выберите сессию —", None)
        for row in recent:
            diam_info = f", D={round(row[3], 1)}" if row[3] else ""
            text = f"ID:{row[0]} | {row[1]} ({row[2]}т.{diam_info})"
            self.history_combo.addItem(text, str(row[0]))

    def on_history_select(self):
        pass

    def load_selected_session(self):
        session_id = self.history_combo.currentData()
        if not session_id:
            QMessageBox.warning(self, "Внимание", "Сначала выберите сессию из списка")
            return

        data = get_session_data_by_id(int(session_id))
        if not data:
            return

        self.user_points.clear()
        for p in data["points"]:
            self.user_points.append(Point(x=p[0], y=p[1], is_real=True))

        if data["center"] and data["radius"]:
            class SavedSphere:
                def __init__(self, c, r):
                    self.center, self.radius = c, r
            self.selected_triangle = SavedSphere(data["center"], data["radius"])
        else:
            self.selected_triangle = None

        self.render()
        QMessageBox.information(self, "Готово", f"Сессия №{session_id} загружена")

    def save_and_clear(self):
        if self.user_points:
            tri = self.selected_triangle
            if tri is None and len(self.user_points) >= 3:
                res = triangulate(list(self.user_points))
                if res:
                    tri = res[0]
            save_session(self.user_points, tri)
            self.update_history_dropdown()
            QMessageBox.information(self, "Готово", "Конфигурация сохранена в БД!")

        self.user_points.clear()
        self.selected_triangle = None
        self.render()

    def export_data(self, export_type):
        base_path = os.path.dirname(os.path.abspath(__file__))
        sphere = self.selected_triangle

        try:
            if export_type == "full_db":
                filename = "full_db_report.txt"
                full_path = os.path.join(base_path, filename)
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM sessions ORDER BY id ASC")
                rows = cursor.fetchall()
                conn.close()

                with open(full_path, "w", encoding="utf-8") as f:
                    f.write("=== ПОЛНЫЙ ОТЧЕТ ПО ВСЕМ СЕССИЯМ ИЗ БД ===\n\n")
                    for row in rows:
                        f.write(f"ID Сессии: {row[0]}\nВремя: {row[1]}\nТочек: {row[2]}\n")
                        f.write(f"Центр сферы: ({row[4]}, {row[5]})\nДиаметр: {row[6]}\n")
                        f.write("-" * 30 + "\n")

            else:
                if not self.user_points:
                    QMessageBox.warning(self, "Ошибка", "Нет точек для экспорта!")
                    return

                if export_type == "txt":
                    filename = "export_data.txt"
                    full_path = os.path.join(base_path, filename)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(f"Отчет по точкам\nКол-во: {len(self.user_points)}\nКоординаты:\n")
                        for p in self.user_points:
                            f.write(f"{p.x}, {p.y}\n")
                        if sphere:
                            f.write(
                                f"\nПараметры проверочной сферы:\n"
                                f"Центр: ({round(sphere.center[0], 2)}, {round(sphere.center[1], 2)})\n"
                                f"Диаметр: {round(sphere.radius * 2, 2)}\n"
                            )

                elif export_type == "csv":
                    filename = "export_table.csv"
                    full_path = os.path.join(base_path, filename)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write("Type;X;Y\n")
                        for p in self.user_points:
                            f.write(f"Point;{p.x};{p.y}\n")
                        if sphere:
                            f.write(f"CircleCenter;{round(sphere.center[0], 2)};{round(sphere.center[1], 2)}\n")
                            f.write(f"Diameter;{round(sphere.radius * 2, 2)};0\n")

            QMessageBox.information(self, "Готово", f"Файл сохранен:\n{full_path}")

        except Exception as err:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {err}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()