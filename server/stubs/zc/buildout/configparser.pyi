from _typeshed import Incomplete

Marker: Incomplete
InvalidMarker: Incomplete
logger: Incomplete

class Error(Exception):
    message: Incomplete
    def __init__(self, msg: str = '') -> None: ...

class ParsingError(Error):
    filename: Incomplete
    errors: Incomplete
    def __init__(self, filename) -> None: ...
    def append(self, lineno, line) -> None: ...

class MissingSectionHeaderError(ParsingError):
    filename: Incomplete
    lineno: Incomplete
    line: Incomplete
    def __init__(self, filename, lineno, line) -> None: ...

section_header: Incomplete
option_start: Incomplete
leading_blank_lines: Incomplete

def parse(fp, fpname, exp_globals=...): ...
