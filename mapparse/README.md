# `mapparse`

The `mapparse` module includes various tools and utilities for parsing and manipulating DMM files.

Map files must be in TGM format.

# `mapparse.linter`

The `mapparse.linter` can perform automatic checks on DMM files. Currently only
per-tile checks are implemented, though room- and network-level checks are
planned.

The linter can be run directly from the command line. An example of this, with
sample output:

```shell
$ python -m mapparse.linter --dmm_file=~/path/to/your/mapfile.dmm
91,144,1:	Warning: pipe on same tile as vent or scrubber
111,78,1:	Warning: pipe on same tile as vent or scrubber
115,119,1:	Warning: tile has multiple center cable nodes
117,175,1:	Warning: pipe on same tile as vent or scrubber
117,168,1:	Warning: pipe on same tile as vent or scrubber
119,175,1:	Warning: pipe on same tile as vent or scrubber
119,168,1:	Warning: pipe on same tile as vent or scrubber
122,162,1:	Warning: pipe on same tile as vent or scrubber
134,174,1:	Warning: pipe on same tile as vent or scrubber
```

## Adding your own checks

It is straightforward to extend the linter with your own checks. See `linter.py`
for the implementations of the current checks.
