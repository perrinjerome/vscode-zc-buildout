import io

import textwrap
import responses
from typing import List

import pytest

from pygls.server import LanguageServer
from pygls.types import (
    Location,
    Position,
    Range,
)

from ..buildout import (
    BuildoutProfile,
    BuildoutTemplate,
    RecursiveIncludeError,
    Symbol,
    SymbolKind,
    _parse,
    open,
)
from buildoutls.buildout import clearCache
from unittest import mock
import requests


## parse tests
@pytest.mark.asyncio
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
                """)),
      uri='file:///buildout.cfg',
      allow_errors=False,
  )
  assert list(parsed.keys()) == ['buildout', 's1', 's2']
  assert sorted(parsed['s1'].keys()) == [
      '_buildout_section_name_', '_profile_base_location_', 'opt1', 'opt2'
  ]
  assert sorted(parsed['s2'].keys()) == [
      '_buildout_section_name_', '_profile_base_location_', 'opt3'
  ]

  assert parsed['s1']['opt1'].value == "value1"
  assert parsed['s1']['opt2'].value == "value2bis"
  assert parsed['s2']['opt3'].value == "multi\nline"

  assert parsed['s1']['opt1'].locations == [
      Location(uri='file:///buildout.cfg',
               range=Range(
                   start=Position(line=1, character=6),
                   end=Position(line=1, character=13),
               ))
  ]
  assert parsed['s1']['opt2'].locations == [
      Location(uri='file:///buildout.cfg',
               range=Range(
                   start=Position(line=2, character=6),
                   end=Position(line=2, character=13),
               )),
      Location(uri='file:///buildout.cfg',
               range=Range(
                   start=Position(line=8, character=6),
                   end=Position(line=8, character=16),
               )),
  ]
  assert parsed['s2']['opt3'].locations == [
      Location(uri='file:///buildout.cfg',
               range=Range(
                   start=Position(line=4, character=6),
                   end=Position(line=6, character=8),
               )),
  ]
  # section headers ranges are properties of buildout
  assert list(parsed.section_header_locations.items()) == [
      ('buildout',
       Location(uri='',
                range=Range(start=Position(line=0, character=0),
                            end=Position(line=0, character=0)))),
      (
          's1',
          Location(
              uri='file:///buildout.cfg',
              # we only have the last range
              range=Range(start=Position(line=7, character=0),
                          end=Position(line=8, character=0)))),
      ('s2',
       Location(uri='file:///buildout.cfg',
                range=Range(start=Position(line=3, character=0),
                            end=Position(line=4, character=0)))),
  ]


@pytest.mark.asyncio
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
                """)),
      uri="file:///buildout.cfg",
      allow_errors=False,
  )
  assert list(parsed.keys()) == [
      'buildout', 'section', 'sectionJINJA_EXPRESSION', 'another_section'
  ]
  assert sorted(parsed['section'].keys()) == [
      'JINJA_EXPRESSION',
      '_buildout_section_name_',
      '_profile_base_location_',
      'option',
  ]
  assert parsed['section']['option'].value == 'JINJA_EXPRESSION'
  assert parsed['section']['JINJA_EXPRESSION'].value == 'value'
  assert parsed['sectionJINJA_EXPRESSION']['option'].value == 'value'
  assert parsed['another_section'][
      'JINJA_EXPRESSION'].value == 'JINJA_EXPRESSION'


@pytest.mark.asyncio
async def test_BuildoutProfile_getSymbolAtPosition_BuildoutOptionKey(
    buildout: BuildoutProfile) -> None:
  for pos in (Position(line=5, character=3), Position(line=5, character=0),
              Position(line=5, character=7)):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.BuildoutOptionKey
    assert symbol.value == 'command'
    assert symbol.current_section_name == 'section1'
    assert symbol.current_option_name == 'command'

  for pos in (Position(line=22, character=1), Position(line=22, character=0)):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.BuildoutOptionKey
    assert symbol.value == 'op'
    assert symbol.current_section_name == 'section4'
    assert symbol.current_option_name == 'op'

  # an empty line is a buildout option key
  for pos in (Position(line=6, character=0), ):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.BuildoutOptionKey
    assert symbol.value == ''
    assert symbol.current_section_name == 'section1'
    assert symbol.current_option_name == ''


@pytest.mark.asyncio
async def test_BuildoutProfile_getSymbolAtPosition_BuildoutOptionValue(
    buildout: BuildoutProfile) -> None:
  for pos in (Position(line=5, character=11), Position(line=5, character=10),
              Position(line=5, character=24)):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.BuildoutOptionValue
    assert symbol.value == 'echo install section1'
    assert symbol.current_section_name == 'section1'
    assert symbol.current_option_name == 'command'

  for pos in (
      Position(line=17, character=5),
      Position(line=17, character=0),
      Position(line=17, character=4),
      Position(line=17, character=10),
  ):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.BuildoutOptionValue
    assert symbol.value == 'value2'  # in a multi line option, value is only the current line
    assert symbol.current_section_name == 'section3'
    assert symbol.current_option_name == 'multi_line_option'


@pytest.mark.asyncio
async def test_BuildoutProfile_getSymbolAtPosition_SectionReference(
    buildout: BuildoutProfile) -> None:
  for pos in (Position(line=13, character=14), Position(line=13, character=12),
              Position(line=13, character=20)):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.SectionReference
    assert symbol.current_section_name == 'section3'
    assert symbol.current_option_name == 'command'
    assert symbol.referenced_section_name == 'section1'
    assert symbol.referenced_section is not None
    assert symbol.referenced_section[
        'command'].value == 'echo install section1'
    assert symbol.referenced_section_recipe is not None
    assert symbol.referenced_section_recipe.name == 'plone.recipe.command'
    assert symbol.referenced_option is not None

  for pos in (Position(line=13, character=34), Position(line=13, character=32),
              Position(line=13, character=40)):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.SectionReference
    assert symbol.referenced_section_name == 'section2'

  for pos in (Position(line=14, character=34), Position(line=14,
                                                        character=37)):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.SectionReference
    assert symbol.current_section_name == 'section3'
    assert symbol.current_option_name == 'option_with_section_reference'
    assert symbol.referenced_section_name == 'section1'
    assert symbol.referenced_section is not None
    assert symbol.referenced_section[
        'command'].value == 'echo install section1'
    assert symbol.referenced_section_recipe is not None
    assert symbol.referenced_section_recipe.name == 'plone.recipe.command'

  # multi-line option
  for pos in (Position(line=18, character=10), Position(line=18, character=7),
              Position(line=18, character=14)):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.SectionReference
    assert symbol.current_section_name == 'section3'
    assert symbol.current_option_name == 'multi_line_option'
    assert symbol.referenced_section_name == 'section1'
    assert symbol.referenced_section is not None
    assert symbol.referenced_section[
        'command'].value == 'echo install section1'
    assert symbol.referenced_section_recipe is not None
    assert symbol.referenced_section_recipe.name == 'plone.recipe.command'


@pytest.mark.asyncio
async def test_BuildoutProfile_getSymbolAtPosition_OptionReference(
    buildout: BuildoutProfile) -> None:
  for pos in (Position(line=13, character=23), Position(line=13, character=21),
              Position(line=13, character=28)):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.OptionReference
    assert symbol.referenced_section_name == 'section1'
    assert symbol.referenced_option_name == 'command'
    assert symbol.referenced_option is not None
    assert symbol.referenced_option.value == 'echo install section1'
    assert symbol.referenced_section_recipe is not None
    assert symbol.referenced_section_recipe.name == 'plone.recipe.command'

  # two on same line
  for pos in (Position(line=13, character=43), Position(line=13, character=41),
              Position(line=13, character=48)):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.OptionReference
    assert symbol.referenced_section_name == 'section2'
    assert symbol.referenced_option_name == 'command'
    assert symbol.referenced_option is not None
    assert symbol.referenced_option.value == 'echo install section2'

  # empty section ${:option}
  symbol = await buildout.getSymbolAtPosition(Position(line=27, character=14))
  assert symbol is not None
  assert symbol.kind == SymbolKind.OptionReference
  assert symbol.referenced_section_name == 'section5'
  assert symbol.referenced_option_name == 'command'
  assert symbol.referenced_option is not None
  assert symbol.referenced_option.value == 'echo install section5'


@pytest.mark.asyncio
async def test_BuildoutProfile_getSymbolAtPosition_SectionDefinition(
    buildout: BuildoutProfile, ) -> None:
  for pos in (Position(line=3, character=1), Position(line=3, character=0),
              Position(line=3, character=10)):
    symbol = await buildout.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.SectionDefinition
    assert symbol.current_section_name == 'section1'


@pytest.mark.asyncio
async def test_BuildoutProfile_getAllOptionReferenceSymbols(
    buildout: BuildoutProfile) -> None:
  symbols: List[Symbol] = []
  async for symbol in buildout.getAllOptionReferenceSymbols():
    symbols.append(symbol)
  assert [(s.referenced_section_name, s.referenced_option_name)
          for s in symbols] == [
              ('section1', 'command'),
              ('section2', 'command'),
              ('section1', 'command'),
              # this is ${:command} in the source, but this had been expanded
              ('section5', 'command'),
          ]
  assert [(s.referenced_section is not None, s.referenced_option is not None)
          for s in symbols] == [
              (True, True),
              (True, True),
              (True, True),
              (True, True),
          ]
  assert {s.current_section_name for s in symbols} == {None}
  assert {s.kind for s in symbols} == {SymbolKind.OptionReference}


@pytest.mark.asyncio
async def test_BuildoutProfile_getTemplate(
    buildout: BuildoutProfile,
    server: LanguageServer,
) -> None:
  assert await buildout.getTemplate(server, 'template.in') is not None
  assert await buildout.getTemplate(server, 'file:///template.in') is not None
  assert await buildout.getTemplate(server, 'not exists') is None


@pytest.mark.asyncio
async def test_BuildoutTemplate_getSymbolAtPosition_SectionReference(
    template: BuildoutTemplate, ) -> None:
  for pos in (Position(line=2, character=24), Position(line=2, character=22),
              Position(line=2, character=30)):
    symbol = await template.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.SectionReference
    assert symbol.referenced_section_name == 'section5'
    assert symbol.referenced_section is not None
    assert 'command' in symbol.referenced_section
    assert symbol.referenced_section_recipe is not None
  for pos in (Position(line=2, character=46), Position(line=2, character=45),
              Position(line=2, character=53)):
    symbol = await template.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.SectionReference
    assert symbol.referenced_section_name == 'section5'
    assert symbol.referenced_section is not None
    assert 'command' in symbol.referenced_section
    assert symbol.referenced_section_recipe is not None


@pytest.mark.asyncio
async def test_BuildoutTemplate_getSymbolAtPosition_OptionReference(
    template: BuildoutTemplate, ) -> None:
  for pos in (Position(line=2, character=34), Position(line=2, character=31),
              Position(line=2, character=38)):
    symbol = await template.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.OptionReference
    assert symbol.referenced_section is not None
    assert symbol.referenced_option_name == 'command'
    assert symbol.referenced_option is not None
    assert symbol.referenced_option.value == 'echo install section5'

  for pos in (Position(line=2, character=56), Position(line=2, character=54),
              Position(line=2, character=60)):
    symbol = await template.getSymbolAtPosition(pos)
    assert symbol is not None
    assert symbol.kind == SymbolKind.OptionReference
    assert symbol.referenced_section is not None
    assert symbol.referenced_option_name == 'option'
    assert symbol.referenced_option is not None
    assert symbol.referenced_option.value == '${:command}'


@pytest.mark.asyncio
async def test_BuildoutTemplate_getSymbolAtPosition_None(
    template: BuildoutTemplate, ) -> None:
  for pos in (Position(line=0, character=0), Position(line=4, character=11),
              Position(line=6, character=60)):
    symbol = await template.getSymbolAtPosition(pos)
    assert symbol is None


@pytest.mark.asyncio
async def test_BuildoutTemplate_getAllOptionReferenceSymbols(
    template: BuildoutTemplate) -> None:
  symbols: List[Symbol] = []
  async for symbol in template.getAllOptionReferenceSymbols():
    symbols.append(symbol)

  assert [(s.referenced_section_name, s.referenced_option_name)
          for s in symbols] == [
              ('buildout', 'directory'),
              ('section5', 'command'),
              ('section5', 'option'),
              ('missing', 'option'),
              ('section5', 'missing_option'),
          ]
  assert [(s.referenced_section is not None, s.referenced_option is not None)
          for s in symbols] == [
              (True, True),
              (True, True),
              (True, True),
              (False, False),
              (True, False),
          ]
  assert {s.current_section_name for s in symbols} == {None}
  assert {s.kind for s in symbols} == {SymbolKind.OptionReference}


@pytest.mark.asyncio
async def test_getOptionValues(server: LanguageServer):
  parsed = await open(
      ls=server,
      uri='file:///option_values/buildout.cfg',
  )
  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.getOptionValues('multi_line', 'option')) == [
      ('first line',
       Range(start=Position(line=2, character=2),
             end=Position(line=2, character=12))),
      ('second line',
       Range(start=Position(line=3, character=2),
             end=Position(line=3, character=13))),
  ]
  assert list(parsed.getOptionValues('simple_line', 'option')) == [
      ('first',
       Range(start=Position(line=6, character=9),
             end=Position(line=6, character=14))),
      ('second',
       Range(start=Position(line=6, character=15),
             end=Position(line=6, character=21))),
  ]


@pytest.mark.asyncio
async def test_open_extends(server: LanguageServer):
  parsed = await open(
      ls=server,
      uri='file:///extended/buildout.cfg',
  )
  assert isinstance(parsed, BuildoutProfile)
  assert parsed.uri == 'file:///extended/buildout.cfg'
  # options are replaced
  assert (parsed['overloaded_from_another_buildout']['option'].value ==
          'this is overloaded in extended/extended.cfg')
  assert parsed['overloaded_from_another_buildout']['option'].locations == [
      Location(uri='file:///extended/extended.cfg',
               range=Range(Position(7, 8), Position(7, 52)))
  ]

  # options are mixed in the same section
  assert parsed['merged_section'][
      'kept_option'].value == 'this is from extended/another/buildout.cfg'
  assert parsed['merged_section']['kept_option'].locations == [
      Location(uri='file:///extended/another/buildout.cfg',
               range=Range(Position(5, 13), Position(5, 56)))
  ]
  assert parsed['merged_section'][
      'overloaded_option'].value == 'from extended/buildout.cfg'
  assert parsed['merged_section']['overloaded_option'].locations == [
      Location(uri='file:///extended/buildout.cfg',
               range=Range(Position(6, 19), Position(6, 46)))
  ]
  # options are extended with +=
  assert parsed['extended_option'][
      'option'].value == 'option from extended/extended.cfg\nthen extended in extended/buildout.cfg'
  assert parsed['extended_option']['option'].locations == [
      Location(uri='file:///extended/extended.cfg',
               range=Range(Position(1, 8), Position(1, 42))),
      Location(uri='file:///extended/buildout.cfg',
               range=Range(Position(9, 9), Position(9, 48)))
  ]
  assert 'option +' not in parsed['extended_option']

  # this works also for multi lines options
  assert parsed['extended_option'][
      'mutli_line_option'].value == 'value1\nvalue2\nvalue3'
  assert parsed['extended_option']['mutli_line_option'].locations == [
      Location(uri='file:///extended/extended.cfg',
               range=Range(Position(2, 19), Position(5, 0))),
      Location(uri='file:///extended/buildout.cfg',
               range=Range(Position(10, 20), Position(12, 0)))
  ]
  assert 'mutli_line_option +' not in parsed['extended_option']

  # options can be removed with -=
  assert parsed['reduced_option']['option'].value == 'value1\nvalue3'
  assert parsed['reduced_option']['option'].locations == [
      Location(uri='file:///extended/extended.cfg',
               range=Range(Position(10, 8), Position(13, 9))),
      Location(uri='file:///extended/buildout.cfg',
               range=Range(Position(14, 9), Position(15, 9)))
  ]
  assert 'option -' not in parsed['reduced_option']


@pytest.mark.asyncio
async def test_open_extends_file_not_found(server: LanguageServer):
  with pytest.raises(FileNotFoundError):
    await open(
        ls=server,
        uri='file:///extended/broken/file_not_found.cfg',
        allow_errors=False,
    )
  parsed = await open(ls=server,
                      uri='file:///extended/broken/file_not_found.cfg')
  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.keys()) == ['buildout', 'section']


@pytest.mark.asyncio
async def test_open_extends_loop(server: LanguageServer):
  with pytest.raises(RecursiveIncludeError):
    await open(ls=server,
               uri='file:///extended/broken/loop.cfg',
               allow_errors=False)
  parsed = await open(ls=server, uri='file:///extended/broken/loop.cfg')
  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.keys()) == ['buildout', 'section']


@pytest.mark.asyncio
async def test_open_extends_getSymbolAtPosition(server: LanguageServer):
  parsed = await open(ls=server, uri='file:///extended/buildout.cfg')
  assert isinstance(parsed, BuildoutProfile)
  overloaded_option = await parsed.getSymbolAtPosition(
      Position(line=6, character=6))
  assert overloaded_option is not None
  assert overloaded_option.kind == SymbolKind.BuildoutOptionKey
  assert overloaded_option.current_section_name == 'merged_section'
  assert overloaded_option.current_option_name == 'overloaded_option'

  overloaded_option_value = await parsed.getSymbolAtPosition(
      Position(line=6, character=26))
  assert overloaded_option_value is not None
  assert overloaded_option_value.kind == SymbolKind.BuildoutOptionValue
  assert overloaded_option_value.current_section_name == 'merged_section'
  assert overloaded_option_value.current_option_name == 'overloaded_option'
  assert overloaded_option_value.value == 'from extended/buildout.cfg'


@pytest.mark.asyncio
async def test_open_extends_section_header_locations(server: LanguageServer):
  parsed = await open(ls=server, uri='file:///extended/buildout.cfg')
  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.section_header_locations.items()) == [
      ('buildout',
       Location(uri='file:///extended/buildout.cfg',
                range=Range(start=Position(line=0, character=0),
                            end=Position(line=1, character=0)))),
      ('extended_option',
       Location(uri='file:///extended/buildout.cfg',
                range=Range(start=Position(line=8, character=0),
                            end=Position(line=9, character=0)))),
      ('overloaded_from_another_buildout',
       Location(uri='file:///extended/extended.cfg',
                range=Range(start=Position(line=6, character=0),
                            end=Position(line=7, character=0)))),
      ('reduced_option',
       Location(uri='file:///extended/buildout.cfg',
                range=Range(start=Position(line=13, character=0),
                            end=Position(line=14, character=0)))),
      ('merged_section',
       Location(uri='file:///extended/buildout.cfg',
                range=Range(start=Position(line=5, character=0),
                            end=Position(line=6, character=0)))),
  ]


@pytest.mark.asyncio
async def test_open_extends_cache(server: LanguageServer):
  await open(
      ls=server,
      uri='file:///extended/buildout.cfg',
  )
  # check the cache is effective, the same file is included twice,
  # but we load it only once.
  assert server.workspace.get_document.call_count == 4  # type: ignore


@pytest.mark.asyncio
async def test_open_extends_cache_clear(server: LanguageServer):
  parsed = await open(
      ls=server,
      uri='file:///extended/two_levels.cfg',
  )
  assert parsed is not None
  symbol = await parsed.getSymbolAtPosition(Position(line=6, character=30))
  assert symbol is not None
  assert symbol.referenced_section is not None
  assert 'option' in symbol.referenced_section

  clearCache('file:///extended/extended.cfg')
  original_get_document = server.workspace.get_document

  def getModifiedDocument(uri: str):
    doc = original_get_document(uri)
    if uri == 'file:///extended/extended.cfg':
      doc._source = textwrap.dedent('''\
          [extended_option]
          new_option = after modification
          ''')
    return doc

  with mock.patch.object(
      server.workspace,
      'get_document',
      side_effect=getModifiedDocument,
  ):
    parsed = await open(
        ls=server,
        uri='file:///extended/two_levels.cfg',
    )
    assert parsed is not None
    symbol = await parsed.getSymbolAtPosition(Position(line=6, character=30))
    assert symbol is not None
    assert symbol.referenced_section is not None
    assert 'new_option' in symbol.referenced_section
    assert 'option' in symbol.referenced_section


@pytest.mark.asyncio
async def test_open_macro(server: LanguageServer):
  parsed = await open(ls=server, uri='file:///extended/macros/buildout.cfg')
  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.keys()) == ['buildout', 'macro1', 'macro2', 'macro_user']
  assert parsed['macro_user']['option1'].value == 'value1'
  assert parsed['macro_user']['option2'].value == 'value2'
  assert parsed['macro_user']['option3'].value == 'value3'
  assert '<' not in parsed['macro_user']


@pytest.mark.asyncio
async def test_open_extends_network(server: LanguageServer, mocked_responses):
  mocked_responses.add(responses.GET,
                       'https://example.com/profiles/buildout.cfg',
                       body=textwrap.dedent('''\
        [buildout]
        extends = ./other.cfg
        '''))
  mocked_responses.add(responses.GET,
                       'https://example.com/profiles/other.cfg',
                       body=textwrap.dedent('''\
        [section]
        option = value
        '''))

  parsed = await open(
      ls=server,
      uri='file:///extended/network.cfg',
      allow_errors=False,
  )

  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.keys()) == ['buildout', 'section']
  assert parsed['section']['option'].value == 'value'


@pytest.mark.asyncio
async def test_open_extends_network_fail(server: LanguageServer,
                                         mocked_responses):
  mocked_responses.add(
      responses.GET,
      'https://example.com/profiles/buildout.cfg',
      body=requests.exceptions.ConnectionError('random network error'))

  parsed = await open(
      ls=server,
      uri='file:///extended/network.cfg',
      allow_errors=False,
  )

  assert isinstance(parsed, BuildoutProfile)
  assert list(parsed.keys()) == ['buildout']
