import os
from mapparse.reader import Reader
from mapparse.writer import Writer

CYBERIAD_DMM = os.path.expanduser(
    '~/ExternalRepos/third_party/Paradise/_maps/map_files/cyberiad/cyberiad.dmm')

r = Reader(CYBERIAD_DMM)
d = r.Read()

for k, tile in d.keys.items():
    floor = tile.get_datums_of_type('/turf/simulated/floor/plasteel')
    if not floor:
        continue
    floor = floor[0]
    if tile.get_propnames(floor):
        continue

    HOLLOW = '/obj/effect/decal/warning_stripes/yellow/hollow'
    decal = tile.get_datums_of_type(HOLLOW)
    if len(decal) == 1:
        decal = decal[0]
        tile.set_value(floor, 'icon_state', 'bot')
        tile.del_datums_of_type(HOLLOW)
        print(f'Replaced key {k} decal with floor icon_state `bot`')
        continue

    YELLOW = '/obj/effect/decal/warning_stripes/yellow'
    decal = tile.get_datums_of_type(YELLOW)
    if len(decal) == 1:
        decal = decal[0]
        tile.set_value(floor, 'icon_state', 'delivery')
        tile.del_datums_of_type(YELLOW)
        print(f'Replaced key {k} decal with floor icon_state `delivery`')
        continue

    PARTIAL = '/obj/effect/decal/warning_stripes/yellow/partial'
    ARROW = '/obj/effect/decal/warning_stripes/arrow'
    partial = tile.get_datums_of_type(PARTIAL)
    arrow = tile.get_datums_of_type(ARROW)
    if len(partial) == 1 and len(arrow) == 1:
        partial = partial[0]
        arrow = arrow[0]
        tile.set_value(floor, 'icon_state', 'loadingarea')
        if 'dir' in tile.get_propnames(partial):
            direction = tile.get_value(partial, 'dir')
            tile.set_value(floor, 'dir', direction)
        tile.del_datums_of_type(PARTIAL)
        tile.del_datums_of_type(ARROW)
        print(f'Replaced key {k} decals with floor icon_state `loadingarea`')
        continue

w = Writer(d)
w.write_file(CYBERIAD_DMM)
