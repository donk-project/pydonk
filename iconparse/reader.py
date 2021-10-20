from lark import Lark, Transformer
from PIL import Image, UnidentifiedImageError

DMI_METADATA_GRAMMAR = r"""
dmi_data       : dmi_header dmi_metadata state_decls dmi_footer
dmi_header     : "#" "BEGIN DMI"
dmi_footer     : "#" "END DMI"
dmi_metadata   : "version = 4.0" icon_width icon_height
icon_width     : "width" "=" NUMBER
icon_height    : "height" "=" NUMBER
state_decls    : state_decl*
state_decl     : "state" "=" (("\"" STATE_NAME "\"") | NO_STATE_NAME) settings
settings       : setting*
setting        : SETTING_NAME "=" (NUMBER | FLOAT) ("," (NUMBER | FLOAT))*
SETTING_NAME   : "dirs" | "frames" | "rewind" | "delay" | "movement" | "loop" | "hotspot"
STATE_NAME     : ( "a".."z" | "A".."Z" | "0".."9" | "-" | "_" | "+" | "*" | "." | "(" | ")" | "," | "/" | "!" | ":" | "'" | "&" | ">" | "<" | "=" | "`" | "?" | "~" ) ( "a".."z" | "A".."Z" | "0".."9" | "-" | "_" | "+" | "*" | "." | " " | "(" | ")" | "," | "/" | "!" | ":" | "'" | "&" | "<" | ">" | "=" | "`" | "?" | "~" )*
NO_STATE_NAME  : "\"\""

%import common.INT -> NUMBER
%import common.FLOAT
%import common.WS
%ignore WS

"""


class DmiState:
    def __init__(self):
        self.name = ""
        self.dirs = 0
        self.frames = 0
        self.rewind = 0
        self.delay = list()

    def TotalFrameCount(self):
        return self.frames * self.dirs

    def DirFrameCount(self):
        return self.frames


class DmiData:
    def __init__(self):
        self.source_filename = ""
        self.raw_ztxt = ""
        self.icon_width = 0
        self.icon_height = 0
        self.image_width = 0
        self.image_height = 0
        self.states = list()
        self.initial_offsets = list()

    def ComputeInitialGlobalOffsets(self):
        cursor = 0
        for state in self.states:
            self.initial_offsets.append(cursor)
            cursor += state.TotalFrameCount()

    def icon_dimensions(self):
        return (self.icon_width, self.icon_height)

    def icon_states(self):
        return [x.name for x in self.states]


class TreeToDmiData(Transformer):
    def __init__(self):
        self.data = DmiData()

    def NUMBER(self, s):
        return int(s.value)

    def FLOAT(self, s):
        return float(s.value)

    def STATE_NAME(self, s):
        return s.value

    def NO_STATE_NAME(self, s):
        return ""

    def dmi_data(self, s):
        return self.data

    def icon_width(self, s):
        self.data.icon_width = s[0]

    def icon_height(self, s):
        self.data.icon_height = s[0]

    def state_decl(self, s):
        name = s.pop(0)
        new_decl = DmiState()
        new_decl.name = name
        for name, val in s[0].items():
            setattr(new_decl, name, val)
        self.data.states.append(new_decl)

    def settings(self, s):
        settings_to_vals = dict()
        for child in s:
            name = child.children.pop(0).value
            values = child.children
            if name in ['dirs', 'frames']:
                settings_to_vals[name] = values[0]
            else:
                settings_to_vals[name] = list(values)
        return settings_to_vals


class Reader:
    def __init__(self, dmi_filename):
        self.dmi_filename = dmi_filename
        self.parser = Lark(DMI_METADATA_GRAMMAR, parser='lalr',
                           start="dmi_data", transformer=TreeToDmiData())
        self.parsed = False

    def Read(self):
        if self.parsed:
            raise RuntimeError("DMI already parsed")

        try:
            self.image = Image.open(self.dmi_filename)
        except UnidentifiedImageError:
            return None

        if "Description" not in self.image.info:
            return None

        unparsed_dmi_data = self.image.info["Description"]
        data = self.parser.parse(unparsed_dmi_data)
        data.raw_ztxt = unparsed_dmi_data
        data.source_filename = self.dmi_filename
        data.image_width = self.image.width
        data.image_height = self.image.height
        data.ComputeInitialGlobalOffsets()

        self.parsed = True

        return data
