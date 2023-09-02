'''
A collection of tools for working with JSON, JSONC files and
JSON-like data structures.
'''
from pathlib import Path
from typing import Union
import json

from .compact_encoder import CompactEncoder as CompactEncoder
from .jsonc import (
    JSONCDecoder as JSONCDecoder
)
from .json_walker import (
    JSONWalker as JSONWalker,
    JSONSplitWalker as JSONSplitWalker,
    SKIP_LIST as SKIP_LIST,
    JSONPath as JSONPath
)

VERSION = (1, 0, 4)
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
    except json.JSONDecodeError:
        with jsonc_path.open(encoding='utf8') as jsonc_file:
            data = json.load(jsonc_file, cls=JSONCDecoder)
    return JSONWalker(data)
