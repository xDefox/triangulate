import random
import os
import sqlite3
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QMessageBox,
    QMenu, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from models.models import Point
from logic.triangulation import triangulate
from logic.db_manager import init_db, save_session, get_recent_sessions, get_session_data_by_id, DB_NAME
from ui.canvas_view import CanvasView

try:
    from openpyxl import Workbook

    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Триангуляция Делоне")
        self.setMinimumSize(1100, 900)
        self.setStyleSheet("""
            QMainWindow { background-color: #11111b; }
            QLabel { color: #cdd6f4; font-family: 'Segoe UI', sans-serif; }
            QPushButton {
                background-color: #313244; color: #cdd6f4; border: none;
                border-radius: 6px; padding: 8px 16px;
                font-family: 'Segoe UI', sans-serif; font-size: 13px;
            }
            QPushButton:hover { background-color: #45475a; }
            QPushButton:pressed { background-color: #585b70; }
            QPushButton:disabled { background-color: #181825; color: #6c7086; }
            QLineEdit {
                background-color: #313244; color: #cdd6f4;
                border: 1px solid #45475a; border-radius: 6px; padding: 6px;
                font-family: 'Segoe UI', sans-serif;
            }
            QComboBox {
                background-color: #313244; color: #cdd6f4;
                border: 1px solid #45475a; border-radius: 6px; padding: 6px;
                min-width: 300px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #313244; color: #cdd6f4;
                selection-background-color: #45475a;
            }
        """)

        init_db()

        self.user_points = []
        self.selected_triangle = None
        self.manual_mode = False

        self.exports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exports")
        os.makedirs(self.exports_dir, exist_ok=True)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Заголовок
        header = QHBoxLayout()
        title = QLabel("▲ Триангуляция Делоне + SQLite")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #89b4fa;")
        header.addWidget(title)
        header.addStretch()

        self.points_input = QLineEdit("15")
        self.points_input.setFixedWidth(80)
        self.points_input.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_generate = QPushButton("▶ Генерировать")
        self.btn_generate.setStyleSheet("background-color: #89b4fa; color: #1e1e2e; font-weight: bold;")
        self.btn_generate.clicked.connect(self.run_demo)

        self.btn_save = QPushButton("💾 Сохранить и очистить")
        self.btn_save.clicked.connect(self.save_and_clear)

        self.btn_mode = QPushButton("✎ Ручной ввод")
        self.btn_mode.setCheckable(True)
        self.btn_mode.clicked.connect(self.toggle_mode)

        header.addWidget(QLabel("Точек:"))
        header.addWidget(self.points_input)
        header.addWidget(self.btn_generate)
        header.addWidget(self.btn_save)
        header.addWidget(self.btn_mode)
        layout.addLayout(header)

        # База данных
        db_row = QHBoxLayout()
        db_row.addWidget(QLabel("🗄 История:"))

        self.history_combo = QComboBox()
        self.history_combo.setFixedWidth(380)
        db_row.addWidget(self.history_combo)

        self.btn_load = QPushButton("⬇ Загрузить")
        self.btn_load.clicked.connect(self.load_selected_session)

        self.btn_check = QPushButton("◎ Проверить сферу")
        self.btn_check.setStyleSheet("background-color: #a6e3a1; color: #1e1e2e;")
        self.btn_check.clicked.connect(self.check_sphere)

        db_row.addWidget(self.btn_load)
        db_row.addWidget(self.btn_check)
        db_row.addStretch()
        layout.addLayout(db_row)

        # Экспорт
        export_row = QHBoxLayout()
        export_row.addWidget(QLabel("📤 Экспорт:"))

        self.btn_export_menu = QPushButton("▼ Экспорт данных")
        self.btn_export_menu.setStyleSheet("background-color: #45475a;")

        export_menu = QMenu(self)
        export_menu.addAction("TXT", lambda: self.export_data("txt"))
        export_menu.addAction("CSV", lambda: self.export_data("csv"))
        export_menu.addAction("XLSX", lambda: self.export_data("xlsx"))
        export_menu.addSeparator()
        export_menu.addAction("📋 Полный отчёт БД", lambda: self.export_data("full_db"))
        self.btn_export_menu.setMenu(export_menu)
        export_row.addWidget(self.btn_export_menu)

        self.btn_screenshot = QPushButton("📷 Скриншот")
        self.btn_screenshot.setStyleSheet("background-color: #f9e2af; color: #1e1e2e;")
        self.btn_screenshot.clicked.connect(self.save_screenshot)
        export_row.addWidget(self.btn_screenshot)

        export_row.addStretch()
        layout.addLayout(export_row)

        # Холст
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
                fill_color=QColor(166, 227, 161, 30),
                stroke_color=QColor("#a6e3a1"), stroke_width=2
            )

        if len(self.user_points) >= 3:
            try:
                for tri in triangulate(list(self.user_points)):
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

        count = int(self.points_input.text().strip() or 15)

        def add_point(i=0):
            if i >= count:
                self.btn_generate.setEnabled(True)
                return
            self.user_points.append(Point(
                x=random.randint(100, 900), y=random.randint(100, 700), is_real=True
            ))
            self.render()
            QTimer.singleShot(50, lambda: add_point(i + 1))

        add_point()

    def toggle_mode(self):
        self.manual_mode = not self.manual_mode
        self.canvas.set_manual_mode(self.manual_mode)
        if self.manual_mode:
            self.btn_mode.setText("✏ Ручной ввод")
            self.btn_mode.setStyleSheet("background-color: #f9e2af; color: #1e1e2e;")
            self.points_input.setEnabled(False)
            self.btn_generate.setEnabled(False)
        else:
            self.btn_mode.setText("✎ Ручной ввод")
            self.btn_mode.setStyleSheet("")
            self.points_input.setEnabled(True)
            self.btn_generate.setEnabled(True)

    def check_sphere(self):
        if len(self.user_points) >= 3:
            self.selected_triangle = random.choice(triangulate(list(self.user_points)))
            self.render()

    def update_history_dropdown(self):
        self.history_combo.clear()
        self.history_combo.addItem("— выберите сессию —", None)
        for row in get_recent_sessions(15):
            diam = f", D={round(row[3], 1)}" if row[3] else ""
            self.history_combo.addItem(
                f"ID:{row[0]} | {row[1]} ({row[2]}т.{diam})", str(row[0])
            )

    def load_selected_session(self):
        sid = self.history_combo.currentData()
        if not sid:
            QMessageBox.warning(self, "Внимание", "Сначала выберите сессию из списка")
            return

        data = get_session_data_by_id(int(sid))
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
        QMessageBox.information(self, "Готово", f"Сессия №{sid} загружена")

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

    def _get_timestamp(self):
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def export_data(self, export_type):
        ts = self._get_timestamp()
        sphere = self.selected_triangle

        try:
            if export_type == "full_db":
                path = os.path.join(self.exports_dir, f"full_db_report_{ts}.txt")
                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()
                cur.execute("SELECT * FROM sessions ORDER BY id ASC")
                rows = cur.fetchall()
                conn.close()

                with open(path, "w", encoding="utf-8") as f:
                    f.write("=== ПОЛНЫЙ ОТЧЁТ ПО БАЗЕ ДАННЫХ ===\n\n")
                    for row in rows:
                        f.write(f"ID сессии: {row[0]}\nВремя: {row[1]}\nТочек: {row[2]}\n")
                        f.write(f"Центр сферы: ({row[4]}, {row[5]})\nДиаметр: {row[6]}\n")
                        f.write("-" * 30 + "\n")

            else:
                if not self.user_points:
                    QMessageBox.warning(self, "Ошибка", "Нет точек для экспорта!")
                    return

                if export_type == "txt":
                    path = os.path.join(self.exports_dir, f"points_{ts}.txt")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(f"Отчёт по точкам\nКоличество: {len(self.user_points)}\nКоординаты:\n")
                        for p in self.user_points:
                            f.write(f"{p.x}, {p.y}\n")
                        if sphere:
                            f.write(f"\nСфера:\nЦентр: ({round(sphere.center[0], 2)}, {round(sphere.center[1], 2)})\n")
                            f.write(f"Диаметр: {round(sphere.radius * 2, 2)}\n")

                elif export_type == "csv":
                    path = os.path.join(self.exports_dir, f"points_{ts}.csv")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write("Type;X;Y\n")
                        for p in self.user_points:
                            f.write(f"Point;{p.x};{p.y}\n")
                        if sphere:
                            f.write(f"CircleCenter;{round(sphere.center[0], 2)};{round(sphere.center[1], 2)}\n")
                            f.write(f"Diameter;{round(sphere.radius * 2, 2)};0\n")

                elif export_type == "xlsx":
                    if not HAS_OPENPYXL:
                        QMessageBox.warning(self, "Недостаёт библиотеки",
                                            "openpyxl не установлен. Выполните: pip install openpyxl")
                        return
                    path = os.path.join(self.exports_dir, f"points_{ts}.xlsx")
                    wb = Workbook()
                    ws = wb.active
                    ws.title = "Точки"
                    ws.append(["Тип", "X", "Y"])
                    for p in self.user_points:
                        ws.append(["Точка", p.x, p.y])
                    if sphere:
                        ws.append([])
                        ws.append(["Центр сферы", round(sphere.center[0], 2), round(sphere.center[1], 2)])
                        ws.append(["Диаметр", round(sphere.radius * 2, 2), 0])
                    wb.save(path)

            QMessageBox.information(self, "Готово", f"Сохранено в exports/:\n{os.path.basename(path)}")

        except Exception as err:
            QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {err}")

    def save_screenshot(self):
        formats = {
            "PNG (*.png)": "png",
            "JPEG (*.jpg)": "jpg",
            "BMP (*.bmp)": "bmp",
            "GIF (*.gif)": "gif",
            "TIFF (*.tif)": "tif"
        }

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Сохранить скриншот",
            os.path.join(self.exports_dir, f"screenshot_{self._get_timestamp()}.png"),
            ";;".join(formats.keys())
        )

        if not file_path:
            return

        fmt = formats.get(selected_filter, "png")

        if not any(file_path.lower().endswith(f".{ext}") for ext in formats.values()):
            file_path += f".{fmt}"

        pixmap = self.canvas.grab()
        if pixmap.save(file_path, fmt.upper()):
            QMessageBox.information(self, "Готово", f"Скриншот сохранён:\n{os.path.basename(file_path)}")
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить скриншот")