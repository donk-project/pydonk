from __future__ import annotations

from typing import Dict, List
import pathlib

from PIL import Image

from dmenv import dmlist

from api.constants import ICON_ADD, ICON_OVERLAY, ICON_SUBTRACT, ICON_UNDERLAY
from api.constants import dirname as _d
from iconparse.extractor import Extractor, ICON_ORDERING
from iconparse.image_store import ImageStore
from iconparse.reader import DmiData

from collections import OrderedDict


class IconManipulationError(RuntimeError):
    pass


class IconFrameset(object):
    """
    An IconFrameset contains the raw image data of a single icon state. This
    includes separate image data for each direction specified in the icon state.
    """

    def FromColor(input: str, dirs: int = 4):
        fs = IconFrameset()
        # TODO: Don't hardcode icon size
        color_rect = Image.new('RGBA', (32, 32), color=input)
        for dir in ICON_ORDERING[dirs]:
            fs.set_frames(dir, [color_rect])

        return fs

    def __init__(self):
        self._frames: Dict[int, List[Image.Image]] = dict()

    def __repr__(self):
        return f"IconFrameset<dirs={self.dircount()} frames={self.framecount()}>"

    def has_dir(self, dir: int) -> bool:
        return dir in self._frames

    def dirs(self) -> List[int]:
        return self._frames.keys()

    def is_empty(self, dir: int) -> bool:
        return len(self._frames.get(dir, None)) == 0

    def set_frames(self, dir: int, images: List[Image.Image]):
        self._frames[dir] = images

    def get_frames(self, dir: int) -> List[Image.Image]:
        if dir in self._frames:
            return self._frames[dir]

        raise IconManipulationError(f'no frames for direction {_d(dir)}')

    def dircount(self) -> int:
        """
        dircount does not necessarily map to the four possible direction-sets an
        icon state can have, i.e. 1, 4, or 8.

        For example, an icon could be retrieved with instructions to only
        extract the EAST direction. In this case, there will be one direction in
        the frameset, but it will be EAST, not SOUTH, as is the default for a
        1-directional icon state.
        """
        return len(self._frames)

    def framecount(self) -> int:
        if len(self._frames):
            # Short-circuit on the first iteration of the loop to ignore which
            # direction is actually available.
            for frames in self._frames.values():
                return len(frames)

        return 0

    def extend_dircount(self, new_count):
        """
        extend_dircount takes a frameset with less than `new_count` directions
        and copies the SOUTH direction data to all directions.

        This is used to settle discrepancies between icon interactions, e.g.
        Blend, when an operation is performed across multiple directions, but
        the input only has one.
        """
        if new_count == 8:
            raise NotImplementedError(
                'extension to 8 directions not supported yet')
        if new_count != 4:
            raise IconManipulationError(
                f'cannot extend direction to {new_count}')

        if self.dircount() != 1:
            raise IconManipulationError(
                f'frameset dircount does not need extension with dircount {self.dircount()}')

        original_frames = [f for f in self._frames.values()][0]

        directions = ICON_ORDERING[4]
        for dir in directions:
            if dir not in self._frames:
                self._frames[dir] = [img.copy() for img in original_frames]

    def get_closest_frames(self, dir: int):
        if self.has_dir(dir):
            return self.get_frames(dir)
        if len(self._frames):
            # we can't rely on the frameset containing SOUTH so we grab the
            # first one we can find
            any_dir = [x for x in self._frames.keys()][0]
            return self.get_frames(any_dir)

        raise IconManipulationError('could not find any frames')

    def manipulate(self, operand_frames: IconFrameset, function=ICON_ADD, x=1, y=1, dirs=None):
        # TODO: Animations
        # TODO: other function modes
        if dirs is None:
            dirs = operand_frames.dirs()

        # Under certain circumstances, we copy image data from one destination
        # frameset to another, to become the template on which the source
        # frameset applies its data.
        #
        # For example, when there is only one direction in the destination
        # frameset, but four directions in the source frameset, the image data
        # in the source frameset is copied to all other directions.
        #
        # TODO: Should this be comparing dirs.dircount() instead?
        if self.dircount() < operand_frames.dircount():
            self.extend_dircount(operand_frames.dircount())

        if function == ICON_OVERLAY:
            for dir in dirs:
                images = self.get_frames(dir)
                if dir in operand_frames.dirs():
                    src_frame = operand_frames.get_frames(dir)[0]
                    results = [Image.alpha_composite(
                        im, src_frame) for im in images]
                    self.set_frames(dir, results)
        elif function == ICON_UNDERLAY:
            for dir in dirs:
                images = self.get_frames(dir)
                if dir in operand_frames.dirs():
                    src_frame = operand_frames.get_frames(dir)[0]
                    results = [Image.alpha_composite(
                        src_frame, im) for im in images]
                    self.set_frames(dir, results)
        elif function == ICON_ADD:
            for dir in dirs:
                images = self.get_frames(dir)
                if dir in operand_frames.dirs():
                    src_frame = operand_frames.get_frames(dir)[0]
                    self.set_frames(dir, [dm_icon_add(x, src_frame)
                                    for x in images])
        elif function == ICON_SUBTRACT:
            for dir in dirs:
                images = self.get_frames(dir)
                if dir in operand_frames.dirs():
                    src_frame = operand_frames.get_closest_frames(dir)[0]
                    self.set_frames(dir, [dm_icon_sub(x, src_frame)
                                    for x in images])
        else:
            raise IconManipulationError(f'unsupported blend mode {function}')


class StateCollection(object):
    """
    StateCollection is a lightweight container mapping icon states to their
    image data.
    """

    def __init__(self):
        self._state_data: Dict[str, IconFrameset] = dict()

    def get_reified_state_names(self) -> List[str]:
        """
        get_reified_state_names returns the names of icon states that already
        have image data associated with them.

        This precludes icon states that may be available but have not yet been
        loaded for any reason.
        """
        return list(self._state_data.keys())

    def get_frameset(self, state_name: str) -> IconFrameset:
        return self._state_data[state_name]

    def add(self, state_name: str) -> IconFrameset:
        if state_name in self._state_data:
            raise IconManipulationError(
                f'cannot add pre-existing state {state_name!r}')
        self._state_data[state_name] = IconFrameset()
        return self._state_data[state_name]

    def set_frames(self, state_name: str, dir: int, frames: List[Image.Image]):
        if not self.has_state(state_name):
            raise IconManipulationError(f'missing icon_state {state_name!r}')
        self._state_data[state_name].set_frames(dir, frames)

    def has_state(self, state_name: str) -> bool:
        return state_name in self._state_data

    def framecount(self, state_name: str) -> int:
        if not self.has_state(state_name):
            raise IconManipulationError(f'missing icon_state {state_name!r}')
        return self._state_data[state_name].framecount()

    def dircount(self, state_name: str) -> int:
        if not self.has_state(state_name):
            raise IconManipulationError(f'missing icon_state {state_name!r}')
        return self._state_data[state_name].dircount()

    def dircount(self):
        return self._icon_frameset.dircount()

    def framecount(self):
        return self._icon_frameset.framecount()


class ExtractRules(object):
    """
    ExtractRules defines the conditions under which icon extraction occurs.
    Namely:

     - Whether or not a specific icon state or all icon states are extracted

     - Whether only one direction or all directions are extracted (note that
       which this occurs, atoms assigned this icon will use the first available
       direction image data, regardless of the set direction of the atom)

     - Whether one frame or all frames are extracted

     - Whether the moving state or default state is extracted
    """
    class LoadAllIconStates(object):
        def __repr__(self) -> str:
            return "LOAD_ALL"

    LOAD_ALL_ICON_STATES = LoadAllIconStates()

    def __init__(self, icon_state, dir, frame, moving):
        self._icon_state = icon_state
        self._dir = dir
        self._frame = frame
        self._moving = moving

    def is_state_restricted(self):
        return self._icon_state != self.LOAD_ALL_ICON_STATES

    def get_state_name_restriction(self) -> str:
        return self._icon_state

    def is_dir_restricted(self):
        return self._dir != None

    def get_dir_restriction(self) -> int:
        return self._dir

    def _repr_pieces(self) -> str:
        pieces = []
        pieces.append(f'state={self._icon_state}')
        if self._dir is not None:
            pieces.append(f'dir={_d(self._dir)}')
        if self._frame is not None:
            pieces.append(f'frame={self._frame}')
        if self._moving is not None:
            pieces.append(f'moving={self._moving}')

        return ' '.join(pieces)

    def __repr__(self) -> str:

        return f"ExtractRules<{self._repr_pieces()}>"


class Catalog(object):
    def add(self, state_name: str) -> IconFrameset:
        raise NotImplementedError()

    def get_available_state_names(self) -> List[str]:
        raise NotImplementedError()

    def get_current_state_names(self) -> List[str]:
        raise NotImplementedError()

    def get_frameset(self, state_name: str) -> IconFrameset:
        raise NotImplementedError()


class IconCatalog(Catalog):
    def __init__(self, icon_src):
        self._icon_src: icon = icon_src
        self._state_collection: StateCollection = StateCollection()

    def add(self, state_name: str) -> IconFrameset:
        return self._state_collection.add(state_name)

    def get_available_state_names(self) -> List[str]:
        # Make sure we reach into the source icon
        # TODO: Maybe use an ordered set if we care about state-insertion order
        return list(set(self._state_collection.get_reified_state_names()
                        + self._icon_src._catalog.get_available_state_names()))

    def get_current_state_names(self) -> List[str]:
        return list(set(self._state_collection.get_reified_state_names()
                        + self._icon_src._catalog.get_current_state_names()))

    def get_frameset(self, state_name: str) -> IconFrameset:
        if self._state_collection.has_state(state_name):
            return self._state_collection.get_frameset(state_name)
        elif state_name in self._icon_src._catalog.get_available_state_names():
            return self._icon_src._catalog.get_frameset(state_name)
        else:
            raise RuntimeError(f'no state {state_name!r} in catalog')

    def __repr__(self):
        output = f'IconCatalog({self._icon_src})'
        return output


class DmiCatalog(Catalog):

    IMAGE_STORE: ImageStore = None

    def __init__(self, envroot: pathlib.Path, filename):
        self._envroot: str = envroot
        self._filename: str = filename

        self._dmi_data: DmiData = None
        self._extractor: Extractor = None

        self._is_dmi_parsed: bool = False
        self._is_image_extracted: bool = False
        self._state_collection: StateCollection = StateCollection()

        self._insertion_order: OrderedDict = OrderedDict()

    def _maybe_parse(self):
        if not self._is_dmi_parsed:
            if self.IMAGE_STORE is None:
                raise RuntimeError(
                    'cannot parse DMI files without a global image store')
            self._dmi_data = self.IMAGE_STORE.GetDmiData(self._filename)
            for s in self._dmi_data.icon_states():
                self._insertion_order[s] = True
            self._is_dmi_parsed = True

    def _maybe_init_extractor(self):
        if self.IMAGE_STORE is None:
            raise RuntimeError(
                'cannot extract DMI icons without a global image store')

        self._maybe_parse()

        if not self._is_image_extracted:
            self._extractor: Extractor = self.IMAGE_STORE.GetExtractor(
                self._dmi_data)

        self._is_image_extracted = True

    def _maybe_inflate_state(self, state_name: str):
        if (not self._state_collection.has_state(state_name)) and self._extractor.HasState(state_name):
            _, state = self._extractor.GetState(state_name)
            self._state_collection.add(state_name)
            for dir in ICON_ORDERING[state.dirs]:
                rects = self._extractor._all_rects_for_state_and_direction(
                    state_name, dir)
                self._state_collection.set_frames(
                    state_name, dir, [self._extractor.image.crop(rect) for rect in rects])
            self._insertion_order[state_name] = True

    def add(self, state_name: str) -> IconFrameset:
        return self._state_collection.add(state_name)

    def get_available_state_names(self) -> List[str]:
        self._maybe_parse()

        return list(self._insertion_order.keys())

    def get_current_state_names(self) -> List[str]:
        return self._state_collection.get_reified_state_names()

    def get_frameset(self, state_name: str) -> IconFrameset:
        self._maybe_parse()
        self._maybe_init_extractor()
        self._maybe_inflate_state(state_name)

        return self._state_collection.get_frameset(state_name)

    def __repr__(self):
        output = f'DmiCatalog({self._filename})'
        return output


class icon(object):
    """
    icon is a rough interpretation of DM's /icon.

    /icons are generally loaded with an original filename and an optional icon
    state. When loaded this way, the image data from the file name are ingested
    and made available to callers. 

    Once an icon is instantiated, its image data may be manipulated via Blend
    and other destructive operations. It may also have arbitrary states and icon
    data passed to it via Insert.

    This means that while the original filename and state data is the
    jumping-off point for rendering, past a certain point the image data/state
    data in the icon is not the same as specified in the dmi file.

    For our purposes, an icon with an specific icon state is known as
    "state-restricted".
    """

    PATH = "/icon"
    _envroot = None

    def __init__(self, data_source=None,
                 icon_state=ExtractRules.LOAD_ALL_ICON_STATES,
                 dir=None, frame=None, moving=None, as_hard_copy=False):

        self._extract_rules: ExtractRules = ExtractRules(
            icon_state, dir, frame, moving)

        if isinstance(data_source, icon):
            self._catalog: Catalog = IconCatalog(data_source)
            # Pass state restriction up the chain
            # In cases like:
            #
            # var/icon/i2 = new /icon('foo.dmi', icon_state="my_state")
            # var/icon/i3 = new /icon(i2)
            #
            # We can set an atom's icon to i3, and "my_state" should be the
            # default at that point.
            if (not self._extract_rules.is_state_restricted()
                    and data_source._extract_rules.is_state_restricted()):
                self._extract_rules._icon_state = data_source._extract_rules.get_state_name_restriction()
        elif isinstance(data_source, str):
            self._catalog: Catalog = DmiCatalog(
                self._envroot, data_source)
        elif as_hard_copy:
            return
        else:
            raise IconManipulationError(
                f'data_source is {data_source!r}, not icon or str')

    def __str__(self):
        return f"/icon@{hex(id(self))}<{self._extract_rules._repr_pieces()}, {self._catalog}>"

    def __repr__(self):
        return self.__str__()

    def Blend(self, input, function=ICON_ADD, x=1, y=1):
        """
        Perform the image manipulation specified by `function`.

        For ease of understanding the below, `input` is the operator, `self` is
        the operand.
        """
        if isinstance(input, icon):
            # If both self and input are allowed to load all icon states,
            # blending does not occur because there's no way to know which icons
            # should be operated on.
            if not (self._extract_rules.is_state_restricted() or
                    input._extract_rules.is_state_restricted()):
                return

            if self._extract_rules.is_state_restricted():
                operand_state_name = input._extract_rules.get_state_name_restriction()
                operand_frames = None
                if operand_state_name in input._catalog.get_available_state_names():
                    operand_frames = input._catalog.get_frameset(
                        operand_state_name)
                else:
                    # If the state doesn't exist, just return, since we can't
                    # perform blending with no operator image data.
                    return

                dirs = None
                if self._extract_rules.is_dir_restricted():
                    if input._extract_rules.is_dir_restricted():
                        if self._extract_rules.get_dir_restriction() == input._extract_rules.get_dir_restriction():
                            dirs = [self._extract_rules.get_dir_restriction()]
                    else:
                        dirs = operand_frames.dirs()

                dest_frameset = self._catalog.get_frameset(
                    self._extract_rules.get_state_name_restriction())
                dest_frameset.manipulate(operand_frames, function, x, y, dirs=dirs)

        elif isinstance(input, str):
            operand_frames = IconFrameset.FromColor(input)
            dest_frameset = self._catalog.get_frameset(
                self._extract_rules.get_state_name_restriction())
            dest_frameset.manipulate(operand_frames, function, x, y)

        else:
            raise IconManipulationError(
                f'expected icon or str for Blend input, got {input}')

    def Insert(self, new_icon, icon_state=None, dir=None, frame=1, moving=0, delay=None):
        # TODO: Currently no animated icons are supported.
        if frame != 1:
            raise IconManipulationError(
                "animated icon states not yet supported for /icon/proc/Insert")

        if not isinstance(new_icon, icon):
            raise IconManipulationError(
                "non-icons not supported for /icon/proc/Insert")

        # In the ideal case, `self` and `new_icon` are state-restricted, and
        # `icon_state` is specified. We know exactly what needs to go where.

        # If `new_icon` isn't specified, and `self` is state-restricted, we use
        # the restricted state. If `self` isn't, we have no destination state,
        # and cannot continue.
        if icon_state is None:
            if self._extract_rules.is_state_restricted():
                icon_state = self._extract_rules.get_state_name_restriction()
            else:
                return

        source_state = None
        # if `new_icon` is not state-restricted, it looks like all we do is
        # choose the first state.
        if new_icon._extract_rules.is_state_restricted():
            source_state = new_icon._extract_rules.get_state_name_restriction()
        elif len(new_icon._catalog.get_available_state_names()):
            source_state = new_icon._catalog.get_available_state_names()[0]
        else:
            # If there's no source states, there's nothing to insert.
            return

        # Find specifically which frameset is being altered
        dest_frameset = None

        # If `self` is not state-restricted, we attempt to retrieve the frameset
        # with the name `icon_state` from our catalog. If it's not available, we
        # insert it.
        if self._extract_rules.is_state_restricted():
            dest_frameset = self._catalog.get_frameset(icon_state)
        else:
            if icon_state in self._catalog.get_available_state_names():
                dest_frameset = self._catalog.get_frameset(icon_state)
            else:
                dest_frameset = self._catalog.add(icon_state)

        # What directions are we adding this for? Either the one specified in `dir`,
        # or all the directions available in `new_icon`.
        dirs = [dir]
        if dir is None:
            if new_icon._extract_rules.is_dir_restricted():
                dirs = [new_icon._extract_rules.get_dir_restriction()]
            else:
                dirs = ICON_ORDERING[new_icon._catalog.get_frameset(
                    source_state).dircount()]

        src_frameset = new_icon._catalog.get_frameset(source_state)

        for d in dirs:
            src_frame = src_frameset.get_frames(d)[frame - 1]
            if dest_frameset.has_dir(d):
                cur_frames = dest_frameset.get_frames(d)
                if len(cur_frames) == 0:
                    cur_frames.append(src_frame)
                else:
                    cur_frames[frame - 1] = src_frame
            else:
                dest_frameset.set_frames(d, [src_frame])
            dest_frameset.set_frames(d, [src_frame])

    def hard_copy(self) -> icon:
        """
        Hard copy copies all frameset image data and returns an icon with those
        copied framesets applied.
        """
        result = icon(as_hard_copy=True)
        if len(result._catalog.get_current_state_names()) > 0:
            raise IconManipulationError(
                'hard copy of icon still has old states')
        for state_name in self._catalog.get_available_state_names():
            src_frameset = self._catalog.get_frameset(state_name)
            dest_frameset = result._catalog.add(src_frameset)
            for d in src_frameset.dirs():
                dest_frameset.set_frames([im.copy()
                                         for im in src_frameset.get_frames(d)])


class overlay_list(dmlist):
    """
    Overlays are stored in lists with slightly different semantics than normal.

    BYOND places even more restrictions on accessing elements within the list
    but we ignore those to make debugging easier and it's Python anyway.

    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __setitem__(self, key_or_index, value):
        if isinstance(key_or_index, icon):
            key_or_index = key_or_index.hard_copy()
        if isinstance(value, icon):
            value = value.hard_copy()

        super().__setitem__(key_or_index, value)

    def append(self, value, key=None):
        if isinstance(value, icon):
            value = value.hard_copy()
        if isinstance(key, icon):
            # This probably never happens?
            key = key.hard_copy()

        super().append(value, key)


# From the BYOND reference on /icon/proc/Blend:
#
#   The valid blending operations are:
#
#   ICON_ADD
#   ICON_SUBTRACT
#   ICON_MULTIPLY
#   ICON_OVERLAY
#   ICON_AND
#   ICON_OR
#   ICON_UNDERLAY
#
#   The result is a combination of each corresponding pixel in the two icons. In
#   all but ICON_OVERLAY, ICON_UNDERLAY, and ICON_OR, the transparent regions of
#   the two icons are ORed together. That means if either icon is transparent on
#   a given pixel, the result will be transparent. With ICON_OVERLAY or
#   ICON_UNDERLAY, on the other hand, the original icon shows through wherever
#   the top icon is transparent, giving the same effect as an overlay object,
#   but resulting in only a single icon. In ICON_OR, the transparent regions are
#   ANDed together; solid pixels are added together where they exist in both
#   icons, or just pass through if the other icon is transparent at that pixel.
#
# Hence the below functions for performing image manipulation as BYOND does.


def dm_icon_sub(im1, im2):
    assert len(im1.getdata()) == len(im2.getdata())
    assert im1.mode == im2.mode and im1.mode == 'RGBA'
    R1, G1, B1, A1 = im1.split()
    R2, G2, B2, A2 = im2.split()

    for x in range(im1.width):
        for y in range(im1.height):
            if A1.getpixel((x, y)) == 0 or A2.getpixel((x, y)) == 0:
                A1.putpixel((x, y), 0)
            R1.putpixel((x, y), R1.getpixel((x, y)) - R2.getpixel((x, y)))
            G1.putpixel((x, y), G1.getpixel((x, y)) - G2.getpixel((x, y)))
            B1.putpixel((x, y), B1.getpixel((x, y)) - B2.getpixel((x, y)))

    return Image.merge('RGBA', [R1, G1, B1, A1])


def dm_icon_add(im1, im2):
    assert len(im1.getdata()) == len(im2.getdata())
    assert im1.mode == im2.mode and im1.mode == 'RGBA'
    R1, G1, B1, A1 = im1.split()
    R2, G2, B2, A2 = im2.split()

    for x in range(im1.width):
        for y in range(im1.height):
            if A1.getpixel((x, y)) == 0 or A2.getpixel((x, y)) == 0:
                A1.putpixel((x, y), 0)
            R1.putpixel((x, y), R1.getpixel((x, y)) + R2.getpixel((x, y)))
            G1.putpixel((x, y), G1.getpixel((x, y)) + G2.getpixel((x, y)))
            B1.putpixel((x, y), B1.getpixel((x, y)) + B2.getpixel((x, y)))

    return Image.merge('RGBA', [R1, G1, B1, A1])
