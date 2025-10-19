import textwrap
from typing import List, Sequence, cast
from unittest import mock

import pytest
from lsprotocol.types import (
  Diagnostic,
  DiagnosticSeverity,
  Position,
  PublishDiagnosticsParams,
  Range,
)

from ..server import parseAndSendDiagnostics


async def test_diagnostics_syntax_error(server) -> None:
  # syntax error
  await parseAndSendDiagnostics(server, "file:///diagnostics/syntax_error.cfg")
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/syntax_error.cfg",
      diagnostics=[mock.ANY],
    )
  )
  (diagnostic,) = server.text_document_publish_diagnostics.call_args[0][0].diagnostics
  assert diagnostic.range == Range(
    start=Position(line=2, character=0), end=Position(line=3, character=0)
  )
  assert diagnostic.message == "ParseError: 'o\\n'"


async def test_diagnostics_missing_section_error(server) -> None:
  # missing section error (a parse error handled differently)
  await parseAndSendDiagnostics(server, "file:///diagnostics/missing_section_error.cfg")
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/missing_section_error.cfg",
      diagnostics=[mock.ANY],
    )
  )
  (diagnostic,) = server.text_document_publish_diagnostics.call_args[0][0].diagnostics
  assert diagnostic.range == Range(
    start=Position(line=0, character=0), end=Position(line=1, character=0)
  )
  assert diagnostic.message == textwrap.dedent("""\
      File contains no section headers.
      file: file:///diagnostics/missing_section_error.cfg, line: 0
      'key = value'""")


async def test_diagnostics_non_existent_sections(server) -> None:
  # warnings for reference to non existent options
  await parseAndSendDiagnostics(server, "file:///diagnostics/reference.cfg")
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/reference.cfg",
      diagnostics=[mock.ANY, mock.ANY],
    )
  )
  diagnostics: Sequence[Diagnostic] = sorted(
    server.text_document_publish_diagnostics.call_args[0][0].diagnostics,
    key=lambda d: d.range.start,
  )
  assert diagnostics[0].severity == DiagnosticSeverity.Error
  assert diagnostics[0].range == Range(
    start=Position(line=1, character=12), end=Position(line=1, character=27)
  )
  assert diagnostics[0].message == "Section `missing_section` does not exist."
  assert diagnostics[1].range == Range(
    start=Position(line=2, character=21), end=Position(line=2, character=35)
  )
  assert (
    diagnostics[1].message == "Option `missing_option` does not exist in `section2`."
  )


async def test_diagnostics_non_existent_sections_multiple_references_per_line(
  server,
) -> None:
  # harder version, two errors on same line
  await parseAndSendDiagnostics(server, "file:///diagnostics/harder.cfg")
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/harder.cfg",
      diagnostics=[mock.ANY] * 8,
    )
  )
  diagnostics = sorted(
    cast(
      List[Diagnostic],
      server.text_document_publish_diagnostics.call_args[0][0].diagnostics,
    ),
    key=lambda d: d.range.start,
  )
  assert diagnostics[0].severity == DiagnosticSeverity.Error
  assert diagnostics[0].range == Range(
    start=Position(line=1, character=55), end=Position(line=1, character=70)
  )
  assert diagnostics[0].message == "Section `missing_section` does not exist."
  assert diagnostics[1].range == Range(
    start=Position(line=1, character=86), end=Position(line=1, character=101)
  )
  assert diagnostics[1].message == "Section `missing_section` does not exist."
  assert diagnostics[2].range == Range(
    start=Position(line=1, character=117), end=Position(line=1, character=132)
  )
  assert diagnostics[2].message == "Section `missing_section` does not exist."

  assert diagnostics[3].range == Range(
    start=Position(line=2, character=63), end=Position(line=2, character=77)
  )
  assert (
    diagnostics[3].message == "Option `missing_option` does not exist in `section`."
  )
  assert diagnostics[4].range == Range(
    start=Position(line=2, character=92), end=Position(line=2, character=106)
  )
  assert (
    diagnostics[4].message == "Option `missing_option` does not exist in `section`."
  )
  assert diagnostics[5].range == Range(
    start=Position(line=2, character=121), end=Position(line=2, character=135)
  )
  assert (
    diagnostics[5].message == "Option `missing_option` does not exist in `section`."
  )

  assert diagnostics[6].range == Range(
    start=Position(line=5, character=19), end=Position(line=5, character=34)
  )
  assert diagnostics[6].message == "Section `missing_section` does not exist."
  assert diagnostics[7].range == Range(
    start=Position(line=6, character=27), end=Position(line=6, character=41)
  )
  assert (
    diagnostics[7].message == "Option `missing_option` does not exist in `section`."
  )


async def test_diagnostics_non_existent_sections_unknown_extends(
  server,
) -> None:
  await parseAndSendDiagnostics(
    server, "file:///diagnostics/non_existant_sections_unknown_extends.cfg"
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/non_existant_sections_unknown_extends.cfg",
      diagnostics=[],
    )
  )
  server.text_document_publish_diagnostics.reset_mock()
  await parseAndSendDiagnostics(
    server, "file:///diagnostics/non_existant_sections_unknown_extends_jinja.cfg"
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/non_existant_sections_unknown_extends_jinja.cfg",
      diagnostics=[],
    )
  )


async def test_diagnostics_non_existent_sections_jinja(server) -> None:
  await parseAndSendDiagnostics(
    server,
    "file:///diagnostics/jinja-sections.cfg",
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/jinja-sections.cfg",
      diagnostics=[],
    )
  )
  server.text_document_publish_diagnostics.reset_mock()


async def test_diagnostics_required_recipe_option(server) -> None:
  await parseAndSendDiagnostics(
    server, "file:///diagnostics/recipe_required_option.cfg"
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/recipe_required_option.cfg",
      diagnostics=[mock.ANY],
    )
  )
  diagnostics = sorted(
    server.text_document_publish_diagnostics.call_args[0][0].diagnostics,
    key=lambda d: d.range.start,
  )
  assert diagnostics[0].severity == DiagnosticSeverity.Error
  assert (
    diagnostics[0].message
    == "Missing required options for `plone.recipe.command`: `command`"
  )
  assert diagnostics[0].range == Range(
    start=Position(line=6, character=0), end=Position(line=7, character=0)
  )


async def test_diagnostics_extends_does_not_exist(server) -> None:
  await parseAndSendDiagnostics(
    server, "file:///diagnostics/extends_does_not_exist.cfg"
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/extends_does_not_exist.cfg",
      diagnostics=[mock.ANY],
    )
  )
  (diagnostic,) = server.text_document_publish_diagnostics.call_args[0][0].diagnostics
  assert diagnostic.range == Range(
    start=Position(line=2, character=4), end=Position(line=2, character=23)
  )
  assert diagnostic.message == "Extended profile `does/not/exists.cfg` does not exist."


async def test_diagnostics_template(server) -> None:
  # syntax error
  await parseAndSendDiagnostics(server, "file:///template.in")
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///template.in",
      diagnostics=[mock.ANY, mock.ANY],
    )
  )
  diagnostic1, diagnostic2 = server.text_document_publish_diagnostics.call_args[0][
    0
  ].diagnostics
  assert diagnostic1.range == Range(
    start=Position(line=4, character=25), end=Position(line=4, character=32)
  )
  assert diagnostic1.message == "Section `missing` does not exist."

  assert diagnostic2.range == Range(
    start=Position(line=6, character=33), end=Position(line=6, character=47)
  )
  assert diagnostic2.message == "Option `missing_option` does not exist in `section5`."


async def test_diagnostics_buildout_parts(server) -> None:
  await parseAndSendDiagnostics(server, "file:///diagnostics/buildout_parts.cfg")
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/buildout_parts.cfg",
      diagnostics=[mock.ANY, mock.ANY],
    )
  )
  diagnostic1, diagnostic2 = sorted(
    server.text_document_publish_diagnostics.call_args[0][0].diagnostics,
    key=lambda d: d.range.start,
  )
  assert diagnostic1.message == "Section `b` has no recipe."
  assert diagnostic1.range == Range(
    start=Position(line=3, character=4), end=Position(line=3, character=5)
  )

  assert diagnostic2.message == "Section `c` does not exist."
  assert diagnostic2.range == Range(
    start=Position(line=4, character=4), end=Position(line=4, character=5)
  )


async def test_diagnostics_buildout_parts_section_name_with_dot(server) -> None:
  # This test checks that we supports section name with dots or dash
  await parseAndSendDiagnostics(
    server, "file:///diagnostics/buildout_parts_section_name_with_dot.cfg"
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/buildout_parts_section_name_with_dot.cfg",
      diagnostics=[mock.ANY],
    )
  )
  (diagnostic,) = server.text_document_publish_diagnostics.call_args[0][0].diagnostics
  assert diagnostic.message == "Section `c.d` has no recipe."
  assert diagnostic.range == Range(
    start=Position(line=1, character=12), end=Position(line=1, character=15)
  )


async def test_diagnostics_option_redefinition(server) -> None:
  await parseAndSendDiagnostics(server, "file:///diagnostics/option_redefinition.cfg")
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/option_redefinition.cfg",
      diagnostics=[mock.ANY, mock.ANY],
    ),
  )
  diagnostic_override, diagnostic_already_has_value = (
    server.text_document_publish_diagnostics.call_args[0][0].diagnostics
  )

  assert repr(diagnostic_override.range) == "5:3-5:18"
  assert diagnostic_override.message == "`a` overrides an existing value."
  assert diagnostic_override.severity == DiagnosticSeverity.Hint
  assert diagnostic_override.related_information
  assert [
    (repr(ri.location), ri.message) for ri in diagnostic_override.related_information
  ] == [
    (
      "file:///diagnostics/option_redefinition.cfg:1:3-1:11",
      "value: `value a`",
    ),
    (
      "file:///diagnostics/option_redefinition.cfg:5:3-5:18",
      "value: `something else`",
    ),
  ]

  assert repr(diagnostic_already_has_value.range) == "7:3-7:11"
  assert diagnostic_already_has_value.message == "`b` already has value `value b`."
  assert diagnostic_already_has_value.severity == DiagnosticSeverity.Information
  assert diagnostic_already_has_value.related_information
  assert [
    (repr(ri.location), ri.message)
    for ri in diagnostic_already_has_value.related_information
  ] == [
    (
      "file:///diagnostics/option_redefinition.cfg:2:3-2:11",
      "value: `value b`",
    ),
    (
      "file:///diagnostics/option_redefinition.cfg:7:3-7:11",
      "value: `value b`",
    ),
  ]


async def test_diagnostics_option_redefinition_extended(server) -> None:
  await parseAndSendDiagnostics(
    server, "file:///diagnostics/extended/option_redefinition.cfg"
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/extended/option_redefinition.cfg",
      diagnostics=[mock.ANY],
    ),
  )
  (diagnostic,) = server.text_document_publish_diagnostics.call_args[0][0].diagnostics
  assert repr(diagnostic.range) == "4:8-4:10"
  assert diagnostic.message == "`recipe` already has value `x`."


async def test_diagnostics_option_redefinition_default_value(server) -> None:
  await parseAndSendDiagnostics(
    server, "file:///diagnostics/option_redefinition_default_value.cfg"
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/option_redefinition_default_value.cfg",
      diagnostics=[mock.ANY],
    ),
  )
  (diagnostic,) = server.text_document_publish_diagnostics.call_args[0][0].diagnostics
  assert repr(diagnostic.range) == "1:13-1:15"
  assert diagnostic.message == "`allow-hosts` already has value `*`."
  assert diagnostic.related_information
  assert [(repr(ri.location), ri.message) for ri in diagnostic.related_information] == [
    (
      "file:///diagnostics/option_redefinition_default_value.cfg:0:0-0:0",
      "default value: `*`",
    ),
    (
      "file:///diagnostics/option_redefinition_default_value.cfg:1:13-1:15",
      "value: `*`",
    ),
  ]


async def test_diagnostics_option_redefined_hints_macro(server) -> None:
  await parseAndSendDiagnostics(
    server,
    "file:///diagnostics/option_redefinition_macro.cfg",
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/option_redefinition_macro.cfg",
      diagnostics=[mock.ANY, mock.ANY],
    ),
  )
  duser, danother_user = server.text_document_publish_diagnostics.call_args[0][
    0
  ].diagnostics
  assert repr(duser.range) == "5:5-5:9"
  assert duser.severity == DiagnosticSeverity.Hint
  assert duser.message == "`foo` overrides an existing value."
  assert duser.related_information
  assert [(repr(ri.location), ri.message) for ri in duser.related_information] == [
    (
      "file:///diagnostics/option_redefinition_macro.cfg:1:5-1:9",
      "value: `bar`",
    ),
    (
      "file:///diagnostics/option_redefinition_macro.cfg:5:5-5:9",
      "value: `baz`",
    ),
  ]

  assert repr(danother_user.range) == "9:5-9:9"
  assert danother_user.severity == DiagnosticSeverity.Hint
  assert danother_user.message == "`foo` overrides an existing value."
  assert danother_user.related_information
  assert [
    (repr(ri.location), ri.message) for ri in danother_user.related_information
  ] == [
    (
      "file:///diagnostics/option_redefinition_macro.cfg:1:5-1:9",
      "value: `bar`",
    ),
    (
      "file:///diagnostics/option_redefinition_macro.cfg:9:5-9:9",
      "value: `baz`",
    ),
  ]


async def test_diagnostics_option_redefined_hints_extends(server) -> None:
  await parseAndSendDiagnostics(
    server,
    "file:///diagnostics/option_redefinition_extend_profile_base_location.cfg",
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///diagnostics/option_redefinition_extend_profile_base_location.cfg",
      diagnostics=[mock.ANY, mock.ANY],
    ),
  )
  dsection, dmacro = server.text_document_publish_diagnostics.call_args[0][
    0
  ].diagnostics

  assert repr(dsection.range) == "5:8-5:46"
  assert dsection.severity == DiagnosticSeverity.Hint
  assert dsection.message == "`option` overrides an existing value."
  assert dsection.related_information
  assert [(repr(ri.location), ri.message) for ri in dsection.related_information] == [
    (
      "file:///diagnostics/extended/option_redefinition_extend_profile_base_location.cfg:1:8-1:46",
      "value: `${:_profile_base_location_}/something`",
    ),
    (
      "file:///diagnostics/option_redefinition_extend_profile_base_location.cfg:5:8-5:46",
      "value: `${:_profile_base_location_}/something`",
    ),
  ]

  assert repr(dmacro.range) == "9:8-9:46"
  assert dmacro.severity == DiagnosticSeverity.Hint
  assert dmacro.message == "`option` overrides an existing value."
  assert dmacro.related_information
  assert [(repr(ri.location), ri.message) for ri in dmacro.related_information] == [
    (
      "file:///diagnostics/extended/option_redefinition_extend_profile_base_location.cfg:4:8-4:46",
      "value: `${:_profile_base_location_}/something`",
    ),
    (
      "file:///diagnostics/option_redefinition_extend_profile_base_location.cfg:9:8-9:46",
      "value: `${:_profile_base_location_}/something`",
    ),
  ]


@pytest.mark.parametrize(
  "url",
  (
    "file:///ok.cfg",
    "file:///diagnostics/extended.cfg",
    "file:///diagnostics/extended/buildout.cfg",
    "file:///diagnostics/jinja.cfg",
    "file:///diagnostics/ok_but_problems_in_extended.cfg",
    "file:///diagnostics/ok_extends_with_substitutions.cfg",
    "file:///diagnostics/ok_extends_from_url.cfg",
    "file:///diagnostics/recipe_any_option.cfg",
    "file:///diagnostics/ok_parts_with_substitutions.cfg",
  ),
)
async def test_diagnostics_ok(server, url) -> None:
  # no false positives
  await parseAndSendDiagnostics(server, url)
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(uri=url, diagnostics=[])
  )
