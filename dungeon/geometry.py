"""World geometry, independent of the display and input libraries."""

from dataclasses import dataclass
from math import hypot


@dataclass(frozen=True, slots=True)
class Vec:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other):
        return Vec(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vec(self.x - other.x, self.y - other.y)

    def __mul__(self, scale):
        return Vec(self.x * scale, self.y * scale)

    def length(self):
        return hypot(self.x, self.y)

    def unit(self):
        length = self.length()
        return self * (1 / length) if length else Vec()


WORLD_ORIGIN = Vec(857, 226)

def project(point, origin=Vec(), tile_width=56, tile_height=28):
    return Vec(
        origin.x + (point.x - point.y) * tile_width / 2,
        origin.y + (point.x + point.y) * tile_height / 2,
    )


def unproject(point, origin=Vec(), tile_width=56, tile_height=28):
    offset = point - origin
    return Vec(
        offset.x / tile_width + offset.y / tile_height,
        offset.y / tile_height - offset.x / tile_width,
    )


def screen_direction(x, y):
    """Convert screen-relative movement to a normalized world direction."""
    return unproject(Vec(x, y)).unit()
