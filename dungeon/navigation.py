"""Small-grid navigation with reachable fallback destinations and path smoothing."""

from collections import deque
from math import floor

from .geometry import Vec


def neighbors(tile):
    x, y = tile
    return ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))


def flood(start, blocked):
    visited = {start}
    queue = deque([start])
    while queue:
        for tile in neighbors(queue.popleft()):
            x, y = tile
            if 0 < x < 16 and 0 < y < 16 and tile not in blocked and tile not in visited:
                visited.add(tile)
                queue.append(tile)
    return visited


def find_path(start, target, blocked, walkable, line_clear):
    """Return waypoints to target, or the nearest reachable floor center."""
    first = (floor(start.x), floor(start.y))
    parents = {first: None}
    queue = deque([first])
    while queue:
        tile = queue.popleft()
        for neighbor in neighbors(tile):
            x, y = neighbor
            if 0 < x < 16 and 0 < y < 16 and neighbor not in blocked and neighbor not in parents:
                parents[neighbor] = tile
                queue.append(neighbor)
    requested = (floor(target.x), floor(target.y))
    if requested in parents and walkable(target):
        last, destination = requested, target
    else:
        last = min(parents, key=lambda t: (Vec(t[0] + 0.5, t[1] + 0.5) - target).length())
        destination = Vec(last[0] + 0.5, last[1] + 0.5)
    route = [destination]
    tile = last
    # Include the center of the first tile as a possible turn near a corner.
    while tile is not None:
        center = Vec(tile[0] + 0.5, tile[1] + 0.5)
        if (center - route[-1]).length() > 0.01:
            route.append(center)
        tile = parents[tile]
    route.reverse()
    result = []
    anchor = start
    while route:
        index = next((i for i in range(len(route) - 1, -1, -1)
                      if line_clear(anchor, route[i])), 0)
        point = route[index]
        if (point - anchor).length() > 0.025:
            result.append(point)
        anchor = point
        route = route[index + 1:]
    return result
