from pathlib import Path
import json

from .compact_encoder import CompactEncoder
from .jsonc import JSONCDecoder
from .json_walker import JsonWalker, JsonSplitWalker, SKIP_LIST


def load_jsonc(jsonc_path: Path) -> JsonWalker:
    '''
    Loads JSONC file into JsonWalker object.
    '''
    try:
        with jsonc_path.open(encoding='utf8') as jsonc_file:
            data = json.load(jsonc_file)
    except json.JSONDecodeError as err:
        with jsonc_path.open(encoding='utf8') as jsonc_file:
            data = json.load(jsonc_file, cls=JSONCDecoder)
    return JsonWalker(data)


VERSION = (1, 1, 0)  # COMPATIBILITY BREAK, NEW FEATURE, BUGFIX
__version__ = '.'.join([str(x) for x in VERSION])
