import flet as ft
import flet.canvas as cv
import asyncio
import random
import os
import sqlite3
from models.models import Point
from logic.triangulation import triangulate
from logic.db_manager import init_db, save_session, get_recent_sessions, get_session_data_by_id, DB_NAME


def main(page: ft.Page):
    page.title = "Delaunay: SQLite System"
    page.window_width = 1100
    page.window_height = 900
    page.theme_mode = ft.ThemeMode.LIGHT

    init_db()

    user_points = []
    selected_triangle = [None]
    cp = cv.Canvas(expand=True, shapes=[])

    points_count_input = ft.TextField(
        label="Кол-во точек",
        hint_text="15",
        value="15",
        width=120,
        text_align=ft.TextAlign.RIGHT,
    )

    def render():
        cp.shapes.clear()
        if selected_triangle[0] is not None:
            tri = selected_triangle[0]
            cp.shapes.append(cv.Circle(tri.center[0], tri.center[1], tri.radius,
                                       paint=ft.Paint(color=ft.Colors.with_opacity(0.1, ft.Colors.GREEN),
                                                      style=ft.PaintingStyle.FILL)))
            cp.shapes.append(cv.Circle(tri.center[0], tri.center[1], tri.radius,
                                       paint=ft.Paint(color=ft.Colors.GREEN, stroke_width=2,
                                                      style=ft.PaintingStyle.STROKE)))

        if len(user_points) >= 3:
            try:
                current_tris = triangulate(list(user_points))
                for tri in current_tris:
                    cp.shapes.append(cv.Path([cv.Path.MoveTo(tri.p1.x, tri.p1.y), cv.Path.LineTo(tri.p2.x, tri.p2.y),
                                              cv.Path.LineTo(tri.p3.x, tri.p3.y), cv.Path.Close()],
                                             paint=ft.Paint(color=ft.Colors.BLUE_400, stroke_width=1,
                                                            style=ft.PaintingStyle.STROKE)))
            except Exception as e:
                print(f"Render error: {e}")

        for p in user_points:
            cp.shapes.append(cv.Circle(p.x, p.y, 3, paint=ft.Paint(color=ft.Colors.BLACK)))
        page.update()

    async def run_demo(e):
        user_points.clear()
        selected_triangle[0] = None
        btn_run.disabled = True
        page.update()

        val = points_count_input.value.strip()
        count = int(val) if val.isdigit() else 15

        for _ in range(count):
            user_points.append(Point(x=random.randint(100, 900), y=random.randint(100, 700), is_real=True))
            render()
            await asyncio.sleep(0.05)

        btn_run.disabled = False
        page.update()

    def update_history_dropdown():
        recent = get_recent_sessions(15)
        history_dd.options = []
        for row in recent:
            diam_info = f", D={round(row[3], 1)}" if row[3] else ""
            history_dd.options.append(
                ft.dropdown.Option(key=str(row[0]), text=f"ID:{row[0]} | {row[1]} ({row[2]}т.{diam_info})"))
        page.update()

    def load_selected_session(e):
        if not history_dd.value:
            page.snack_bar = ft.SnackBar(ft.Text("Сначала выберите сессию из списка"), bgcolor=ft.Colors.ORANGE)
            page.snack_bar.open = True
            page.update()
            return

        session_id = int(history_dd.value)
        data = get_session_data_by_id(session_id)

        if data:
            user_points.clear()
            for p in data["points"]:
                user_points.append(Point(x=p[0], y=p[1], is_real=True))

            if data["center"] and data["radius"]:
                class SavedSphere:
                    def __init__(self, c, r):
                        self.center, self.radius = c, r

                selected_triangle[0] = SavedSphere(data["center"], data["radius"])
            else:
                selected_triangle[0] = None

            render()
            page.snack_bar = ft.SnackBar(ft.Text(f"Сессия №{session_id} загружена"))
            page.snack_bar.open = True
            page.update()

    def save_and_clear(e):
        if user_points:
            tri = selected_triangle[0]
            if tri is None and len(user_points) >= 3:
                res = triangulate(list(user_points))
                if res: tri = res[0]
            save_session(user_points, tri)
            update_history_dropdown()
            page.snack_bar = ft.SnackBar(ft.Text("Конфигурация сохранена в БД!"), bgcolor=ft.Colors.GREEN)
            page.snack_bar.open = True
        user_points.clear()
        selected_triangle[0] = None
        render()

    def export_data(export_type):
        base_path = os.path.dirname(os.path.abspath(__file__))
        sphere = selected_triangle[0]

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
                if not user_points:
                    page.snack_bar = ft.SnackBar(ft.Text("Нет точек для экспорта!"), bgcolor=ft.Colors.RED)
                    page.snack_bar.open = True
                    page.update()
                    return

                if export_type == "txt":
                    filename = "export_data.txt"
                    full_path = os.path.join(base_path, filename)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(f"Отчет по точкам\nКол-во: {len(user_points)}\nКоординаты:\n")
                        for p in user_points: f.write(f"{p.x}, {p.y}\n")
                        if sphere:
                            f.write(
                                f"\nПараметры проверочной сферы:\nЦентр: ({round(sphere.center[0], 2)}, {round(sphere.center[1], 2)})\nДиаметр: {round(sphere.radius * 2, 2)}\n")

                elif export_type == "csv":
                    filename = "export_table.csv"
                    full_path = os.path.join(base_path, filename)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write("Type;X;Y\n")
                        for p in user_points: f.write(f"Point;{p.x};{p.y}\n")
                        if sphere:
                            f.write(f"CircleCenter;{round(sphere.center[0], 2)};{round(sphere.center[1], 2)}\n")
                            f.write(f"Diameter;{round(sphere.radius * 2, 2)};0\n")

            page.snack_bar = ft.SnackBar(ft.Text(f"Файл сохранен: {full_path}"), bgcolor=ft.Colors.GREEN)

        except Exception as err:
            page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка сохранения: {err}"), bgcolor=ft.Colors.RED)

        page.snack_bar.open = True
        page.update()

    btn_run = ft.FilledButton("Генерировать", icon=ft.Icons.PLAY_ARROW, on_click=run_demo)
    btn_save = ft.OutlinedButton("Очистить и сохранить", icon=ft.Icons.SAVE, on_click=save_and_clear)

    history_dd = ft.Dropdown(
        label="История сессий",
        width=400
    )

    btn_load = ft.TextButton("Загрузить", on_click=load_selected_session)

    def check_sphere(e):
        if len(user_points) >= 3:
            selected_triangle[0] = random.choice(triangulate(list(user_points)))
            render()

    btn_check = ft.FilledButton("Проверить сферу", icon=ft.Icons.VERIFIED, color=ft.Colors.GREEN, on_click=check_sphere)

    draw_area = ft.Container(content=cp, bgcolor=ft.Colors.GREY_100, expand=True,
                             border=ft.Border.all(1, ft.Colors.GREY_300), border_radius=10)

    page.add(
        ft.Container(
            padding=10,
            content=ft.Column([
                ft.Row([
                    ft.Text("Триангуляция Делоне + БД", size=20, weight="bold"),
                    ft.Row([points_count_input, btn_run, btn_save], spacing=10)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

                ft.Row([
                    ft.Text("База данных:"), history_dd, btn_load, btn_check
                ], spacing=10),

                ft.Row([
                    ft.Text("Экспорт сессии:"),
                    ft.TextButton("Экспорт TXT", on_click=lambda _: export_data("txt")),
                    ft.TextButton("Экспорт CSV", on_click=lambda _: export_data("csv")),
                    ft.FilledButton("ПОЛНЫЙ ОТЧЕТ (ВСЯ БД)", icon=ft.Icons.ALL_INBOX,
                                    on_click=lambda _: export_data("full_db"),
                                    bgcolor=ft.Colors.SECONDARY_CONTAINER,
                                    color=ft.Colors.ON_SECONDARY_CONTAINER)
                ], spacing=10)
            ])
        ),
        draw_area
    )

    update_history_dropdown()


if __name__ == "__main__":
    ft.run(main)