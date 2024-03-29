import zc.buildout.download
from collections.abc import MutableMapping as DictMixin
from typing import Any, Optional, Dict, Tuple, Union
from zc.buildout.rmtree import rmtree as rmtree

PY3: Any
text_type = str

def command(method: Any): ...
def commands(cls): ...
def print_(*args: Any, **kw: Any) -> None: ...

realpath: Any

DefaultOptionBuildout292 =  Dict[str, Tuple[str, str]]
DefaultOptionBuildoutCurrent =  Dict[str, SectionKey]

_buildout_default_options: Union[DefaultOptionBuildout292, DefaultOptionBuildoutCurrent]

class MissingOption(zc.buildout.UserError, KeyError): ...
class MissingSection(zc.buildout.UserError, KeyError): ...

class SectionKey:
    history: Any = ...
    value: Any = ...
    lineno: int = ...
    def __init__(self, value: Any, source: Any) -> None: ...
    @property
    def source(self): ...
    def overrideValue(self, sectionkey: Any) -> None: ...
    def setDirectory(self, value: Any) -> None: ...
    def addToValue(self, added: Any, source: Any) -> None: ...
    def removeFromValue(self, removed: Any, source: Any) -> None: ...
    def addToHistory(self, operation: Any, value: Any, source: Any) -> None: ...
    def printAll(self, key: Any, basedir: Any, verbose: Any) -> None: ...
    def printKeyAndValue(self, key: Any) -> None: ...
    def printVerbose(self, basedir: Any) -> None: ...
    def printTerse(self, basedir: Any) -> None: ...

class HistoryItem:
    operation: Any = ...
    value: Any = ...
    source: Any = ...
    def __init__(self, operation: Any, value: Any, source: Any) -> None: ...
    def printShort(self, toprint: Any, basedir: Any) -> None: ...
    def printOperation(self) -> None: ...
    def printSource(self, basedir: Any) -> None: ...
    def source_for_human(self, basedir: Any): ...
    def printAll(self, basedir: Any) -> None: ...

class Buildout(DictMixin):
    COMMANDS: Any = ...
    offline: Any = ...
    newest: Any = ...
    versions: Any = ...
    show_picked_versions: Any = ...
    update_versions_file: Any = ...
    def __init__(self, config_file: Any, cloptions: Any, user_defaults: bool = ..., command: Optional[Any] = ..., args: Any = ...) -> None: ...
    def bootstrap(self, args: Any) -> None: ...
    def init(self, args: Any) -> None: ...
    def install(self, install_args: Any) -> None: ...
    def setup(self, args: Any) -> None: ...
    def runsetup(self, args: Any) -> None: ...
    def query(self, args: Optional[Any] = ...) -> None: ...
    def annotate(self, args: Optional[Any] = ...) -> None: ...
    def print_options(self, base_path: Optional[Any] = ...) -> None: ...
    def __getitem__(self, section: Any): ...
    def __setitem__(self, name: Any, data: Any) -> None: ...
    def parse(self, data: Any) -> None: ...
    def __delitem__(self, key: Any) -> None: ...
    def keys(self): ...
    def __iter__(self) -> Any: ...
    def __len__(self): ...

class Options(DictMixin):
    buildout: Any = ...
    name: Any = ...
    def __init__(self, buildout: Any, section: Any, data: Any) -> None: ...
    recipe: Any = ...
    def initialize(self) -> None: ...
    def get(self, option: Any, default: Optional[Any] = ..., seen: Optional[Any] = ...): ...
    def __getitem__(self, key: Any): ...
    def __setitem__(self, option: Any, value: Any) -> None: ...
    def __delitem__(self, key: Any) -> None: ...
    def keys(self): ...
    def __iter__(self) -> Any: ...
    def __len__(self): ...
    def copy(self): ...
    def created(self, *paths: Any): ...

ignore_directories: Any

def main(args: Optional[Any] = ...) -> None: ...
def bool_option(options: Any, name: Any, default: Optional[Any] = ...): ...
