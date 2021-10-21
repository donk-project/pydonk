# Donk Project
# Copyright (c) 2021 Warriorstar Orion <orion@snowfrost.garden>
# SPDX-License-Identifier: MIT
import pathlib
from typing import Dict

from iconparse.reader import DmiData, Reader
from iconparse.extractor import Extractor


class ImageStore:
    def __init__(self, root: pathlib.Path):
        self.root: pathlib.Path = root
        self.dmi_datas: Dict[pathlib.Path, DmiData] = dict()
        self.extractors: Dict[pathlib.Path, Extractor] = dict()

    def GetDmiData(self, filename) -> DmiData:
        p = self.root / pathlib.Path(filename)
        if p not in self.dmi_datas:
            self.dmi_datas[p] = Reader(p).Read()
        return self.dmi_datas[p]

    def GetExtractor(self, filename) -> Extractor:
        p = self.root / pathlib.Path(filename)
        if p not in self.extractors:
            self.extractors[p] = Extractor(self.GetDmiData(filename))
        return self.extractors[p]
