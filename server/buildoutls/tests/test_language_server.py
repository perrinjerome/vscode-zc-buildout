import textwrap
import urllib.parse
from typing import cast, List, Sequence
from unittest import mock

import pytest

from pygls.server import LanguageServer
from pygls.lsp.types import (
    CompletionContext,
    CompletionParams,
    CompletionTriggerKind,
    Diagnostic,
    DiagnosticSeverity,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    DocumentLinkParams,
    DocumentSymbolParams,
    Location,
    MarkupContent,
    MarkupKind,
    Position,
    Range,
    TextDocumentIdentifier,
    TextDocumentItem,
    TextDocumentPositionParams,
)
from pygls.workspace import Document, Workspace

from ..server import (
    lsp_completion,
    lsp_definition,
    lsp_document_link,
    lsp_hover,
    lsp_references,
    lsp_symbols,
    parseAndSendDiagnostics,
)


def getTextDocumentItem(workspace: Workspace,
                        doc_uri: str) -> TextDocumentItem:
  """Returns a TextDocumentItem for an uri
  """
  doc = workspace.get_document(doc_uri)
  return TextDocumentItem(
      uri=doc_uri,
      language_id='zc.buildout',
      version=1,
      text=doc.source,
  )


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
  ):
    await parseAndSendDiagnostics(server, url)
    server.publish_diagnostics.assert_called_once_with(url, [])
    server.publish_diagnostics.reset_mock()


@pytest.mark.asyncio
async def test_symbol(server: LanguageServer):
  params = DocumentSymbolParams(text_document=TextDocumentIdentifier(
      uri='file:///symbol/buildout.cfg'))

  symbols = await lsp_symbols(server, params)
  assert [s.name for s in symbols] == [
      'section1',
      'section2',
      'section3',
  ]
  assert [s.range for s in symbols] == [
      Range(start=Position(line=0, character=0),
            end=Position(line=1, character=0)),
      Range(start=Position(line=3, character=0),
            end=Position(line=5, character=0)),
      Range(start=Position(line=7, character=0),
            end=Position(line=12, character=0)),
  ]
  assert [s.detail for s in symbols] == [
      '',
      '',
      'plone.recipe.command',
  ]
  assert symbols[1].children is not None
  assert [o.name for o in symbols[1].children] == [
      "option2",
      "option3",
  ]
  assert [o.detail for o in symbols[1].children] == [
      '${section1:option1}',
      '${section2:option2} ${section3:option4}',
  ]
  assert [s.range for s in symbols[1].children] == [
      Range(start=Position(line=4, character=0),
            end=Position(line=4, character=0)),
      Range(start=Position(line=5, character=0),
            end=Position(line=5, character=0)),
  ]

  assert symbols[2].children is not None
  assert [o.name for o in symbols[2].children] == [
      "recipe",
      "multi-line-option",
      "command",
  ]
  assert [s.range for s in symbols[2].children] == [
      Range(start=Position(line=8, character=0),
            end=Position(line=8, character=0)),
      Range(start=Position(line=9, character=0),
            end=Position(line=11, character=0)),
      Range(start=Position(line=12, character=0),
            end=Position(line=12, character=0)),
  ]

  params = DocumentSymbolParams(text_document=TextDocumentIdentifier(
      uri='file:///symbol/with_default_section.cfg'))

  symbols = await lsp_symbols(server, params)
  assert [s.name for s in symbols] == [
      'buildout',
  ]
  assert [s.range for s in symbols] == [
      Range(start=Position(line=0, character=0),
            end=Position(line=2, character=0)),
  ]

  assert symbols[0].children is not None
  assert [o.name for o in symbols[0].children] == [
      "option1",
      "option2",
  ]
  assert [o.range for o in symbols[0].children] == [
      Range(start=Position(line=1, character=0),
            end=Position(line=1, character=0)),
      Range(start=Position(line=2, character=0),
            end=Position(line=2, character=0)),
  ]

  params = DocumentSymbolParams(text_document=TextDocumentIdentifier(
      uri='file:///symbol/broken.cfg'))
  symbols = await lsp_symbols(server, params)
  assert symbols[0].children is not None
  assert [s.name for s in symbols] == ['a', 'c']
  assert [o.name for o in symbols[0].children] == ['b']


@pytest.mark.asyncio
async def test_complete_section_reference(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked, )
  # complete section names
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/sections.cfg"),
      position=Position(line=13, character=13),
      context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([(c.text_edit.range, c.text_edit.new_text) for c in completions
                 if c.text_edit is not None]) == [
                     (
                         Range(start=Position(line=13, character=10),
                               end=Position(line=13, character=13)),
                         '${buildout',
                     ),
                     (
                         Range(start=Position(line=13, character=10),
                               end=Position(line=13, character=13)),
                         '${section1',
                     ),
                     (
                         Range(start=Position(line=13, character=10),
                               end=Position(line=13, character=13)),
                         '${section2',
                     ),
                     (
                         Range(start=Position(line=13, character=10),
                               end=Position(line=13, character=13)),
                         '${section3',
                     ),
                     (
                         Range(start=Position(line=13, character=10),
                               end=Position(line=13, character=13)),
                         '${xsection4',
                     ),
                 ]

  # edge cases: complete section names on a line with a ${section:ref}
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/sections.cfg"),
                            position=Position(line=4, character=32),
                            context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([(c.text_edit.range, c.text_edit.new_text) for c in completions
                 if c.text_edit is not None]) == [
                     (Range(start=Position(line=4, character=30),
                            end=Position(line=4, character=32)), '${buildout'),
                     (Range(start=Position(line=4, character=30),
                            end=Position(line=4, character=32)), '${section1'),
                     (Range(start=Position(line=4, character=30),
                            end=Position(line=4, character=32)), '${section2'),
                     (Range(start=Position(line=4, character=30),
                            end=Position(line=4, character=32)), '${section3'),
                     (Range(start=Position(line=4, character=30),
                            end=Position(line=4,
                                         character=32)), '${xsection4'),
                 ]

  # in documentation we show the section content
  documentation, = [
      c.documentation for c in completions if c.label == 'section1'
  ]
  assert isinstance(documentation, MarkupContent)
  assert documentation.kind == MarkupKind.Markdown
  assert documentation.value == textwrap.dedent('''\
      ```ini
      option1 = value1
      ```''')

  # section names of known recipes also have description in markdown for documentation
  documentation, = [
      c.documentation for c in completions if c.label == 'section3'
  ]
  assert isinstance(documentation, MarkupContent)
  assert (documentation.value == textwrap.dedent('''\
      ## `plone.recipe.command`

      ---
      The `plone.recipe.command` buildout recipe allows you to run a command when a buildout part is installed or updated.

      ---
      ```ini
      recipe = plone.recipe.command
      option4 = value4
      ```'''))

  # test completions from various positions where all sections are suggested
  for (completion_position, textEditRange) in (
      (Position(line=5, character=10),
       Range(start=Position(line=5, character=10),
             end=Position(line=5, character=20))),
      (Position(line=5, character=17),
       Range(start=Position(line=5, character=10),
             end=Position(line=5, character=20))),
      (Position(line=5, character=32),
       Range(start=Position(line=5, character=30),
             end=Position(line=5, character=40))),
      (Position(line=5, character=34),
       Range(start=Position(line=5, character=30),
             end=Position(line=5, character=40))),
      (Position(line=5, character=40),
       Range(start=Position(line=5, character=30),
             end=Position(line=5, character=40))),
      (Position(line=5, character=52),
       Range(start=Position(line=5, character=50),
             end=Position(line=5, character=60))),
      (Position(line=5, character=56),
       Range(start=Position(line=5, character=50),
             end=Position(line=5, character=60))),
  ):
    params = CompletionParams(text_document=TextDocumentIdentifier(
        uri="file:///completions/sections.cfg"),
                              position=completion_position,
                              context=context)
    completions = await lsp_completion(server, params)
    assert completions is not None
    assert sorted([
        (c.text_edit.range, c.text_edit.new_text, c.filter_text, c.label)
        for c in completions if c.text_edit is not None
    ]) == [
        (textEditRange, '${buildout', '${buildout', 'buildout'),
        (textEditRange, '${section1', '${section1', 'section1'),
        (textEditRange, '${section2', '${section2', 'section2'),
        (textEditRange, '${section3', '${section3', 'section3'),
        (textEditRange, '${xsection4', '${xsection4', 'xsection4'),
    ]


@pytest.mark.asyncio
async def test_complete_option_reference(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked)

  # complete referenced options
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/options.cfg"),
                            position=Position(line=1, character=21),
                            context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
      '_buildout_section_name_', '_profile_base_location_', 'option2', 'recipe'
  ]

  # complete referenced options, including recipe generated options
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/recipe.cfg"),
                            position=Position(line=8, character=41),
                            context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
      '_buildout_section_name_', '_profile_base_location_', 'location',
      'recipe', 'repository'
  ]

  # complete referenced options from current section
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/options.cfg"),
                            position=Position(line=2, character=13),
                            context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  # options of section1
  assert sorted([c.label for c in completions]) == [
      '_buildout_section_name_',
      '_profile_base_location_',
      'option1',
      'option2',
      'option3',
  ]

  assert sorted([(c.text_edit.range, c.text_edit.new_text) for c in completions
                 if c.text_edit is not None]) == [
                     (
                         Range(start=Position(line=2, character=13),
                               end=Position(line=2, character=13)),
                         '_buildout_section_name_}',
                     ),
                     (
                         Range(start=Position(line=2, character=13),
                               end=Position(line=2, character=13)),
                         '_profile_base_location_}',
                     ),
                     (
                         Range(start=Position(line=2, character=13),
                               end=Position(line=2, character=13)),
                         'option1}',
                     ),
                     (
                         Range(start=Position(line=2, character=13),
                               end=Position(line=2, character=13)),
                         'option2}',
                     ),
                     (
                         Range(start=Position(line=2, character=13),
                               end=Position(line=2, character=13)),
                         'option3}',
                     ),
                 ]

  # options has values for docstrings
  documentation, = [
      c.documentation for c in completions if c.label == 'option3'
  ]
  assert isinstance(documentation, MarkupContent)
  assert documentation.kind == MarkupKind.Markdown
  assert documentation.value == '```\nvalue3```'

  # more complex replace text scenarios
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/options.cfg"),
                            position=Position(line=13, character=53),
                            context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([(c.text_edit.range, c.text_edit.new_text) for c in completions
                 if c.text_edit is not None]) == [
                     (
                         Range(start=Position(line=13, character=51),
                               end=Position(line=13, character=59)),
                         '_buildout_section_name_}',
                     ),
                     (
                         Range(start=Position(line=13, character=51),
                               end=Position(line=13, character=59)),
                         '_profile_base_location_}',
                     ),
                     (
                         Range(start=Position(line=13, character=51),
                               end=Position(line=13, character=59)),
                         'option1}',
                     ),
                     (
                         Range(start=Position(line=13, character=51),
                               end=Position(line=13, character=59)),
                         'option2}',
                     ),
                     (
                         Range(start=Position(line=13, character=51),
                               end=Position(line=13, character=59)),
                         'option3}',
                     ),
                 ]

  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/options.cfg"),
                            position=Position(line=14, character=53),
                            context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([(c.text_edit.range, c.text_edit.new_text) for c in completions
                 if c.text_edit is not None]) == [
                     (
                         Range(start=Position(line=14, character=51),
                               end=Position(line=14, character=58)),
                         '_buildout_section_name_}',
                     ),
                     (
                         Range(start=Position(line=14, character=51),
                               end=Position(line=14, character=58)),
                         '_profile_base_location_}',
                     ),
                     (
                         Range(start=Position(line=14, character=51),
                               end=Position(line=14, character=58)),
                         'option1}',
                     ),
                     (
                         Range(start=Position(line=14, character=51),
                               end=Position(line=14, character=58)),
                         'option2}',
                     ),
                     (
                         Range(start=Position(line=14, character=51),
                               end=Position(line=14, character=58)),
                         'option3}',
                     ),
                 ]


@pytest.mark.asyncio
async def test_complete_option_name(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked, )
  # complete options of a section
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/options.cfg"),
                            position=Position(line=8, character=0),
                            context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  # completion includes known options of the recipe and already defined
  # options, for cases where user wants to override an already defined
  # option
  assert sorted([c.label for c in completions]) == [
      'command',
      'location',
      'option2',
      'recipe',
      'stop-on-error',
      'update-command',
  ]

  # we insert with the = like: option =
  textEdit, = [c.text_edit for c in completions if c.label == 'command']
  assert textEdit is not None
  assert textEdit.range == Range(start=Position(line=8, character=0),
                                 end=Position(line=8, character=0))
  assert textEdit.new_text == 'command = '
  assert [
      c.documentation.value for c in completions
      if c.label == 'command' and isinstance(c.documentation, MarkupContent)
  ] == ['Command to run when the buildout part is installed.']

  # when there's no recipe we offer completion for "recipe"
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/options.cfg"),
                            position=Position(line=10, character=1),
                            context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == ['recipe']
  assert sorted([
      c.text_edit.new_text for c in completions if c.text_edit is not None
  ]) == ['recipe = ']

  # Also works when document has invalid syntax
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///diagnostics/syntax_error.cfg"),
                            position=Position(line=3, character=0),
                            context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == ['option1', 'recipe']
  assert sorted([
      c.text_edit.new_text for c in completions if c.text_edit is not None
  ]) == ['option1 = ', 'recipe = ']


@pytest.mark.asyncio
async def test_complete_referenced_option_recipe_valid_values(
    server: LanguageServer):
  # complete option values with recipe valid values
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/option_definitions.cfg"),
                            position=Position(line=2, character=16),
                            context=CompletionContext(
                                trigger_kind=CompletionTriggerKind.Invoked, ))
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == ['true', 'yes']
  assert sorted([
      c.text_edit.new_text for c in completions if c.text_edit is not None
  ]) == ['true', 'yes']


@pytest.mark.asyncio
async def test_complete_recipe_option_value(server: LanguageServer):
  # complete recipe= with known recipes
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/recipe.cfg"),
      position=Position(line=1, character=18),
      context=CompletionContext(trigger_kind=CompletionTriggerKind.Invoked))
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert 'plone.recipe.command' in [c.label for c in completions]
  assert [
      c.text_edit.new_text for c in completions
      if c.text_edit is not None and c.label == 'plone.recipe.command'
  ] == ['plone.recipe.command']
  assert [
      c.text_edit.range for c in completions
      if c.text_edit is not None and c.label == 'plone.recipe.command'
  ] == [
      Range(start=Position(line=1, character=9),
            end=Position(line=1, character=18))
  ]


@pytest.mark.asyncio
async def test_complete_macro_option_value(server: LanguageServer):
  # complete <= with parts
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/buildout.cfg"),
      position=Position(line=18, character=3),
      context=CompletionContext(trigger_kind=CompletionTriggerKind.Invoked))
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert [c.label for c in completions] == [
      'section1',
      'section2',
      'section3',
  ]


@pytest.mark.asyncio
async def test_complete_insert_text(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked, )
  # Only insert the text after the latest -
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/partial_completions.cfg"),
      position=Position(line=1, character=24),
      context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  completion, = [c for c in completions if c.label == 'sec-tion-one']
  assert completion.text_edit is not None
  assert completion.text_edit.range == Range(start=Position(line=1,
                                                            character=18),
                                             end=Position(line=1,
                                                          character=24))
  assert completion.text_edit.new_text == '${sec-tion-one'
  # we set a filter text, because the inserted text is different from the label
  assert completion.filter_text == '${sec-tion-one'

  # Only insert the text after the latest .
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/partial_completions.cfg"),
      position=Position(line=2, character=24),
      context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  completion, = [c for c in completions if c.label == 'sect.ion.three']
  assert completion.text_edit is not None
  assert completion.text_edit.range == Range(start=Position(line=2,
                                                            character=17),
                                             end=Position(line=2,
                                                          character=24))
  assert completion.text_edit.new_text == '${sect.ion.three'


@pytest.mark.asyncio
async def test_goto_definition(server: LanguageServer):
  params = TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(
          uri='file:///extended/with_references.cfg'),
      position=Position(line=5, character=23),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == [
      Location(uri='file:///buildout.cfg',
               range=Range(start=Position(line=5, character=9),
                           end=Position(line=5, character=31)))
  ]


@pytest.mark.asyncio
async def test_complete_buildout_options(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked, )
  # complete known buildout options
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/empty_buildout.cfg"),
                            position=Position(line=1, character=0),
                            context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert 'extends' in [c.label for c in completions]
  assert 'parts' in [c.label for c in completions]
  assert 'allow-hosts' in [c.label for c in completions]
  assert 'allow-picked-versions' in [c.label for c in completions]


@pytest.mark.asyncio
async def test_complete_buildout_parts(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked, )
  # complete buildout:parts with existing parts
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/buildout.cfg"),
                            position=Position(line=1, character=8),
                            context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
      'section1',
      'section2',
      'section3',
  ]


@pytest.mark.asyncio
async def test_complete_buildout_extends(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked, )
  # complete buildout:extends with local files
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/buildout.cfg"),
                            position=Position(line=2, character=12),
                            context=context)

  completions = await lsp_completion(server, params)
  assert completions is not None
  assert "buildout.cfg" in [c.label for c in completions]
  assert "not_buildout.txt" not in [c.label for c in completions]
  assert "../buildout.cfg" in [c.label for c in completions]
  assert "../symbol/buildout.cfg" in [c.label for c in completions]

  # multi lines
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/buildout.cfg"),
                            position=Position(line=7, character=7),
                            context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert "buildout.cfg" in [c.label for c in completions]
  assert "not_buildout.txt" not in [c.label for c in completions]
  assert "../buildout.cfg" in [c.label for c in completions]
  assert "../symbol/buildout.cfg" in [c.label for c in completions]

  # multi line on empty line
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/buildout.cfg"),
                            position=Position(line=8, character=4),
                            context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert "buildout.cfg" in [c.label for c in completions]
  assert "not_buildout.txt" not in [c.label for c in completions]
  assert "../buildout.cfg" in [c.label for c in completions]
  assert "../symbol/buildout.cfg" in [c.label for c in completions]

  # multi line with existing text
  params = CompletionParams(text_document=TextDocumentIdentifier(
      uri="file:///completions/buildout.cfg"),
                            position=Position(line=10, character=10),
                            context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert "buildout.cfg" in [c.label for c in completions]
  assert "not_buildout.txt" not in [c.label for c in completions]
  assert "../buildout.cfg" in [c.label for c in completions]
  assert "../symbol/buildout.cfg" in [c.label for c in completions]
  completion, = [c for c in completions if c.label == '../symbol/buildout.cfg']
  assert completion.text_edit is not None
  assert completion.text_edit.new_text == '../symbol/buildout.cfg'
  assert completion.text_edit.range == Range(
      start=Position(line=10, character=4),
      end=Position(line=10, character=10),
  )


@pytest.mark.asyncio
async def test_goto_definition_unknown_option(server: LanguageServer):
  # location option in ${section1:location} is not explicitly defined,
  # in this case we jump to the section header
  params = TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(
          uri='file:///extended/with_references.cfg'),
      position=Position(line=6, character=35),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == [
      Location(uri='file:///buildout.cfg',
               range=Range(start=Position(line=3, character=0),
                           end=Position(line=4, character=0)))
  ]


@pytest.mark.asyncio
async def test_goto_definition_unknown_section(server: LanguageServer):
  params = TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(
          uri='file:///diagnostics/reference.cfg'),
      position=Position(line=1, character=21),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == []


@pytest.mark.asyncio
async def test_goto_definition_macro(server: LanguageServer):
  params = TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(
          uri='file:///extended/macros/buildout.cfg'),
      position=Position(line=9, character=6),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == [
      Location(uri='file:///extended/macros/buildout.cfg',
               range=Range(start=Position(line=0, character=0),
                           end=Position(line=1, character=0)))
  ]


@pytest.mark.asyncio
async def test_goto_definition_extended_profile(server: LanguageServer):
  params = TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(
          uri='file:///extended/buildout.cfg'),
      position=Position(line=2, character=5),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == [
      Location(uri='file:///extended/another/buildout.cfg',
               range=Range(start=Position(line=0, character=0),
                           end=Position(line=1, character=0)))
  ]


@pytest.mark.asyncio
async def test_document_link(server: LanguageServer):
  params = DocumentLinkParams(text_document=TextDocumentIdentifier(
      uri="file:///extended/buildout.cfg"))
  links = sorted(await lsp_document_link(server, params),
                 key=lambda l: l.range.start)
  assert [l.target for l in links] == [
      'file:///extended/another/buildout.cfg', 'file:///extended/extended.cfg'
  ]
  assert [l.range for l in links] == [
      Range(start=Position(line=2, character=4),
            end=Position(line=2, character=26)),
      Range(start=Position(line=3, character=4),
            end=Position(line=3, character=16)),
  ]

  # no links
  params = DocumentLinkParams(text_document=TextDocumentIdentifier(
      uri="file:///buildout.cfg"))
  links = sorted(await lsp_document_link(server, params),
                 key=lambda l: l.range.start)
  assert links == []

  # harder one
  params = DocumentLinkParams(text_document=TextDocumentIdentifier(
      uri="file:///extended/harder.cfg"))
  links = await lsp_document_link(server, params)
  links = sorted(await lsp_document_link(server, params),
                 key=lambda l: l.range.start)
  assert [l.target for l in links] == [
      'file:///extended/another/buildout.cfg',
      'https://example.com/buildout.cfg',
      'file:///buildout.cfg',
  ]
  assert [l.range for l in links] == [
      Range(start=Position(line=5, character=4),
            end=Position(line=5, character=37)),
      Range(start=Position(line=7, character=4),
            end=Position(line=7, character=36)),
      Range(start=Position(line=9, character=4),
            end=Position(line=9, character=19)),
  ]


@pytest.mark.asyncio
async def test_hover(server: LanguageServer):
  # on referenced option, hover show the option value
  hover = await lsp_hover(
      server,
      TextDocumentPositionParams(
          text_document=TextDocumentIdentifier(uri="file:///buildout.cfg"),
          position=Position(line=13, character=25)))
  assert hover is not None
  assert hover.contents == '```\necho install section1\n```'

  # on referenced section, hover show the section recipe
  hover = await lsp_hover(
      server,
      TextDocumentPositionParams(
          text_document=TextDocumentIdentifier(uri="file:///buildout.cfg"),
          position=Position(line=13, character=16)))
  assert hover is not None
  assert hover.contents == '```\nplone.recipe.command\n```'

  # on most places hover show nothing.
  hover = await lsp_hover(
      server,
      TextDocumentPositionParams(
          text_document=TextDocumentIdentifier(uri="file:///buildout.cfg"),
          position=Position(line=4, character=4)))
  assert hover is not None
  assert hover.contents == '```\n\n```'


@pytest.mark.asyncio
async def test_references_on_section_header(server: LanguageServer):
  references = await lsp_references(
      server,
      TextDocumentPositionParams(text_document=TextDocumentIdentifier(
          uri="file:///references/referenced.cfg"),
                                 position=Position(line=4, character=10)))

  reference1, reference2 = sorted(references, key=lambda l: l.range.start)
  assert reference1.uri.endswith('/references/buildout.cfg')
  assert reference1.range == Range(start=Position(line=8, character=10),
                                   end=Position(line=8, character=29))

  # this one is a <= macro
  assert reference2.uri.endswith('/references/buildout.cfg')
  assert reference2.range == Range(start=Position(line=11, character=2),
                                   end=Position(line=11, character=21))


@pytest.mark.asyncio
async def test_references_on_option_definition(server: LanguageServer):
  # ${referenced_section1:value1} is referenced once
  references = await lsp_references(
      server,
      TextDocumentPositionParams(text_document=TextDocumentIdentifier(
          uri="file:///references/referenced.cfg"),
                                 position=Position(line=1, character=2)))
  reference, = references
  assert reference.uri.endswith('/references/buildout.cfg')
  assert reference.range == Range(start=Position(line=5, character=30),
                                  end=Position(line=5, character=36))

  # ${referenced_section1:value2} is not referenced
  references = await lsp_references(
      server,
      TextDocumentPositionParams(text_document=TextDocumentIdentifier(
          uri="file:///references/referenced.cfg"),
                                 position=Position(line=2, character=2)))
  assert references == []


@pytest.mark.asyncio
async def test_references_on_option_reference(server: LanguageServer):
  references = await lsp_references(
      server,
      TextDocumentPositionParams(text_document=TextDocumentIdentifier(
          uri="file:///references/buildout.cfg"),
                                 position=Position(line=5, character=20)))
  reference, = references
  assert reference.uri.endswith('/references/buildout.cfg')
  assert reference.range == Range(start=Position(line=5, character=10),
                                  end=Position(line=5, character=29))


@pytest.mark.asyncio
async def test_references_on_section_reference(server: LanguageServer):
  references = await lsp_references(
      server,
      TextDocumentPositionParams(text_document=TextDocumentIdentifier(
          uri="file:///references/buildout.cfg"),
                                 position=Position(line=5, character=32)))
  reference, = references
  assert reference.uri.endswith('/references/buildout.cfg')
  assert reference.range == Range(start=Position(line=5, character=30),
                                  end=Position(line=5, character=36))


@pytest.mark.asyncio
async def test_references_from_parts(server: LanguageServer):
  references = await lsp_references(
      server,
      TextDocumentPositionParams(text_document=TextDocumentIdentifier(
          uri="file:///references/parts.cfg"),
                                 position=Position(line=5, character=4)))
  reference, = references
  assert reference.uri.endswith('/references/parts.cfg')
  assert reference.range == Range(start=Position(line=2, character=4),
                                  end=Position(line=2, character=22))
