from pathlib import Path
from typing import Union
import json

from .compact_encoder import CompactEncoder
from .jsonc import JSONCDecoder
from .json_walker import JSONWalker, JSONSplitWalker, SKIP_LIST, JSONPath

VERSION = (1, 0, 1)  # COMPATIBILITY BREAK, NEW FEATURE, BUGFIX
__version__ = '.'.join([str(x) for x in VERSION])


def load_jsonc(jsonc_path: Union[Path, str]) -> JSONWalker:
    '''
    Loads JSONC file into a JSON walker object.
    '''
    if isinstance(jsonc_path, str):
        jsonc_path = Path(jsonc_path)
    try:
        with jsonc_path.open(encoding='utf8') as jsonc_file:
            data = json.load(jsonc_file)
    except json.JSONDecodeError as err:
        with jsonc_path.open(encoding='utf8') as jsonc_file:
            data = json.load(jsonc_file, cls=JSONCDecoder)
    return JSONWalker(data)


