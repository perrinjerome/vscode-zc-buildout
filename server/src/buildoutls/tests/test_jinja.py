from ..jinja import JinjaParser


def test_is_in_jinja() -> None:
  parser = JinjaParser()
  for line, is_in_jinja in (
    ("", False),
    ("not jinja", False),
    ("not { jinja", False),
    ("not ${jinja", False),
    # expressions
    ("{{ jinja }}", False),
    ("[section{{ jinja }}]", False),
    ("key = {{ jinja }}", False),
    # one line statements
    ("{% set something = True %}", True),
    ("{% do 1 + 1 %}", True),
    ("{%- do 1 + 1 %}", True),
    ("{% do 1 + 1 -%}", True),
    # multi line statements
    ("{% do ", True),
    (" 1 + 1 ", True),
    (" %}", True),
    # block statements
    # for
    ("{% for i in list() %}", True),
    ("  jinja context", True),
    ("{% endfor %}", True),
    (" out of block", False),
    # if
    ("{% if False %}", True),
    ("  jinja context", True),
    ("{% elif False %}", True),
    ("  jinja context", True),
    ("{% else False %}", True),
    ("  jinja context", True),
    ("{% endif %}", True),
    (" out of block", False),
    # macro
    ("{% macro m %}", True),
    ("  jinja context", True),
    ("{% endmacro %}", True),
    (" out of block", False),
    # call
    ("{% call m %}", True),
    ("  jinja context", True),
    ("{% endcall %}", True),
    (" out of block", False),
    # filter
    ("{% filter m %}", True),
    ("  jinja context", True),
    ("{% endfilter %}", True),
    (" out of block", False),
    # blocks with - or +
    ("{%- for i in list() %}", True),
    ("  jinja context", True),
    ("{%+ endfor %}", True),
    (" out of block", False),
    # nested blocks
    ("{% for i in list() %}", True),
    ("{%  if False %}", True),
    ("      jinja context", True),
    ("{%  endif %}", True),
    ("    jinja context", True),
    ("{% endfor %}", True),
    (" out of block", False),
    # multi line expressions
    ("{{ ", True),
    (" multi ", True),
    (" line ", True),
    ("}}", True),
    ("{{multi ", True),
    (" line}}", True),
    # comments
    ("{# one line comment #}", True),
    ("after comment", False),
    ("{# multi ", True),
    ("line ", True),
    ("comment #}", True),
    ("after multi line comment", False),
    # raw
    ("{% raw %}", True),
    ("in raw", False),
    ("{% set jinja_ignored_in_raw = True %}", False),
    ("{% endraw %}", True),
    ("{% set jinja_detected_after_in_raw = True %}", True),
  ):
    parser.feed(line)
    assert parser.is_in_jinja == is_in_jinja
    assert not parser.is_error


def test_jinja_error() -> None:
  parser = JinjaParser()
  for line, is_error in (
    # mismatched end of block
    ("{% for i in list() %}", False),
    ("  jinja context", False),
    ("{% endfilter %}", True),
    (" out of block", False),
    # unexpected end of block
    ("{% endmacro %}", True),
    # no statement
    ("{%  %}", False),
    # unknown statement
    ("{% unknown %}", False),
  ):
    parser.feed(line)
    assert parser.is_error == is_error
