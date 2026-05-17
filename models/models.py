import math


class Point:
    def __init__(self, x, y, is_real=True):
        self.x = x
        self.y = y
        self.is_real = is_real  # Флаг: точка пользователя или супер-треугольника

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))


class Triangle:
    def __init__(self, p1, p2, p3):
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.center, self.radius = self._calculate_circumcircle()

    def _calculate_circumcircle(self):
        # Математика для нахождения центра и радиуса описанной окружности
        d = 2 * (self.p1.x * (self.p2.y - self.p3.y) + self.p2.x * (self.p3.y - self.p1.y) + self.p3.x * (
                    self.p1.y - self.p2.y))
        if d == 0:
            return (0, 0), 0

        ux = ((self.p1.x ** 2 + self.p1.y ** 2) * (self.p2.y - self.p3.y) + (self.p2.x ** 2 + self.p2.y ** 2) * (
                    self.p3.y - self.p1.y) + (self.p3.x ** 2 + self.p3.y ** 2) * (self.p1.y - self.p2.y)) / d
        uy = ((self.p1.x ** 2 + self.p1.y ** 2) * (self.p3.x - self.p2.x) + (self.p2.x ** 2 + self.p2.y ** 2) * (
                    self.p1.x - self.p3.x) + (self.p3.x ** 2 + self.p3.y ** 2) * (self.p2.x - self.p1.x)) / d

        r = math.sqrt((self.p1.x - ux) ** 2 + (self.p1.y - uy) ** 2)
        return (ux, uy), r

    def contains_point_in_circumcircle(self, pt):
        dist = math.sqrt((pt.x - self.center[0]) ** 2 + (pt.y - self.center[1]) ** 2)
        return dist <= self.radius + 1e-5  # Погрешность вычислений с плавающей запятой

    def has_vertex(self, p):
        return p == self.p1 or p == self.p2 or p == self.p3