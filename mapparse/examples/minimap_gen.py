import os
import random
from collections import OrderedDict

from PIL import Image

from mapparse.reader import Reader
from mapparse.writer import Writer

STATION_MAPS = {
    'box': '~/ExternalRepos/third_party/Paradise/_maps/map_files/cyberiad/cyberiad.dmm',
    'delta': '~/ExternalRepos/third_party/Paradise/_maps/map_files/delta/delta.dmm',
    'meta': '~/ExternalRepos/third_party/Paradise/_maps/map_files/metastation/metastation.dmm',
}


def random_gray():
    r = random.randint(180, 240)
    g = random.randint(180, 240)
    b = random.randint(180, 240)
    return (r, r, r)


# Note these are prefixes, all subtypes will match the key with their prefix. If
# a tile doesn't match any area prefix, and has is TileShadings.UNKNOWN, it is
# colored a random shade of gray, which are also kept in here for ease of reuse
AREA_SHADING = OrderedDict({
    '/area/space': (255, 255, 255),
    '/area/medical': (117, 141, 170),
    '/area/maintenance': (160, 160, 160),
    '/area/shuttle/pod': (254, 167, 2),
    '/area/hallway/primary': (166, 171, 194),
    '/area/shuttle/gamma/station': (255, 255, 255),
    # etc...
})


class TileShadings:
    """Shadings based on the objects on the tile instead of the /area."""
    UNKNOWN = 0
    WALLS = 1
    GIRDERS_GRILLES_WINDOWS = 2
    FLOORS = 3
    TRANSIT_TUBE = 4
    SHUTTLES = 5
    SOLAR_PANELS = 6
    ROUNDSTART_CLOSED_SHUTTERS = 7
    EXTERIOR_AIRLOCKS = 8
    CATWALKS = 9
    LATTICE = 10
    PLATING = 11


COLORS = {
    TileShadings.WALLS: (0, 0, 0),
    TileShadings.GIRDERS_GRILLES_WINDOWS: (107, 107, 107),
    TileShadings.FLOORS: (164, 164, 164),
    TileShadings.PLATING: (164, 164, 164),
    TileShadings.CATWALKS: (164, 164, 164),
    TileShadings.LATTICE: (164, 164, 164),
    TileShadings.TRANSIT_TUBE: (192, 224, 252),
    TileShadings.SOLAR_PANELS: (1, 11, 101),
    TileShadings.ROUNDSTART_CLOSED_SHUTTERS: (223, 223, 223),
    TileShadings.EXTERIOR_AIRLOCKS: (86, 25, 26),
}


def determine_shading(tile):
    result = random_gray()
    area_path = tile.get_area_path()
    tile_shading = TileShadings.UNKNOWN

    area_shading_found = False
    for path, color in AREA_SHADING.items():
        if area_path.startswith(path):
            area_shading_found = True
            result = color

    if not area_shading_found:
        AREA_SHADING[area_path] = result

    shutter = tile.get_datums_with_prefix(
        '/obj/machinery/door/poddoor/shutters')
    if shutter:
        if 'icon_state' in tile.get_propnames(shutter[0]):
            icon_state = tile.get_value(shutter[0], "icon_state")
            if icon_state == 'closed':
                tile_shading = TileShadings.ROUNDSTART_CLOSED_SHUTTERS
        else:
            tile_shading = TileShadings.ROUNDSTART_CLOSED_SHUTTERS
    elif tile.get_datums_with_prefix('/obj/structure/grille'):
        tile_shading = TileShadings.GIRDERS_GRILLES_WINDOWS
    elif tile.get_datums_with_prefix('/obj/effect/spawner/window'):
        tile_shading = TileShadings.GIRDERS_GRILLES_WINDOWS
    elif tile.get_datums_with_prefix('/obj/structure/transit_tube'):
        tile_shading = TileShadings.TRANSIT_TUBE
    elif tile.get_datums_with_prefix('/obj/machinery/power/solar'):
        tile_shading = TileShadings.SOLAR_PANELS
    elif tile.get_datums_with_prefix('/obj/machinery/power/tracker'):
        tile_shading = TileShadings.SOLAR_PANELS
    elif tile.get_datums_with_prefix('/obj/machinery/door/airlock/external'):
        tile_shading = TileShadings.EXTERIOR_AIRLOCKS
    elif tile.get_datums_with_prefix('/obj/structure/lattice/catwalk'):
        tile_shading = TileShadings.CATWALKS
    elif tile.get_datums_with_prefix('/obj/structure/lattice'):
        tile_shading = TileShadings.LATTICE
    elif tile.get_datums_with_prefix('/turf/simulated/wall'):
        tile_shading = TileShadings.WALLS
    elif tile.get_datums_with_prefix('/turf/simulated/floor/plating'):
        tile_shading = TileShadings.PLATING
    elif tile.get_datums_with_prefix('/turf/simulated/floor'):
        tile_shading = TileShadings.FLOORS

    # We use floors as the 'canvas' for area type shadings, but all other tile
    # shadings will take priority over area shadings
    if tile_shading not in (TileShadings.UNKNOWN, TileShadings.FLOORS):
        result = COLORS[tile_shading]

    # Various weird fiddly logic for specific tile types

    # HACK(wso): Pods are weird because whereas e.g. a wall in medbay area gets
    # shaded as a wall, a wall in escape pod area gets shaded as the area
    if area_path.startswith('/area/shuttle/pod'):
        result = AREA_SHADING['/area/shuttle/pod']

    # HACK(wso): Get rid of station and debris lattice
    if tile_shading == TileShadings.LATTICE and tile.get_turf_path().startswith('/turf/space'):
        result = AREA_SHADING['/area/space']

    return result


for map, dmm in STATION_MAPS.items():
    r = Reader(os.path.expanduser(dmm))
    d = r.Read()

    i = Image.new('RGB', (255, 255))
    pixels = i.load()
    for coords, key_row in d.map.items():
        x = coords[0] - 1
        y = 0
        for key in key_row:
            tile = d.keys[key]
            pixels[x, y] = determine_shading(tile)
            y += 1

    i.save(f"{map}.png")

