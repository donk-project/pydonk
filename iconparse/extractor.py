from typing import Tuple, List

from iconparse.reader import DmiState, DmiData
from PIL import Image
from api.constants import NORTH, SOUTH, EAST, WEST, NORTHEAST, SOUTHEAST, NORTHWEST, SOUTHWEST


ICON_ORDERING = {
    1: [SOUTH],
    4: [SOUTH, NORTH, EAST, WEST],
    8: [SOUTH, NORTH, EAST, WEST, SOUTHEAST, SOUTHWEST, NORTHEAST, NORTHWEST],
}

ICON_FILEPART = {
    SOUTH: "s",
    NORTH: "n",
    EAST: "e",
    WEST: "w",
    SOUTHEAST: "se",
    SOUTHWEST: "sw",
    NORTHEAST: "ne",
    NORTHWEST: "nw",
}


class Extractor:
    def __init__(self, dmi_data: DmiData):
        self.dmi_data = dmi_data
        try:
            self.image = Image.open(self.dmi_data.source_filename)
            self.image = self.image.convert('RGBA')
        except:
            raise RuntimeError(
                f"could not parse dmi file {self.dmi_data.source_filename}")

        self.icons_per_row = int(
            self.dmi_data.image_width / self.dmi_data.icon_width)

    def HasState(self, name) -> bool:
        for state in self.dmi_data.states:
            if state.name == name:
                return True
        return False

    def GetState(self, name: str) -> Tuple[int, DmiState]:
        for idx, state in enumerate(self.dmi_data.states):
            if state.name == name:
                return (idx, state)
        # If a state is specified that does not exist in the icon file, the
        # default null state will be displayed if it exists.
        if name != "":
            for idx, state in enumerate(self.dmi_data.states):
                if state.name == "":
                    return (idx, state)

        return (-1, None)

    def StateNames(self) -> List[str]:
        return [x.name for x in self.dmi_data.states]

    def _all_rects_for_state_and_direction(self, state_name: str, dir: int) -> List[Tuple[int, int, int, int]]:
        idx, state = self.GetState(state_name)
        rects = []
        if idx < 0:
            return rects

        global_offset = self.dmi_data.initial_offsets[idx]
        offsets = ICON_ORDERING[state.dirs]
        if dir not in offsets:
            raise RuntimeError(f"no dir {dir} in state {state_name}")
        dir_offset = offsets.index(dir)
        # example:
        # 4 directions per frame
        # icon dimensions 32x32
        # frame 1 of state index 0, direction offset SOUTH/0 = global frame 0
        # (0, 0, 32, 32)
        # frame 2 of state index 0, direction offset SOUTH/0 = global frame 4
        # (128, 0, 32, 32)
        # frame 3 of state index 0, direction offset SOUTH/0 = global frame 8
        # (256, 0, 32, 32)

        # example:
        # 4 directions per frame
        # icon dimensions 32x32
        # frame 1 of state index 3, direction offset NORHT/1 = global frame
        cursor = global_offset + dir_offset
        for frame_no in range(state.frames):
            rect_x = int(cursor % self.icons_per_row) * \
                self.dmi_data.icon_height
            rect_y = int(cursor / self.icons_per_row) * \
                self.dmi_data.icon_width
            rects.append((rect_x, rect_y, rect_x + self.dmi_data.icon_width,
                          rect_y + self.dmi_data.icon_height))
            cursor += state.dirs
        return rects

    # The below methods are generally not used for rendering icons inside of a
    # runtime environment. Rather, they are useful for pulling out individual
    # sprites/animations from icon files independently.

    # frame is 1-indexed for consistency with dream maker
    def SingleFrameRect(self, state_name, dir=SOUTH, frame=1) -> Tuple[int, int, int, int]:
        idx, state = self.GetState(state_name)
        if idx < 0:
            return ()
        global_offset = self.dmi_data.initial_offsets[idx]
        offsets = ICON_ORDERING[state.dirs]
        if dir not in offsets:
            raise RuntimeError(f"no dir {dir} in state {state_name}")
        dir_offset = offsets.index(dir)
        if state.frames < frame:
            raise RuntimeError(f"no frame {frame} in state {state_name}")
        cursor = global_offset + dir_offset + frame - 1
        rect_x = int(cursor % self.icons_per_row) * self.dmi_data.icon_height
        rect_y = int(cursor / self.icons_per_row) * self.dmi_data.icon_width
        return (rect_x, rect_y, rect_x + self.dmi_data.icon_width, rect_y + self.dmi_data.icon_height)

    def Animate(self, output_filename, rects, duration_ticks=None):
        if duration_ticks is None:
            duration_ticks = [1] * len(rects)
        cropped = list()
        for rect in rects:
            c = self.image.crop(rect)
            cropped.append(c)

        animated = Image.new(
            'RGBA',
            (self.dmi_data.icon_width, self.dmi_data.icon_height),
            (255, 0, 0, 0))
        first_frame = cropped.pop(0)
        animated.paste(first_frame, (0, 0))
        animated.save(output_filename,
                      save_all=True,
                      disposal=2,
                      loop=0,
                      append_images=cropped,
                      duration=[x * 100.0 for x in duration_ticks],  # ms
                      transparency=0)

    def SpriteSheet(self, rects, max_icons_per_row=64) -> Image:
        # TODO: max_icons_per_row currently ignored
        image_width = len(rects) * self.dmi_data.icon_width
        image_height = self.dmi_data.icon_height
        sheet = Image.new('RGBA', (image_width, image_height))
        cursor = 0
        for rect in rects:
            cropped = self.image.crop(rect)
            dst_rect = (cursor,
                        0,
                        cursor + self.dmi_data.icon_width,
                        self.dmi_data.icon_height)
            sheet.paste(cropped, dst_rect)
            cursor += self.dmi_data.icon_width
        return sheet
