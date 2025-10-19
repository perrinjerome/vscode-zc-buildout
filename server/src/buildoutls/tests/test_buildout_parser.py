import io
import textwrap
from typing import List
from unittest import mock

import pytest
import aioresponses
from aiohttp.client_exceptions import ClientConnectionError
from lsprotocol.types import Location, Position, Range
from pygls.lsp.server import LanguageServer


from ..buildout import (
  BuildoutProfile,
  BuildoutTemplate,
  RecursiveIncludeError,
  Symbol,
  SymbolKind,
  clearCache,
  _parse,
  open,
)


## parse tests
async def test_parse() -> None:
  parsed = await _parse(
    fp=io.StringIO(
      textwrap.dedent("""\
                [s1]
                opt1 = value1
                opt2 = value2
                [s2]
                opt3 =
                    multi
                    line
                [s1]
                opt2 = value2bis
                """)
    ),
    uri="file:///buildout.cfg",
    allow_errors=False,
  )
  assert list(parsed.keys()) == ["buildout", "s1", "s2"]
  assert sorted(parsed["s1"].keys()) == [
    "_buildout_section_name_",
    "_profile_base_location_",
    "opt1",
    "opt2",
  ]
  assert sorted(parsed["s2"].keys()) == [
    "_buildout_section_name_",
    "_profile_base_location_",
    "opt3",
  ]

  assert parsed["s1"]["opt1"].value == "value1"
  assert parsed["s1"]["opt2"].value == "value2bis"
  assert parsed["s2"]["opt3"].value == "multi\nline"

  assert parsed["s1"]["opt1"].locations == (
    Location(
      uri="file:///buildout.cfg",
      range=Range(
        start=Position(line=1, character=6),
        end=Position(line=1, character=13),
      ),
    ),
  )
  assert parsed["s1"]["opt2"].locations == (
    Location(
      uri="file:///buildout.cfg",
      range=Range(
        start=Position(line=2, character=6),
        end=Position(line=2, character=13),
      ),
    ),
    Location(
      uri="file:///buildout.cfg",
      range=Range(
        start=Position(line=8, character=6),
        end=Position(line=8, character=16),
      ),
    ),
  )
  assert parsed["s2"]["opt3"].locations == (
    Location(
      uri="file:///buildout.cfg",
      range=Range(
        start=Position(line=4, character=6),
        end=Position(line=6, character=8),
      ),
    ),
  )
  # section headers ranges are properties of buildout
  assert list(parsed.section_header_locations.items()) == [
    (
      "buildout",
      Location(
        uri="",
        range=Range(
          start=Position(line=0, character=0), end=Position(line=0, character=0)
        ),
      ),
    ),
    (
      "s1",
      Location(
        uri="file:///buildout.cfg",
        # we only have the last range
        range=Range(
          start=Position(line=7, character=0), end=Position(line=8, character=0)
        ),
      ),
    ),
    (
      "s2",
      Location(
        uri="file:///buildout.cfg",
        range=Range(
          start=Position(line=3, character=0), end=Position(line=4, character=0)
        ),
      ),
    ),
  ]
  assert not parsed.has_jinja


async def test_parse_jinja_option() -> None:
  parsed = await _parse(
    fp=io.StringIO(
      textwrap.dedent("""\
                [section]
                option = {{ jinja_expression }}
                {# ignored #}
                {% jinja_key = value %}
                {{ jinja_expression }} = value

                [section{{ jinja_expression }}]
                option = value

                [another_section]
                {{ jinja_expression }} = {{ jinja_expression }}
                """)
    ),
    uri="file:///buildout.cfg",
    allow_errors=False,
  )
  assert list(parsed.keys()) == [
    "buildout",
    "section",
    "sectionJINJA_EXPRESSION",
    "another_section",
  ]
  assert sorted(parsed["section"].keys()) == [
    "JINJA_EXPRESSION",
    "_buildout_section_name_",
    "_profile_base_location_",
    "option",
  ]
  assert parsed["section"]["option"].value == "JINJA_EXPRESSION"
  assert parsed["section"]["JINJA_EXPRESSION"].value == "value"
  assert parsed["sectionJINJA_EXPRESSION"]["option"].value == "value"
  assert parsed["another_section"]["JINJA_EXPRESSION"].value == "JINJA_EXPRESSION"
  assert parsed.has_jinja


async def test_BuildoutProfile_getSymbolAtPosition_BuildoutOptionKey(
  buildout: BuildoutProfile,
) -> None:
  for pos in (
    Position(line=5, character=3),
    Position(line=5, character=0),
    Position(line=5, character=7),
  ):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.BuildoutOptionKey
    assert symbol.value == "command"
    assert symbol.current_section_name == "section1"
    assert symbol.current_option_name == "command"

  for pos in (Position(line=22, character=1), Position(line=22, character=0)):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.BuildoutOptionKey
    assert symbol.value == "op"
    assert symbol.current_section_name == "section4"
    assert symbol.current_option_name == "op"

  # an empty line is a buildout option key
  for pos in (Position(line=6, character=0),):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.BuildoutOptionKey
    assert symbol.value == ""
    assert symbol.current_section_name == "section1"
    assert symbol.current_option_name == ""


async def test_BuildoutProfile_getSymbolAtPosition_BuildoutOptionValue(
  buildout: BuildoutProfile,
) -> None:
  for pos in (
    Position(line=5, character=11),
    Position(line=5, character=10),
    Position(line=5, character=24),
  ):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.BuildoutOptionValue
    assert symbol.value == "echo install section1"
    assert symbol.current_section_name == "section1"
    assert symbol.current_option_name == "command"

  for pos in (
    Position(line=17, character=5),
    Position(line=17, character=0),
    Position(line=17, character=4),
    Position(line=17, character=10),
  ):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.BuildoutOptionValue
    assert (
      symbol.value == "value2"
    )  # in a multi line option, value is only the current line
    assert symbol.current_section_name == "section3"
    assert symbol.current_option_name == "multi_line_option"


async def test_BuildoutProfile_getSymbolAtPosition_SectionReference(
  buildout: BuildoutProfile,
) -> None:
  for pos in (
    Position(line=13, character=14),
    Position(line=13, character=12),
    Position(line=13, character=20),
  ):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.SectionReference
    assert symbol.current_section_name == "section3"
    assert symbol.current_option_name == "command"
    assert symbol.referenced_section_name == "section1"
    assert symbol.referenced_section is not None
    assert symbol.referenced_section["command"].value == "echo install section1"
    assert symbol.referenced_section_recipe is not None
    assert symbol.referenced_section_recipe.name == "plone.recipe.command"
    assert symbol.referenced_option is not None

  for pos in (
    Position(line=13, character=34),
    Position(line=13, character=32),
    Position(line=13, character=40),
  ):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.SectionReference
    assert symbol.referenced_section_name == "section2"

  for pos in (Position(line=14, character=34), Position(line=14, character=37)):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.SectionReference
    assert symbol.current_section_name == "section3"
    assert symbol.current_option_name == "option_with_section_reference"
    assert symbol.referenced_section_name == "section1"
    assert symbol.referenced_section is not None
    assert symbol.referenced_section["command"].value == "echo install section1"
    assert symbol.referenced_section_recipe is not None
    assert symbol.referenced_section_recipe.name == "plone.recipe.command"

  # multi-line option
  for pos in (
    Position(line=18, character=10),
    Position(line=18, character=7),
    Position(line=18, character=14),
  ):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.SectionReference
    assert symbol.current_section_name == "section3"
    assert symbol.current_option_name == "multi_line_option"
    assert symbol.referenced_section_name == "section1"
    assert symbol.referenced_section is not None
    assert symbol.referenced_section["command"].value == "echo install section1"
    assert symbol.referenced_section_recipe is not None
    assert symbol.referenced_section_recipe.name == "plone.recipe.command"


async def test_BuildoutProfile_getSymbolAtPosition_OptionReference(
  buildout: BuildoutProfile,
) -> None:
  for pos in (
    Position(line=13, character=23),
    Position(line=13, character=21),
    Position(line=13, character=28),
  ):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.OptionReference
    assert symbol.referenced_section_name == "section1"
    assert symbol.referenced_option_name == "command"
    assert symbol.referenced_option is not None
    assert symbol.referenced_option.value == "echo install section1"
    assert symbol.referenced_section_recipe is not None
    assert symbol.referenced_section_recipe.name == "plone.recipe.command"

  # two on same line
  for pos in (
    Position(line=13, character=43),
    Position(line=13, character=41),
    Position(line=13, character=48),
  ):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.OptionReference
    assert symbol.referenced_section_name == "section2"
    assert symbol.referenced_option_name == "command"
    assert symbol.referenced_option is not None
    assert symbol.referenced_option.value == "echo install section2"

  # empty section ${:option}
  symbol = await buildout.getSymbolAtPosition(Position(line=27, character=14))
  assert symbol is not None
  assert symbol.kind == SymbolKind.OptionReference
  assert symbol.referenced_section_name == "section5"
  assert symbol.referenced_option_name == "command"
  assert symbol.referenced_option is not None
  assert symbol.referenced_option.value == "echo install section5"


async def test_BuildoutProfile_getSymbolAtPosition_SectionDefinition(
  buildout: BuildoutProfile,
) -> None:
  for pos in (
    Position(line=3, character=1),
    Position(line=3, character=0),
    Position(line=3, character=10),
  ):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.SectionDefinition
    assert symbol.current_section_name == "section1"


async def test_BuildoutProfile_getSymbolAtPosition_Comment(
  buildout: BuildoutProfile,
) -> None:
  for pos in (
    Position(line=34, character=2),
    Position(line=34, character=10),
    Position(line=34, character=21),
    Position(line=34, character=28),
    Position(line=35, character=17),
    Position(line=35, character=20),
  ):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.Comment
    assert symbol.referenced_section is None
    assert symbol.referenced_option_name is None
    assert symbol.referenced_option is None

  # symbols with comments on same line
  symbol = await buildout.getSymbolAtPosition(Position(line=35, character=2))
  assert symbol is not None
  assert symbol.kind == SymbolKind.BuildoutOptionKey
  assert symbol.value == "option"

  symbol = await buildout.getSymbolAtPosition(Position(line=35, character=11))
  assert symbol is not None
  assert symbol.kind == SymbolKind.BuildoutOptionValue
  assert symbol.value == "value # we can have comments after options"


async def test_BuildoutProfile_getAllOptionReferenceSymbols(
  buildout: BuildoutProfile,
) -> None:
  symbols: List[Symbol] = []
  async for symbol in buildout.getAllOptionReferenceSymbols():
    symbols.append(symbol)
  assert [
    (
      s.referenced_section_name,
      s.referenced_option_name,
      s.referenced_section is not None,
      s.referenced_option is not None,
    )
    for s in symbols
  ] == [
    ("section1", "command", True, True),
    ("section2", "command", True, True),
    ("section1", "command", True, True),
    # this is ${:command} in the source, but this had been expanded
    ("section5", "command", True, True),
    ("section7", "circular2", True, True),
    ("section7", "circular1", True, True),
    ("section8", "recursive2", True, True),
    ("section8", "recursive3", True, True),
    ("not-exists", "not-exists", False, False),
    ("section10", "not-exists", True, False),
  ]

  assert {s.current_section_name for s in symbols} == {None}
  assert {s.kind for s in symbols} == {SymbolKind.OptionReference}


async def test_BuildoutProfile_getTemplate(
  buildout: BuildoutProfile,
  server: LanguageServer,
) -> None:
  assert await buildout.getTemplate(server, "template.in") is not None
  assert await buildout.getTemplate(server, "file:///template.in") is not None
  assert await buildout.getTemplate(server, "not exists") is None


async def test_BuildoutTemplate_getSymbolAtPosition_SectionReference(
  template: BuildoutTemplate,
) -> None:
  for pos in (
    Position(line=2, character=24),
    Position(line=2, character=22),
    Position(line=2, character=30),
  ):
    symbol = await template.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.SectionReference
    assert symbol.referenced_section_name == "section5"
    assert symbol.referenced_section is not None
    assert "command" in symbol.referenced_section
    assert symbol.referenced_section_recipe is not None
  for pos in (
    Position(line=2, character=46),
    Position(line=2, character=45),
    Position(line=2, character=53),
  ):
    symbol = await template.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.SectionReference
    assert symbol.referenced_section_name == "section5"
    assert symbol.referenced_section is not None
    assert "command" in symbol.referenced_section
    assert symbol.referenced_section_recipe is not None


async def test_BuildoutTemplate_getSymbolAtPosition_OptionReference(
  template: BuildoutTemplate,
) -> None:
  for pos in (
    Position(line=2, character=34),
    Position(line=2, character=31),
    Position(line=2, character=38),
  ):
    symbol = await template.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.OptionReference
    assert symbol.referenced_section is not None
    assert symbol.referenced_option_name == "command"
    assert symbol.referenced_option is not None
    assert symbol.referenced_option.value == "echo install section5"

  for pos in (
    Position(line=2, character=56),
    Position(line=2, character=54),
    Position(line=2, character=60),
  ):
    symbol = await template.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.OptionReference
    assert symbol.referenced_section is not None
    assert symbol.referenced_option_name == "option"
    assert symbol.referenced_option is not None
    assert symbol.referenced_option.value == "${:command}"


async def test_BuildoutTemplate_getSymbolAtPosition_None(
  template: BuildoutTemplate,
) -> None:
  for pos in (
    Position(line=0, character=0),
    Position(line=4, character=11),
    Position(line=6, character=60),
  ):
    symbol = await template.getSymbolAtPosition(pos)
    assert symbol is None


async def test_BuildoutTemplate_getAllOptionReferenceSymbols(
  template: BuildoutTemplate,
) -> None:
  symbols: List[Symbol] = []
  async for symbol in template.getAllOptionReferenceSymbols():
    symbols.append(symbol)

  assert [(s.referenced_section_name, s.referenced_option_name) for s in symbols] == [
    ("buildout", "directory"),
    ("section5", "command"),
    ("section5", "option"),
    ("missing", "option"),
    ("section5", "missing_option"),
  ]
  assert [
    (s.referenced_section is not None, s.referenced_option is not None) for s in symbols
  ] == [
    (True, True),
    (True, True),
    (True, True),
    (False, False),
    (True, False),
  ]
  assert {s.current_section_name for s in symbols} == {None}
  assert {s.kind for s in symbols} == {SymbolKind.OptionReference}


async def test_getOptionValues(server: LanguageServer):
  parsed = await open(
    ls=server,
    uri="file:///option_values/buildout.cfg",
  )
  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.getOptionValues("multi_line", "option")) == [
    (
      "first line",
      Range(start=Position(line=2, character=2), end=Position(line=2, character=12)),
    ),
    (
      "second line",
      Range(start=Position(line=3, character=2), end=Position(line=3, character=13)),
    ),
  ]
  assert list(parsed.getOptionValues("simple_line", "option")) == [
    (
      "first",
      Range(start=Position(line=6, character=9), end=Position(line=6, character=14)),
    ),
    (
      "second",
      Range(start=Position(line=6, character=15), end=Position(line=6, character=21)),
    ),
  ]


async def test_open_extends(server: LanguageServer):
  parsed = await open(
    ls=server,
    uri="file:///extended/buildout.cfg",
  )
  assert isinstance(parsed, BuildoutProfile)
  assert parsed.uri == "file:///extended/buildout.cfg"
  # options are replaced
  assert (
    parsed["overloaded_from_another_buildout"]["option"].value
    == "this is overloaded in extended/extended.cfg"
  )
  assert parsed["overloaded_from_another_buildout"]["option"].locations == (
    Location(
      uri="file:///extended/extended.cfg",
      range=Range(
        start=Position(line=7, character=8), end=Position(line=7, character=52)
      ),
    ),
    Location(
      uri="file:///extended/another/buildout.cfg",
      range=Range(
        start=Position(line=8, character=8), end=Position(line=8, character=78)
      ),
    ),
    # here we have a "cycle", because extended/another/buildout.cfg
    # extends ./extended/buildout.cfg again
    Location(
      uri="file:///extended/extended.cfg",
      range=Range(
        start=Position(line=7, character=8), end=Position(line=7, character=52)
      ),
    ),
  )
  assert parsed["overloaded_from_another_buildout"]["option"].values == (
    "this is overloaded in extended/extended.cfg",
    "this is from extended/another/buildout.cfg but it should be overloaded",
    "this is overloaded in extended/extended.cfg",
  )

  # options are mixed in the same section
  assert (
    parsed["merged_section"]["kept_option"].value
    == "this is from extended/another/buildout.cfg"
  )
  assert parsed["merged_section"]["kept_option"].locations == (
    Location(
      uri="file:///extended/another/buildout.cfg",
      range=Range(
        start=Position(line=5, character=13), end=Position(line=5, character=56)
      ),
    ),
  )
  assert parsed["merged_section"]["kept_option"].values == (
    "this is from extended/another/buildout.cfg",
  )

  assert (
    parsed["merged_section"]["overloaded_option"].value == "from extended/buildout.cfg"
  )
  assert parsed["merged_section"]["overloaded_option"].locations == (
    Location(
      uri="file:///extended/another/buildout.cfg",
      range=Range(
        start=Position(line=4, character=19), end=Position(line=4, character=68)
      ),
    ),
    Location(
      uri="file:///extended/buildout.cfg",
      range=Range(
        start=Position(line=6, character=19), end=Position(line=6, character=46)
      ),
    ),
  )
  assert parsed["merged_section"]["overloaded_option"].values == (
    "this will be overloaded in extended/buildout.cfg",
    "from extended/buildout.cfg",
  )

  # options are extended with +=
  assert (
    parsed["extended_option"]["option"].value
    == "option from extended/extended.cfg\nthen extended in extended/buildout.cfg"
  )
  assert parsed["extended_option"]["option"].locations == (
    Location(
      uri="file:///extended/extended.cfg",
      range=Range(
        start=Position(line=1, character=8), end=Position(line=1, character=42)
      ),
    ),
    Location(
      uri="file:///extended/buildout.cfg",
      range=Range(
        start=Position(line=9, character=9), end=Position(line=9, character=48)
      ),
    ),
  )
  assert parsed["extended_option"]["option"].values == (
    "option from extended/extended.cfg",
    "option from extended/extended.cfg\nthen extended in extended/buildout.cfg",
  )

  assert "option +" not in parsed["extended_option"]

  # this works also for multi lines options
  assert (
    parsed["extended_option"]["mutli_line_option"].value == "value1\nvalue2\nvalue3"
  )
  assert parsed["extended_option"]["mutli_line_option"].locations == (
    Location(
      uri="file:///extended/extended.cfg",
      range=Range(
        start=Position(line=2, character=19), end=Position(line=5, character=0)
      ),
    ),
    Location(
      uri="file:///extended/buildout.cfg",
      range=Range(
        start=Position(line=10, character=20), end=Position(line=12, character=0)
      ),
    ),
  )
  assert parsed["extended_option"]["mutli_line_option"].values == (
    "value1\nvalue2",
    "value1\nvalue2\nvalue3",
  )
  assert "mutli_line_option +" not in parsed["extended_option"]

  # options can be removed with -=
  assert parsed["reduced_option"]["option"].value == "value1\nvalue3"
  assert parsed["reduced_option"]["option"].locations == (
    Location(
      uri="file:///extended/extended.cfg",
      range=Range(
        start=Position(line=10, character=8), end=Position(line=13, character=9)
      ),
    ),
    Location(
      uri="file:///extended/buildout.cfg",
      range=Range(
        start=Position(line=14, character=9), end=Position(line=15, character=9)
      ),
    ),
  )
  assert parsed["reduced_option"]["option"].values == (
    "value1\nvalue2\nvalue3",
    "value1\nvalue3",
  )
  assert "option -" not in parsed["reduced_option"]


async def test_open_extends_buildout_default_options(server: LanguageServer):
  parsed = await open(
    ls=server, uri="file:///extended/default_buildout_options/buildout.cfg"
  )
  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.keys()) == ["buildout"]
  assert parsed["buildout"]["bin-directory"].value == "different-default-value"
  assert parsed["buildout"]["bin-directory"].locations == (
    Location(
      uri="file:///extended/default_buildout_options/extended.cfg",
      range=Range(
        start=Position(line=0, character=0),
        end=Position(line=0, character=0),
      ),
    ),
    Location(
      uri="file:///extended/default_buildout_options/extended.cfg",
      range=Range(
        start=Position(line=1, character=15),
        end=Position(line=1, character=39),
      ),
    ),
  )
  assert parsed["buildout"]["allow-hosts"].value == "extended-default-value"
  assert parsed["buildout"]["allow-hosts"].locations == (
    Location(
      uri="file:///extended/default_buildout_options/buildout.cfg",
      range=Range(
        start=Position(line=0, character=0),
        end=Position(line=0, character=0),
      ),
    ),
    Location(
      uri="file:///extended/default_buildout_options/buildout.cfg",
      range=Range(
        start=Position(line=2, character=14),
        end=Position(line=2, character=37),
      ),
    ),
  )


async def test_open_extends_file_not_found(server: LanguageServer):
  with pytest.raises(FileNotFoundError):
    await open(
      ls=server,
      uri="file:///extended/broken/file_not_found.cfg",
      allow_errors=False,
    )
  parsed = await open(ls=server, uri="file:///extended/broken/file_not_found.cfg")
  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.keys()) == ["buildout", "section"]


async def test_open_extends_empty_extends(server: LanguageServer):
  parsed = await open(ls=server, uri="file:///extended/broken/empty_extends.cfg")
  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.keys()) == ["buildout", "section"]


async def test_open_extends_loop(server: LanguageServer):
  with pytest.raises(RecursiveIncludeError):
    await open(ls=server, uri="file:///extended/broken/loop.cfg", allow_errors=False)
  parsed = await open(ls=server, uri="file:///extended/broken/loop.cfg")
  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.keys()) == ["buildout", "section"]


async def test_open_extends_getSymbolAtPosition(server: LanguageServer):
  parsed = await open(ls=server, uri="file:///extended/buildout.cfg")
  assert isinstance(parsed, BuildoutProfile)
  overloaded_option = await parsed.getSymbolAtPosition(Position(line=6, character=6))
  assert overloaded_option is not None
  assert overloaded_option.kind == SymbolKind.BuildoutOptionKey
  assert overloaded_option.current_section_name == "merged_section"
  assert overloaded_option.current_option_name == "overloaded_option"

  overloaded_option_value = await parsed.getSymbolAtPosition(
    Position(line=6, character=26)
  )
  assert overloaded_option_value is not None
  assert overloaded_option_value.kind == SymbolKind.BuildoutOptionValue
  assert overloaded_option_value.current_section_name == "merged_section"
  assert overloaded_option_value.current_option_name == "overloaded_option"
  assert overloaded_option_value.value == "from extended/buildout.cfg"


async def test_open_extends_section_header_locations(server: LanguageServer):
  parsed = await open(ls=server, uri="file:///extended/buildout.cfg")
  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.section_header_locations.items()) == [
    (
      "buildout",
      Location(
        uri="file:///extended/buildout.cfg",
        range=Range(
          start=Position(line=0, character=0), end=Position(line=1, character=0)
        ),
      ),
    ),
    (
      "extended_option",
      Location(
        uri="file:///extended/buildout.cfg",
        range=Range(
          start=Position(line=8, character=0), end=Position(line=9, character=0)
        ),
      ),
    ),
    (
      "overloaded_from_another_buildout",
      Location(
        uri="file:///extended/extended.cfg",
        range=Range(
          start=Position(line=6, character=0), end=Position(line=7, character=0)
        ),
      ),
    ),
    (
      "reduced_option",
      Location(
        uri="file:///extended/buildout.cfg",
        range=Range(
          start=Position(line=13, character=0), end=Position(line=14, character=0)
        ),
      ),
    ),
    (
      "merged_section",
      Location(
        uri="file:///extended/buildout.cfg",
        range=Range(
          start=Position(line=5, character=0), end=Position(line=6, character=0)
        ),
      ),
    ),
  ]


async def test_open_extends_cache(server: LanguageServer):
  await open(
    ls=server,
    uri="file:///extended/buildout.cfg",
  )
  # check the cache is effective, the same file is included twice,
  # but we load it only once.
  assert server.workspace.get_text_document.call_count == 4  # type: ignore


async def test_open_extends_cache_clear(server: LanguageServer):
  parsed = await open(
    ls=server,
    uri="file:///extended/two_levels.cfg",
  )
  assert parsed is not None
  symbol = await parsed.getSymbolAtPosition(Position(line=6, character=30))
  assert symbol is not None
  assert symbol.referenced_section is not None
  assert "option" in symbol.referenced_section

  clearCache("file:///extended/extended.cfg")
  original_get_text_document = server.workspace.get_text_document

  def getModifiedDocument(uri: str):
    doc = original_get_text_document(uri)
    if uri == "file:///extended/extended.cfg":
      doc._source = textwrap.dedent("""\
          [extended_option]
          new_option = after modification
          """)
    return doc

  with mock.patch.object(
    server.workspace,
    "get_text_document",
    side_effect=getModifiedDocument,
  ):
    parsed = await open(
      ls=server,
      uri="file:///extended/two_levels.cfg",
    )
    assert parsed is not None
    symbol = await parsed.getSymbolAtPosition(Position(line=6, character=30))
    assert symbol is not None
    assert symbol.referenced_section is not None
    assert "new_option" in symbol.referenced_section
    assert "option" in symbol.referenced_section


async def test_open_resolved_cache_clear(server: LanguageServer):
  with mock.patch.object(
    server.workspace,
    "get_text_document",
    wraps=server.workspace.get_text_document,
  ) as get_text_document_initial:
    parsed = await open(
      ls=server,
      uri="file:///extended/two_levels.cfg",
    )
    assert parsed is not None
    symbol = await parsed.getSymbolAtPosition(Position(line=6, character=30))
    assert symbol is not None
    assert symbol.referenced_section is not None
    assert "option" in symbol.referenced_section
  assert (
    mock.call("file:///extended/extended.cfg") in get_text_document_initial.mock_calls
  )

  clearCache("file:///extended/two_levels.cfg")

  with mock.patch.object(
    server.workspace,
    "get_text_document",
    wraps=server.workspace.get_text_document,
  ) as get_text_document_after_clear_cache:
    parsed = await open(
      ls=server,
      uri="file:///extended/two_levels.cfg",
    )
    assert parsed is not None
    symbol = await parsed.getSymbolAtPosition(Position(line=6, character=30))
    assert symbol is not None
    assert symbol.referenced_section is not None
    assert "option" in symbol.referenced_section
  assert (
    mock.call("file:///extended/two_levels.cfg")
    in get_text_document_after_clear_cache.mock_calls
  )
  assert (
    mock.call("file:///extended/extended.cfg")
    not in get_text_document_after_clear_cache.mock_calls
  )


async def test_open_macro(server: LanguageServer):
  parsed = await open(ls=server, uri="file:///extended/macros/buildout.cfg")
  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.keys()) == ["buildout", "macro1", "macro2", "macro_user"]
  assert parsed["macro_user"]["option1"].value == "value1"
  assert parsed["macro_user"]["option2"].value == "value2"
  assert parsed["macro_user"]["option3"].value == "value3"
  assert "<" not in parsed["macro_user"]


async def test_open_extends_network(
  server: LanguageServer, mocked_responses: aioresponses.aioresponses
):
  mocked_responses.get(
    "https://example.com/profiles/buildout.cfg",
    body=textwrap.dedent("""\
        [buildout]
        extends = ./other.cfg
        """),
  )
  mocked_responses.get(
    "https://example.com/profiles/other.cfg",
    body=textwrap.dedent("""\
        [section]
        option = value
        """),
  )

  parsed = await open(
    ls=server,
    uri="file:///extended/network.cfg",
    allow_errors=False,
  )

  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.keys()) == ["buildout", "section"]
  assert parsed["section"]["option"].value == "value"


async def test_open_extends_network_fail(
  server: LanguageServer, mocked_responses: aioresponses.aioresponses
):
  mocked_responses.get(
    "https://example.com/profiles/buildout.cfg", exception=ClientConnectionError()
  )

  parsed = await open(
    ls=server,
    uri="file:///extended/network.cfg",
    allow_errors=False,
  )

  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.keys()) == ["buildout"]


async def test_BuildoutProfile_resolve_value(buildout: BuildoutProfile) -> None:
  assert buildout.resolve_value("section5", "option") == "echo install section5"
  assert (
    buildout.resolve_value("section3", "command")
    == "echo install section1 echo install section2"
  )
  assert buildout.resolve_value("section7", "recursive1") == "recursive value"
  assert buildout.resolve_value("section9", "option") == "echo install section9"

  # error cases
  assert (
    buildout.resolve_value("section3", "option_with_section_reference") == "${section1"
  )
  assert buildout.resolve_value("section7", "circular1") == "${section7:circular2}"
  assert (
    buildout.resolve_value("section10", "section-not-exists")
    == "${not-exists:not-exists}"
  )
  assert buildout.resolve_value("section10", "option-not-exists") == "${:not-exists}"
  with pytest.raises(KeyError):
    buildout.resolve_value("section1", "option-not-exists")
  with pytest.raises(KeyError):
    buildout.resolve_value("section-not-exists", "option")
