from __future__ import annotations
'''
This module implements :class:`JSONWalker` and :class:`JSONSplitWalker`
classes for easier, more compact way of navigating JSON files.
They use the similar syntax to pathlib Path objects, they overload the
division and integer division operators to create paths using keys like strings
and integers.

Here are some code examples:

.. code-block:: python

    from bedrock_packs.json import JSONWalker

    with open('file.json', 'r') as f:
        walker = JSONWalker.load(f)

    # the content of the file
    print(walker.data)
    # output:
    # {'a': 1, 'b': [{'x': 1, 'y': 2}, {'x': 4, 'y': 5}],
    # 'c': {'c1': {'x': 11, 'y': 22}, 'c2': {'x': 44, 'y': 55}}}

    # the value of 'a' property
    print((walker / 'a').data)
    # output:
    # 1

    # the value of any list element from 'b' property
    for i in (walker / 'b' // int).data:
        print(i.data)
    # output:
    # {'x': 1, 'y': 2}
    # {'x': 4, 'y': 5}

    # the 'x' value of any item (from list or object) from any object that
    # matches the '[a-z]' regex
    for i in (walker // '[a-z]' // None / 'x').data:
        print(i.data)
    # output:
    # 1
    # 4
    # 11
    # 44

    # Creating JSON paths using create_path method
    data = JSONWalker({})

    new_path = data /'a' / 'b'
    new_path.create_path("Hello")
    # data:
    # {"a": {"b": "Hello"}}

    new_path = data / 'c' / 3
    new_path.create_path("Test", empty_list_item_factory=lambda: "abc")
    # data:
    # {"a": {"b": "Hello"}, "c": ["abc", "abc", "abc", "Test"]}
'''
import json
import re
from typing import Literal, Union, Type, Optional, IO, Callable, Iterator

class SKIP_LIST:
    '''Used as literal value for JSONSplitWalker paths'''


## Type definitions
JSON = Union[dict, list, str, float, int, bool, None]
JSON_KEY = Union[str, int]
JSON_SPLIT_KEY = Union[str, Type[int], Type[str], None, Type[SKIP_LIST]]
JSON_WALKER_DATA = Union[dict, list, str, float, int, bool, None, Exception]


class JSONWalker:
    '''
    Safe access to data accessed with json.load without risk of exceptions.
    '''

    def __init__(
            self, data: JSON_WALKER_DATA, *,
            parent: Optional[JSONWalker] = None,
            parent_key: Optional[JSON_KEY] = None):
        if not isinstance(
                data, (Exception, dict, list, str, float, int, bool, type(None))):
            raise ValueError('Input data is not JSON.')
        self._data: JSON_WALKER_DATA = data
        self._parent = parent
        self._parent_key = parent_key

    @property
    def parent(self) -> JSONWalker:
        '''
        The :class:`JSONWalker` which created this instance of
        :class:`JSONWalker` with :code:`__truediv__` or :code:`__floordiv__` .

        :rises: :class:`KeyError` when this :class:`JSONWalker` is a root
            object.
        '''
        if self._parent is None:
            raise KeyError("You can't get parent of the root object.")
        return self._parent

    @property
    def parent_key(self) -> JSON_KEY:
        '''
        The JSON key used to access this :class:`JSONWalker` from parent
        :class:`JSONWalker` .

        :rises: :class:`KeyError` when this :class:`JSONWalker` is a root
            object
        '''
        if self._parent_key is None:
            raise KeyError("You can't get parent of the root object.")
        return self._parent_key

    @staticmethod
    def loads(json_text: Union[str, bytes], **kwargs) -> JSONWalker:
        '''
        Create :class:`JSONWalker` from string with :code:`json.loads()` .

        :rises: Any type of exception risen by :code:`json.loads()` function
            (:class:`ValueError`).
        '''
        data = json.loads(json_text, **kwargs)
        return JSONWalker(data)

    @staticmethod
    def load(json_file: IO, **kwargs) -> JSONWalker:
        '''
        Create :class:`JSONWalker` from file input with :code:`json.load()` .

        :rises: Any type of exception risen by :code:`json.load()` function
            (:class:`ValueError`).
        '''
        data = json.load(json_file, **kwargs)
        return JSONWalker(data)

    @property
    def data(self) -> JSON_WALKER_DATA:
        '''
        The part of the JSON file related to this :class:`JSONWalker`.
        '''
        return self._data

    @data.setter
    def data(self, value: JSON):
        if self._parent is not None:
            self.parent.data[  # type: ignore
                self.parent_key  # type: ignore
            ] = value
        self._data = value

    def create_path(
            self, data: JSON, *,
            exists_ok: bool = True,
            can_break_data_structure: bool = True,
            can_create_empty_list_items: bool = True,
            empty_list_item_factory: Optional[Callable[[], JSON]] = None):
        '''
        Creates path to the part of JSON file pointed by this JSONWalker.

        :param data: the data to put at the end of the path.
        :param exists_ok: if False, the ValueError will be risen if the path
            to this item already exists.
        :param can_break_data_structure: if True than the function will be able
            to replace certain existing paths with dicts or lists. Example -
            if path "a"/"b"/"c" points at integer, creating path
            "a"/"b"/"c"/"d" will replace this integer with a dict in order to
            make "d" a valid key. Setting this to false will cause a KeyError
            in this situation.
        :param can_create_empty_list_items: enables filling up the lists in
            JSON with values produced by the empty_list_item_factory in order
            to match the item index specified in the path. Example - if you
            specify a path to create "a"/5/"c" but the list at "a" path only
            has 2 items, then the function will create additional item so
            the 5th index can be valid.
        :param empty_list_item_factory: a function used to create items for
            lists in order to make indices specified in the path valid (see
            can_create_empty_list_items function parameter). If this value
            is left as None than the lists will be filled with null values.
        '''
        if self.exists:
            if exists_ok:
                return
            raise ValueError("Path already exists")
        if empty_list_item_factory is None:
            def empty_list_item_factory(): return None
        curr_item = self.root
        path = self.path
        for key in path:
            if isinstance(key, str):  # key is a string data must be a dict
                if not isinstance(curr_item.data, dict):
                    if not can_break_data_structure:
                        raise KeyError(key)
                    curr_item.data = {}
                if key not in curr_item.data:
                    can_break_data_structure = True  # Creating new data
                curr_item = curr_item / key
            elif isinstance(key, int):  # key is an int data must be a list
                if key < 0:
                    raise KeyError(key)
                if not isinstance(curr_item.data, list):
                    if not can_break_data_structure:
                        raise KeyError(key)
                    curr_item.data = []
                if len(curr_item.data)-1 < key:
                    if not can_create_empty_list_items:
                        raise KeyError(key)
                    curr_item.data += [
                        empty_list_item_factory()
                        for _ in range(1+key-len(curr_item.data))
                    ]
                    can_break_data_structure = True  # Creating new data
                curr_item = curr_item / key
            else:
                raise KeyError(key)
        self._parent = curr_item.parent
        self._parent_key = curr_item.parent_key
        self.data = data

    @property
    def exists(self) -> bool:
        '''
        Returns true if path to this item already exists.
        '''
        keys: list[JSON_KEY] = []
        root = self
        try:
            while True:
                keys.append(root.parent_key)
                root = root.parent
        except KeyError:
            pass
        keys = list(reversed(keys))
        root_data = root.data
        try:
            for key in keys:
                root_data = root_data[key]  # type: ignore
        except:  # pylint: disable=bare-except
            return False
        return True

    @property
    def root(self) -> JSONWalker:
        '''
        The root object of this JSON file.
        '''
        root = self
        try:
            while True:
                root = root.parent
        except KeyError:
            pass
        return root

    @property
    def path(self) -> tuple[JSON_KEY, ...]:
        '''
        Full JSON path to this :class:`JSONWalker` starting from the root of
        the JSON file (loaded recursively from JSON parents).
        '''
        result: list[JSON_KEY] = []
        parent = self
        try:
            while True:
                result.append(parent.parent_key)
                parent = parent.parent
        except KeyError:
            pass
        return tuple(reversed(result))

    def __truediv__(self, key: JSON_KEY) -> JSONWalker:
        '''
        Try to access next object in the JSON path. Returns :class:`JSONWalker`
        with the next object in JSON path or with an exception if the path is
        invalid. The exception is not risen, it becomes the data of returned
        :class:`JSONWalker`.

        :param key: a json key (list index or object field name)
        '''
        try:
            return JSONWalker(
                self.data[key],  # type: ignore
                parent=self, parent_key=key)
        except Exception as e:  # pylint: disable=broad-except
            return JSONWalker(e, parent=self, parent_key=key)

    def __floordiv__(self, key: JSON_SPLIT_KEY) -> JSONSplitWalker:
        '''
        Access multiple objects from this :class:`JSONWalker` at once. Return
        :class:`JSONSplitWalker`.

        :param key: :code:`str` (any item from dictionary), :code:`int` (any
            item from list), regular expression (matches dictionary keys),
            :code:`None` (any item from dictionary or list),
            or :code:`SKIP_LIST` (access to all list items if
            current path points at list or skip this step and return
            JSONSplitWalker with only current JSONWalker).

        :raises:
            :class:`TypeError` - invalid input data type

            :class:`re.error` - invlid regular expression.
        '''
        # pylint: disable=too-many-return-statements
        # ANYTHING
        if key is None:
            if isinstance(self.data, dict):
                return JSONSplitWalker([
                    JSONWalker(v, parent=self, parent_key=k)
                    for k, v in self.data.items()
                ])
            if isinstance(self.data, list):
                return JSONSplitWalker([
                    JSONWalker(v, parent=self, parent_key=i)
                    for i, v in enumerate(self.data)
                ])
        # ANY LIST ITEM
        elif key is int:
            if isinstance(self.data, list):
                return JSONSplitWalker([
                    JSONWalker(v, parent=self, parent_key=i)
                    for i, v in enumerate(self.data)
                ])
        # ANY DICT ITEM
        elif key is str:
            if isinstance(self.data, dict):
                return JSONSplitWalker([
                    JSONWalker(v, parent=self, parent_key=k)
                    for k, v in self.data.items()
                ])
        # REGEX DICT ITEM
        elif isinstance(key, str):
            if isinstance(self.data, dict):
                result: list[JSONWalker] = []
                for k, v in self.data.items():
                    if re.fullmatch(key, k):
                        result.append(JSONWalker(
                            v, parent=self, parent_key=k))
                return JSONSplitWalker(result)
        # IF it's a list use ing key ELSE return split walker with self
        elif key is SKIP_LIST:
            if isinstance(self.data, list):
                return self // int
            return JSONSplitWalker([self])
        else:  # INVALID KEY TYPE
            raise TypeError(
                'Key must be a regular expression or one of the values: '
                'str, int, or None')
        # DATA DOESN'T ACCEPT THIS TYPE OF KEY
        return JSONSplitWalker([])

    def __add__(self, other: Union[JSONSplitWalker, JSONWalker]) -> JSONSplitWalker:
        '''
        Combine with :class:`JSONWalker` or  :class:`JSONSplitWalker`
        object to create :class:`JSONSplitWalker`.
        '''
        if isinstance(other, JSONWalker):
            data = [self, other]
        else:
            data = other.data + [self]
        return JSONSplitWalker(
            [i for i in data if not isinstance(i.data, Exception)])


class JSONSplitWalker:
    '''
    Multiple :class:`JSONWalker` objects grouped together. This class can be
    browse JSON file in multiple places at once.
    '''

    def __init__(self, data: list[JSONWalker]) -> None:
        self._data: list[JSONWalker] = data

    @property
    def data(self) -> list[JSONWalker]:
        '''
        The list of the :class:`JSONWalker` objects contained in this
            :class:`JSONSplitWalker`.
        '''
        return self._data

    def __truediv__(self, key: JSON_KEY) -> JSONSplitWalker:
        '''
        Execute :code:`__truediv__(key)` of every :class:`JSONWalker` of this
        object and return new :class:`JSONSplitWalker` that contains only
        thouse of the newly created :class:`JSONWalker` objects that represent
        valid JSON path.

        :param key: a json key (list index or object field name)
        '''
        result = []
        for walker in self.data:
            new_walker = walker / key
            if not isinstance(new_walker.data, Exception):
                result.append(new_walker)
        return JSONSplitWalker(result)

    def __floordiv__(self, key: JSON_SPLIT_KEY) -> JSONSplitWalker:
        '''
        Execute :code:`__floordiv__(key)` of every :class:`JSONWalker` of this
        object and return new :class:`JSONSplitWalker` which combines all of
        the results.

        :param key: a json key (list index or object field name)
        '''
        result: list[JSONWalker] = []
        for walker in self.data:
            new_walker = walker // key
            result.extend(new_walker.data)
        return JSONSplitWalker(result)

    def __add__(self, other: Union[JSONSplitWalker, JSONWalker]) -> JSONSplitWalker:
        '''
        Combine with :class:`JSONWalker` or  another :class:`JSONSplitWalker`
        object.
        '''
        if isinstance(other, JSONWalker):
            data = self.data + [other]
        else:
            data = self.data + other.data
        return JSONSplitWalker(
            [i for i in data if not isinstance(i.data, Exception)])

    def __iter__(self) -> Iterator[JSONWalker]:
        '''
        Yield every :class:`JSONWalker` contained in this object.
        '''
        for i in self.data:
            yield i

