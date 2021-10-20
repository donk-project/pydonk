import os
import pathlib
import re

from iconparse.extractor import ICON_FILEPART, ICON_ORDERING
from iconparse.image_store import ImageStore


def makepath(path):
    s = re.sub("^icons/turf/", "icons/t/", str(path))
    s = re.sub("\.dmi", "$", str(s))
    return pathlib.Path(s)


class BlenderExtractor(object):
    def __init__(self, image_store: ImageStore, extract_root: str):
        self.image_store: ImageStore = image_store
        self.extract_root = extract_root
        self.filenames = [
            filename for filename in self.image_store.dmi_datas.keys()]

    def get_files(self):
        return self.filenames

    def get_states(self, filename):
        return self.image_store.GetExtractor(filename).StateNames()

    def mkdirs_for(self, filename):
        ex = self.image_store.GetExtractor(filename)
        for state in ex.StateNames():
            p = self.makepath_withroot(filename, state)
            print(p)
            os.makedirs(p, exist_ok=True)

    def makepath_withroot(self, filename, state_name: str):
        return self.extract_root / makepath(filename.relative_to(self.image_store.root)) / state_name

    def export_state(self, filename, state_name: str):
        basepath = self.makepath_withroot(filename, state_name)
        dmi_data = self.image_store.GetDmiData(filename)
        extractor = self.image_store.GetExtractor(filename)
        idx, dmi_state = extractor.GetState(state_name)
        dirs = ICON_ORDERING[dmi_state.dirs]
        for dir in dirs:
            filepart = ICON_FILEPART[dir]
            rect = extractor.SingleFrameRect(state_name, dir, frame=1)
            img = extractor.SpriteSheet([rect], max_icons_per_row=1)
            img.save(basepath / f"{filepart}.png")
