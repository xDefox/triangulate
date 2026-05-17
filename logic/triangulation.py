from models.models import Point, Triangle


def triangulate(points):
    if len(points) < 3:
        return []

    # Создаем "супер-треугольник", охватывающий все точки
    min_x = min(p.x for p in points)
    min_y = min(p.y for p in points)
    max_x = max(p.x for p in points)
    max_y = max(p.y for p in points)

    dx = max_x - min_x
    dy = max_y - min_y
    delta_max = max(dx, dy)
    mid_x = (min_x + max_x) / 2
    mid_y = (min_y + max_y) / 2

    p1 = Point(mid_x - 20 * delta_max, mid_y - delta_max, is_real=False)
    p2 = Point(mid_x, mid_y + 20 * delta_max, is_real=False)
    p3 = Point(mid_x + 20 * delta_max, mid_y - delta_max, is_real=False)

    super_triangle = Triangle(p1, p2, p3)
    triangulation = [super_triangle]

    for pt in points:
        bad_triangles = []
        for tri in triangulation:
            if tri.contains_point_in_circumcircle(pt):
                bad_triangles.append(tri)

        polygon = []
        for tri in bad_triangles:
            edges = [(tri.p1, tri.p2), (tri.p2, tri.p3), (tri.p3, tri.p1)]
            for edge in edges:
                shared = False
                for other_tri in bad_triangles:
                    if tri == other_tri:
                        continue
                    other_edges = [(other_tri.p1, other_tri.p2), (other_tri.p2, other_tri.p3),
                                   (other_tri.p3, other_tri.p1)]
                    if (edge[0] == other_edges[0][0] and edge[1] == other_edges[0][1]) or \
                            (edge[0] == other_edges[0][1] and edge[1] == other_edges[0][0]) or \
                            (edge[0] == other_edges[1][0] and edge[1] == other_edges[1][1]) or \
                            (edge[0] == other_edges[1][1] and edge[1] == other_edges[1][0]) or \
                            (edge[0] == other_edges[2][0] and edge[1] == other_edges[2][1]) or \
                            (edge[0] == other_edges[2][1] and edge[1] == other_edges[2][0]):
                        shared = True
                        break
                if not shared:
                    polygon.append(edge)

        for tri in bad_triangles:
            triangulation.remove(tri)

        for edge in polygon:
            new_tri = Triangle(edge[0], edge[1], pt)
            triangulation.append(new_tri)

    final_triangulation = []
    # Удаляем треугольники, связанные с супер-треугольником
    for tri in triangulation:
        if not (tri.has_vertex(p1) or tri.has_vertex(p2) or tri.has_vertex(p3)):
            final_triangulation.append(tri)

    return final_triangulation