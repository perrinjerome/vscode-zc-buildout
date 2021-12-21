import textwrap
from typing import List, Sequence, cast
from unittest import mock

import pytest
from pygls.lsp.types import (
    Diagnostic,
    DiagnosticSeverity,
    Location,
    Position,
    Range,
)

from ..server import parseAndSendDiagnostics


@pytest.mark.asyncio
async def test_diagnostics_syntax_error(server) -> None:
  # syntax error
  await parseAndSendDiagnostics(server, 'file:///diagnostics/syntax_error.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///diagnostics/syntax_error.cfg',
      [mock.ANY],
  )
  diagnostic, = server.publish_diagnostics.call_args[0][1]
  assert diagnostic.range == Range(start=Position(line=2, character=0),
                                   end=Position(line=3, character=0))
  assert diagnostic.message == "ParseError: 'o\\n'"


@pytest.mark.asyncio
async def test_diagnostics_missing_section_error(server) -> None:
  # missing section error (a parse error handled differently)
  await parseAndSendDiagnostics(
      server, 'file:///diagnostics/missing_section_error.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///diagnostics/missing_section_error.cfg',
      [mock.ANY],
  )
  diagnostic, = server.publish_diagnostics.call_args[0][1]
  assert diagnostic.range == Range(start=Position(line=0, character=0),
                                   end=Position(line=1, character=0))
  assert diagnostic.message == textwrap.dedent("""\
      File contains no section headers.
      file: file:///diagnostics/missing_section_error.cfg, line: 0
      'key = value'""")


@pytest.mark.asyncio
async def test_diagnostics_non_existent_sections(server) -> None:
  # warnings for reference to non existent options
  await parseAndSendDiagnostics(server, 'file:///diagnostics/reference.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///diagnostics/reference.cfg',
      [mock.ANY, mock.ANY],
  )
  diagnostics: Sequence[Diagnostic] = sorted(
      server.publish_diagnostics.call_args[0][1],
      key=lambda d: d.range.start,
  )
  assert diagnostics[0].severity == DiagnosticSeverity.Error
  assert diagnostics[0].range == Range(start=Position(line=1, character=12),
                                       end=Position(line=1, character=27))
  assert diagnostics[0].message == \
    "Section `missing_section` does not exist."
  assert diagnostics[1].range == Range(start=Position(line=2, character=21),
                                       end=Position(line=2, character=35))
  assert diagnostics[1].message == \
    "Option `missing_option` does not exist in `section2`."


@pytest.mark.asyncio
async def test_diagnostics_non_existent_sections_multiple_references_per_line(
    server, ) -> None:
  # harder version, two errors on same line
  await parseAndSendDiagnostics(server, 'file:///diagnostics/harder.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///diagnostics/harder.cfg',
      [mock.ANY] * 8,
  )
  diagnostics = sorted(
      cast(List[Diagnostic], server.publish_diagnostics.call_args[0][1]),
      key=lambda d: d.range.start,
  )
  assert diagnostics[0].severity == DiagnosticSeverity.Error
  assert diagnostics[0].range == Range(start=Position(line=1, character=55),
                                       end=Position(line=1, character=70))
  assert diagnostics[0].message == \
    "Section `missing_section` does not exist."
  assert diagnostics[1].range == Range(start=Position(line=1, character=86),
                                       end=Position(line=1, character=101))
  assert diagnostics[1].message == \
    "Section `missing_section` does not exist."
  assert diagnostics[2].range == Range(start=Position(line=1, character=117),
                                       end=Position(line=1, character=132))
  assert diagnostics[2].message == \
    "Section `missing_section` does not exist."

  assert diagnostics[3].range == Range(start=Position(line=2, character=63),
                                       end=Position(line=2, character=77))
  assert diagnostics[3].message == \
    "Option `missing_option` does not exist in `section`."
  assert diagnostics[4].range == Range(start=Position(line=2, character=92),
                                       end=Position(line=2, character=106))
  assert diagnostics[4].message == \
    "Option `missing_option` does not exist in `section`."
  assert diagnostics[5].range == Range(start=Position(line=2, character=121),
                                       end=Position(line=2, character=135))
  assert diagnostics[5].message == \
    "Option `missing_option` does not exist in `section`."

  assert diagnostics[6].range == Range(start=Position(line=5, character=19),
                                       end=Position(line=5, character=34))
  assert diagnostics[6].message == \
    "Section `missing_section` does not exist."
  assert diagnostics[7].range == Range(start=Position(line=6, character=27),
                                       end=Position(line=6, character=41))
  assert diagnostics[7].message == \
    "Option `missing_option` does not exist in `section`."


@pytest.mark.asyncio
async def test_diagnostics_non_existent_sections_unknown_extends(
    server, ) -> None:
  await parseAndSendDiagnostics(
      server, 'file:///diagnostics/non_existant_sections_unknown_extends.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///diagnostics/non_existant_sections_unknown_extends.cfg', [])
  server.publish_diagnostics.reset_mock()
  await parseAndSendDiagnostics(
      server,
      'file:///diagnostics/non_existant_sections_unknown_extends_jinja.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///diagnostics/non_existant_sections_unknown_extends_jinja.cfg',
      [])


@pytest.mark.asyncio
async def test_diagnostics_required_recipe_option(server) -> None:
  await parseAndSendDiagnostics(
      server, 'file:///diagnostics/recipe_required_option.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///diagnostics/recipe_required_option.cfg',
      [mock.ANY],
  )
  diagnostics = sorted(
      cast(List[Diagnostic], server.publish_diagnostics.call_args[0][1]),
      key=lambda d: d.range.start,
  )
  assert diagnostics[0].severity == DiagnosticSeverity.Error
  assert diagnostics[0].message == \
    "Missing required options for `plone.recipe.command`: `command`"
  assert diagnostics[0].range == Range(start=Position(line=6, character=0),
                                       end=Position(line=7, character=0))


@pytest.mark.asyncio
async def test_diagnostics_extends_does_not_exist(server) -> None:
  await parseAndSendDiagnostics(
      server, 'file:///diagnostics/extends_does_not_exist.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///diagnostics/extends_does_not_exist.cfg',
      [mock.ANY],
  )
  diagnostics = sorted(
      cast(List[Diagnostic], server.publish_diagnostics.call_args[0][1]),
      key=lambda d: d.range.start,
  )
  assert diagnostics[0].severity == DiagnosticSeverity.Error
  assert diagnostics[0].message == \
    "Extended profile `does/not/exists.cfg` does not exist."
  assert diagnostics[0].range == Range(start=Position(line=2, character=4),
                                       end=Position(line=2, character=23))


@pytest.mark.asyncio
async def test_diagnostics_template(server) -> None:
  # syntax error
  await parseAndSendDiagnostics(server, 'file:///template.in')
  server.publish_diagnostics.assert_called_once_with(
      'file:///template.in',
      [mock.ANY, mock.ANY],
  )
  diagnostic1, diagnostic2 = server.publish_diagnostics.call_args[0][1]
  assert diagnostic1.range == Range(start=Position(line=4, character=25),
                                    end=Position(line=4, character=32))
  assert diagnostic1.message == "Section `missing` does not exist."

  assert diagnostic2.range == Range(start=Position(line=6, character=33),
                                    end=Position(line=6, character=47))
  assert diagnostic2.message == "Option `missing_option` does not exist in `section5`."


@pytest.mark.asyncio
async def test_diagnostics_buildout_parts(server) -> None:
  await parseAndSendDiagnostics(server,
                                'file:///diagnostics/buildout_parts.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///diagnostics/buildout_parts.cfg',
      [mock.ANY, mock.ANY],
  )
  diagnostic1, diagnostic2 = sorted(cast(
      List[Diagnostic], server.publish_diagnostics.call_args[0][1]),
                                    key=lambda d: d.range.start)
  assert diagnostic1.message == "Section `b` has no recipe."
  assert diagnostic1.range == Range(start=Position(line=3, character=4),
                                    end=Position(line=3, character=5))

  assert diagnostic2.message == "Section `c` does not exist."
  assert diagnostic2.range == Range(start=Position(line=4, character=4),
                                    end=Position(line=4, character=5))


@pytest.mark.asyncio
async def test_diagnostics_buildout_parts_section_name_with_dot(
    server) -> None:
  # This test checks that we supports section name with dots or dash
  await parseAndSendDiagnostics(
      server, 'file:///diagnostics/buildout_parts_section_name_with_dot.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///diagnostics/buildout_parts_section_name_with_dot.cfg',
      [mock.ANY])
  diagnostic, = server.publish_diagnostics.call_args[0][1]
  assert diagnostic.message == "Section `c.d` has no recipe."
  assert diagnostic.range == Range(start=Position(line=1, character=12),
                                   end=Position(line=1, character=15))


@pytest.mark.asyncio
async def test_diagnostics_option_redefinition(server) -> None:
  await parseAndSendDiagnostics(server,
                                'file:///diagnostics/option_redefinition.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///diagnostics/option_redefinition.cfg',
      [mock.ANY],
  )
  diagnostic, = cast(List[Diagnostic],
                     server.publish_diagnostics.call_args[0][1])
  assert diagnostic.range == Range(start=Position(line=7, character=3),
                                   end=Position(line=7, character=11))
  assert diagnostic.message == "`b` already has value `value b`."
  assert diagnostic.related_information
  assert [(ri.location, ri.message)
          for ri in diagnostic.related_information] == [
              (
                  Location(
                      uri='file:///diagnostics/option_redefinition.cfg',
                      range=Range(
                          start=Position(line=2, character=3),
                          end=Position(line=2, character=11),
                      ),
                  ),
                  'value: `value b`',
              ),
              (
                  Location(
                      uri='file:///diagnostics/option_redefinition.cfg',
                      range=Range(
                          start=Position(line=7, character=3),
                          end=Position(line=7, character=11),
                      ),
                  ),
                  'value: `value b`',
              ),
          ]


@pytest.mark.asyncio
async def test_diagnostics_option_redefinition_extended(server) -> None:
  await parseAndSendDiagnostics(
      server, 'file:///diagnostics/extended/option_redefinition.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///diagnostics/extended/option_redefinition.cfg',
      [mock.ANY],
  )
  diagnostic, = cast(List[Diagnostic],
                     server.publish_diagnostics.call_args[0][1])
  assert diagnostic.range == Range(start=Position(line=4, character=8),
                                   end=Position(line=4, character=10))
  assert diagnostic.message == "`recipe` already has value `x`."


@pytest.mark.asyncio
async def test_diagnostics_option_redefinition_default_value(server) -> None:
  await parseAndSendDiagnostics(
      server, 'file:///diagnostics/option_redefinition_default_value.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///diagnostics/option_redefinition_default_value.cfg',
      [mock.ANY],
  )
  diagnostic, = cast(List[Diagnostic],
                     server.publish_diagnostics.call_args[0][1])
  assert diagnostic.range == Range(start=Position(line=1, character=13),
                                   end=Position(line=1, character=15))
  assert diagnostic.message == "`allow-hosts` already has value `*`."
  assert diagnostic.related_information
  assert [
      (ri.location, ri.message) for ri in diagnostic.related_information
  ] == [
      (
          Location(
              uri='file:///diagnostics/option_redefinition_default_value.cfg',
              range=Range(
                  start=Position(line=0, character=0),
                  end=Position(line=0, character=0),
              ),
          ),
          'default value: `*`',
      ),
      (
          Location(
              uri='file:///diagnostics/option_redefinition_default_value.cfg',
              range=Range(
                  start=Position(line=1, character=13),
                  end=Position(line=1, character=15),
              ),
          ),
          'value: `*`',
      ),
  ]


@pytest.mark.asyncio
async def test_diagnostics_ok(server) -> None:
  # no false positives
  for url in (
      'file:///ok.cfg',
      'file:///diagnostics/extended.cfg',
      'file:///diagnostics/extended/buildout.cfg',
      'file:///diagnostics/jinja.cfg',
      'file:///diagnostics/ok_but_problems_in_extended.cfg',
      'file:///diagnostics/option_redefinition_macro.cfg',
      'file:///diagnostics/option_redefinition_extend_profile_base_location.cfg',
      'file:///diagnostics/recipe_any_option.cfg',
  ):
    await parseAndSendDiagnostics(server, url)
    server.publish_diagnostics.assert_called_once_with(url, [])
    server.publish_diagnostics.reset_mock()
