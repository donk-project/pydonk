# Donk Project
# Copyright (c) 2021 Warriorstar Orion <orion@snowfrost.garden>
# SPDX-License-Identifier: MIT
from collections import namedtuple
from typing import List, OrderedDict
import argparse
import pathlib
import os

from mapparse.reader import Reader
from mapparse.reader import TreeToDmmData


class LintChecker(object):
    pass


class Severity():
    UNKNOWN = 0
    INFO = 1
    WARNING = 2
    FATAL = 3

    STRINGS = {
        UNKNOWN: "Unknown",
        INFO: "Info",
        WARNING: "Warning",
        FATAL: "Fatal",
    }

    def to_string(s):
        return Severity.STRINGS[s]


CheckResult = namedtuple('CheckResult', ['severity', 'message'])


class SingleTileChecker(LintChecker):
    """Perform a check against a single provided tile.

    The amount of information provided to this checker is intentionally minimal.
    If you need more information other than the tile datums, this check subtype
    will not be adequate.
    """

    def perform_check(self, tile) -> List[CheckResult]:
        raise NotImplementedError(
            'check is not a concrete subclass of SingleTileChecker')


class PipeVentChecker(SingleTileChecker):
    """Check that vents and pipes do not share a tile."""
    PIPE_PREFIXES = (
        "/obj/machinery/atmospherics/pipe/manifold/hidden/supply",
        "/obj/machinery/atmospherics/pipe/simple/hidden/scrubbers")
    UNARY_PREFIXES = ("/obj/machinery/atmospherics/unary", )

    def perform_check(self, tile) -> List[CheckResult]:
        result = list()
        pipes = [tile.get_datums_with_prefix(
            pth) for pth in self.PIPE_PREFIXES]
        unaries = [tile.get_datums_with_prefix(
            pth) for pth in self.UNARY_PREFIXES]
        if any(pipes) and any(unaries):
            result.append(CheckResult(Severity.WARNING,
                          "pipe on same tile as vent or scrubber"))

        return result


class CableNodeChecker(SingleTileChecker):
    """Check that a tile with cables only has one centered cable node."""

    def perform_check(self, tile) -> List[CheckResult]:
        result = list()

        # TODO(wso): We ignore electrified windows because it seems having two
        # cable nodes is the convention with long runs of reinforced window
        # spawners (e.g. Box's Vault)
        if tile.get_datums_of_type("/obj/effect/spawner/window/reinforced"):
            return result

        cables = tile.get_datums_of_type("/obj/structure/cable")
        center_nodes = 0

        if len(cables) <= 1:
            return result

        for cable in cables:
            # obj defaults: d1 = 0, d2 = 1
            d1 = tile.get_value(
                cable, 'd1') if 'd1' in tile.get_propnames(cable) else 0
            d2 = tile.get_value(
                cable, 'd2') if 'd2' in tile.get_propnames(cable) else 1
            if d1 == 0 or d2 == 0:
                center_nodes += 1

        if center_nodes > 1:
            result.append(CheckResult(Severity.WARNING,
                          "tile has multiple center cable nodes"))

        return result


class Linter(object):
    def __init__(self, dmm_path, checklist):
        self.dmm_path = dmm_path
        self.lint_failures = OrderedDict()
        self.checklist = checklist
        self.reader = Reader(self.dmm_path)
        self.mapdata: TreeToDmmData = None

    def perform_checks(self):
        self.lint_failures.clear()
        if not self.mapdata:
            self.mapdata = self.reader.Read()

        for coords, key_row in self.mapdata.map.items():
            x = coords[0]
            z = coords[2]
            y = 1
            for key in key_row:
                # TODO(wso): Actually parse out map height
                flipped_coords = (x, 256 - y, z)
                tile = self.mapdata.keys[key]

                all_findings = list()

                for check in self.checklist:
                    if issubclass(check, SingleTileChecker):
                        all_findings.append(check().perform_check(tile))

                if all_findings:
                    for checkresults in all_findings:
                        if checkresults:
                            if flipped_coords not in self.lint_failures:
                                self.lint_failures[flipped_coords] = list()
                            for result in checkresults:
                                self.lint_failures[flipped_coords].append(
                                    result)

                y += 1

    def print_failures(self):
        for coords, failures in self.lint_failures.items():
            print('\n'.join(
                [f"{coords_str(coords)}:\t{Severity.to_string(x.severity)}: {x.message}" for x in failures]))


# Cable check: If there are two cable nodes on the same tile.
# nodes are represented by "0" as one of the two values in the icon_state, e.g. "0-4"

def coords_str(coords):
    """Python may linewrap tuples on output which is dumb for our purposes."""
    return f"{coords[0]},{coords[1]},{coords[2]}"


CHECKLIST = [
    PipeVentChecker,
    CableNodeChecker,
]


def main():
    parser = argparse.ArgumentParser(
        description='Perform lint checks on a .dmm file.\nThe file must be in TGM format.')
    parser.add_argument('--dmm_file', type=os.path.expanduser,
                        help='The exact path of the map file being linted.',
                        required=True, dest='dmm_file')
    args = parser.parse_args()
    linter = Linter(args.dmm_file, CHECKLIST)
    linter.perform_checks()
    linter.print_failures()


if __name__ == '__main__':
    main()
