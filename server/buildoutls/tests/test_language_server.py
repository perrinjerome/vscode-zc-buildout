import textwrap
import urllib.parse
from typing import List, Sequence
from unittest import mock

import pytest

from pygls.server import LanguageServer
from pygls.types import (
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


def getTextDocumentItem(workspace: Workspace, doc_uri: str) -> TextDocumentItem:
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
  await parseAndSendDiagnostics(server, 'file:///broken/syntax_error.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///broken/syntax_error.cfg',
      [mock.ANY],
  )
  diagnostic, = server.publish_diagnostics.call_args[0][1]
  assert diagnostic.range == Range(start=Position(2, 0), end=Position(3, 0))
  assert diagnostic.message == "ParseError: 'o\\n'"


@pytest.mark.asyncio
async def test_diagnostics_missing_section_error(server) -> None:
  # missing section error (a parse error handled differently)
  await parseAndSendDiagnostics(server,
                                'file:///broken/missing_section_error.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///broken/missing_section_error.cfg',
      [mock.ANY],
  )
  diagnostic, = server.publish_diagnostics.call_args[0][1]
  assert diagnostic.range == Range(start=Position(0, 0), end=Position(1, 0))
  assert diagnostic.message == textwrap.dedent("""\
      File contains no section headers.
      file: file:///broken/missing_section_error.cfg, line: 0
      'key = value'""")


@pytest.mark.asyncio
async def test_diagnostics_non_existent_sections(server) -> None:
  # warnings for reference to non existent options
  await parseAndSendDiagnostics(server, 'file:///broken/reference.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///broken/reference.cfg',
      [mock.ANY, mock.ANY],
  )
  diagnostics: Sequence[Diagnostic] = sorted(
      server.publish_diagnostics.call_args[0][1],
      key=lambda d: d.range.start,
  )
  assert diagnostics[0].severity == DiagnosticSeverity.Error
  assert diagnostics[0].range == Range(
      start=Position(1, 12), end=Position(1, 27))
  assert diagnostics[0].message == \
    "Section `missing_section` does not exist."
  assert diagnostics[1].range == Range(
      start=Position(2, 21), end=Position(2, 35))
  assert diagnostics[1].message == \
    "Option `missing_option` does not exist in `section2`."


@pytest.mark.asyncio
async def test_diagnostics_non_existent_sections_multiple_references_per_line(
    server,) -> None:
  # harder version, two errors on same line
  await parseAndSendDiagnostics(server, 'file:///broken/harder.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///broken/harder.cfg',
      [mock.ANY] * 8,
  )
  diagnostics = sorted(
      server.publish_diagnostics.call_args[0][1],
      key=lambda d: d.range.start,
  )
  assert diagnostics[0].severity == DiagnosticSeverity.Error
  assert diagnostics[0].range == Range(
      start=Position(1, 55), end=Position(1, 70))
  assert diagnostics[0].message == \
    "Section `missing_section` does not exist."
  assert diagnostics[1].range == Range(
      start=Position(1, 86), end=Position(1, 101))
  assert diagnostics[1].message == \
    "Section `missing_section` does not exist."
  assert diagnostics[2].range == Range(
      start=Position(1, 117), end=Position(1, 132))
  assert diagnostics[2].message == \
    "Section `missing_section` does not exist."

  assert diagnostics[3].range == Range(
      start=Position(2, 63), end=Position(2, 77))
  assert diagnostics[3].message == \
    "Option `missing_option` does not exist in `section`."
  assert diagnostics[4].range == Range(
      start=Position(2, 92), end=Position(2, 106))
  assert diagnostics[4].message == \
    "Option `missing_option` does not exist in `section`."
  assert diagnostics[5].range == Range(
      start=Position(2, 121), end=Position(2, 135))
  assert diagnostics[5].message == \
    "Option `missing_option` does not exist in `section`."

  assert diagnostics[6].range == Range(
      start=Position(5, 19), end=Position(5, 34))
  assert diagnostics[6].message == \
    "Section `missing_section` does not exist."
  assert diagnostics[7].range == Range(
      start=Position(6, 27), end=Position(6, 41))
  assert diagnostics[7].message == \
    "Option `missing_option` does not exist in `section`."


@pytest.mark.asyncio
async def test_diagnostics_required_recipe_option(server) -> None:
  await parseAndSendDiagnostics(server,
                                'file:///broken/recipe_required_option.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///broken/recipe_required_option.cfg',
      [mock.ANY],
  )
  diagnostics = sorted(
      server.publish_diagnostics.call_args[0][1],
      key=lambda d: d.range.start,
  )
  assert diagnostics[0].severity == DiagnosticSeverity.Error
  assert diagnostics[0].message == \
    "Missing required options for `plone.recipe.command`: `command`"
  assert diagnostics[0].range == Range(start=Position(6, 0), end=Position(7, 0))


@pytest.mark.asyncio
async def test_diagnostics_template(server) -> None:
  # syntax error
  await parseAndSendDiagnostics(server, 'file:///template.in')
  server.publish_diagnostics.assert_called_once_with(
      'file:///template.in',
      [mock.ANY, mock.ANY],
  )
  diagnostic1, diagnostic2 = server.publish_diagnostics.call_args[0][1]
  assert diagnostic1.range == Range(start=Position(4, 25), end=Position(4, 32))
  assert diagnostic1.message == "Section `missing` does not exist."

  assert diagnostic2.range == Range(start=Position(6, 33), end=Position(6, 47))
  assert diagnostic2.message == "Option `missing_option` does not exist in `section5`."


@pytest.mark.asyncio
async def test_diagnostics_buildout_parts(server) -> None:
  await parseAndSendDiagnostics(server, 'file:///broken/buildout_parts.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///broken/buildout_parts.cfg',
      [mock.ANY, mock.ANY],
  )
  diagnostic1, diagnostic2 = sorted(
      server.publish_diagnostics.call_args[0][1], key=lambda d: d.range.start)
  assert diagnostic1.message == "Section `b` has no recipe."
  assert diagnostic1.range == Range(start=Position(3, 4), end=Position(3, 5))

  assert diagnostic2.message == "Section `c` does not exist."
  assert diagnostic2.range == Range(start=Position(4, 4), end=Position(4, 5))


@pytest.mark.asyncio
async def test_diagnostics_buildout_parts_section_name_with_dot(server) -> None:
  # This test checks that we supports section name with dots or dash
  await parseAndSendDiagnostics(
      server, 'file:///broken/buildout_parts_section_name_with_dot.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///broken/buildout_parts_section_name_with_dot.cfg', [mock.ANY])
  diagnostic, = server.publish_diagnostics.call_args[0][1]
  assert diagnostic.message == "Section `c.d` has no recipe."
  assert diagnostic.range == Range(start=Position(1, 12), end=Position(1, 15))


@pytest.mark.asyncio
async def test_diagnostics_ok(server) -> None:
  # no false positives
  await parseAndSendDiagnostics(server, 'file:///ok.cfg')
  server.publish_diagnostics.assert_called_once_with('file:///ok.cfg', [])


@pytest.mark.asyncio
async def test_symbol(server: LanguageServer):
  params = DocumentSymbolParams(
      TextDocumentIdentifier('file:///symbol/buildout.cfg'))

  symbols = await lsp_symbols(server, params)
  assert [s.name for s in symbols] == [
      'section1',
      'section2',
      'section3',
  ]
  assert [s.range for s in symbols] == [
      Range(Position(0, 0), Position(1, 0)),
      Range(Position(3, 0), Position(5, 0)),
      Range(Position(7, 0), Position(12, 0)),
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
      Range(Position(4, 0), Position(4, 0)),
      Range(Position(5, 0), Position(5, 0)),
  ]

  assert symbols[2].children is not None
  assert [o.name for o in symbols[2].children] == [
      "recipe",
      "multi-line-option",
      "command",
  ]
  assert [s.range for s in symbols[2].children] == [
      Range(Position(8, 0), Position(8, 0)),
      Range(Position(9, 0), Position(11, 0)),
      Range(Position(12, 0), Position(12, 0)),
  ]

  params = DocumentSymbolParams(
      TextDocumentIdentifier('file:///symbol/with_default_section.cfg'))

  symbols = await lsp_symbols(server, params)
  assert [s.name for s in symbols] == [
      'buildout',
  ]
  assert [s.range for s in symbols] == [
      Range(Position(0, 0), Position(2, 0)),
  ]

  assert symbols[0].children is not None
  assert [o.name for o in symbols[0].children] == [
      "option1",
      "option2",
  ]
  assert [o.range for o in symbols[0].children] == [
      Range(Position(1, 0), Position(1, 0)),
      Range(Position(2, 0), Position(2, 0)),
  ]

  params = DocumentSymbolParams(
      TextDocumentIdentifier('file:///symbol/broken.cfg'))
  symbols = await lsp_symbols(server, params)
  assert symbols[0].children is not None
  assert [s.name for s in symbols] == ['a', 'c']
  assert [o.name for o in symbols[0].children] == ['b']


@pytest.mark.asyncio
async def test_complete_section_reference(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked,)
  # complete section names
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/sections.cfg"),
      position=Position(13, 13),
      context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
      'buildout',
      'section1',
      'section2',
      'section3',
      'xsection4',
  ]

  # edge case: complete section names on a line with a ${section:ref}
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/sections.cfg"),
      position=Position(4, 32),
      context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  # sections
  assert sorted([c.label for c in completions]) == [
      'buildout',
      'section1',
      'section2',
      'section3',
      'xsection4',
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


@pytest.mark.asyncio
async def test_complete_option_reference(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked)

  # complete referenced options
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/options.cfg"),
      position=Position(1, 21),
      context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
      '_buildout_section_name_', '_profile_base_location_', 'option2', 'recipe'
  ]

  # complete referenced options, including recipe generated options
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/recipe.cfg"),
      position=Position(8, 41),
      context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
      '_buildout_section_name_', '_profile_base_location_', 'location',
      'recipe', 'repository'
  ]

  # complete referenced options from current section
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/options.cfg"),
      position=Position(2, 13),
      context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  # options of xsection4
  assert sorted([c.label for c in completions]) == [
      '_buildout_section_name_',
      '_profile_base_location_',
      'option1',
      'option2',
      'option3',
  ]
  assert sorted([c.insertText for c in completions]) == [
      '_buildout_section_name_',
      '_profile_base_location_',
      'option1',
      'option2',
      'option3',
  ]

  # options has values for docstrings
  documentation, = [
      c.documentation for c in completions if c.label == 'option3'
  ]
  assert isinstance(documentation, MarkupContent)
  assert documentation.kind == MarkupKind.Markdown
  assert documentation.value == '```\nvalue3```'

  # complete options of a section (when document has invalid syntax)
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///broken/syntax_error.cfg"),
      position=Position(3, 0),
      context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
      'recipe',
  ]


@pytest.mark.asyncio
async def test_complete_option_name(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked,)
  # complete options of a section
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/options.cfg"),
      position=Position(8, 0),
      context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
      'command', 'location', 'stop-on-error', 'update-command'
  ]
  # we insert with the = like: option =
  assert [c.insertText for c in completions if c.label == 'command'
         ] == ['command = ']
  assert [
      c.documentation.value
      for c in completions
      if c.label == 'command' and isinstance(c.documentation, MarkupContent)
  ] == ['Command to run when the buildout part is installed.']

  # when there's no recipe, at least we try to complete "recipe"
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/options.cfg"),
      position=Position(10, 1),
      context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == ['recipe']


@pytest.mark.asyncio
async def test_complete_referenced_option_recipe_valid_values(
    server: LanguageServer):
  # complete option values with recipe valid values
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/option_definitions.cfg"),
      position=Position(2, 16),
      context=CompletionContext(trigger_kind=CompletionTriggerKind.Invoked,))
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == ['true', 'yes']


@pytest.mark.asyncio
async def test_complete_recipe_option_value(server: LanguageServer):
  # complete recipe= with known recipes
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/recipe.cfg"),
      position=Position(1, 18),
      context=CompletionContext(trigger_kind=CompletionTriggerKind.Invoked))
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert 'plone.recipe.command' in [c.label for c in completions]
  assert [
      c.insertText for c in completions if c.label == 'plone.recipe.command'
  ] == ['recipe.command']


@pytest.mark.asyncio
async def test_complete_macro_option_value(server: LanguageServer):
  # complete <= with parts
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/buildout.cfg"),
      position=Position(18, 3),
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
  # Only insert the last "word". This is made to accomodate vscode, the spec
  # does not seem to document how editor should behave for this.
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked,)
  # Only insert the text after the latest -
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/partial_completions.cfg"),
      position=Position(1, 24),
      context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert [c.insertText for c in completions if c.label == 'sec-tion-one'
         ] == ['tion-one']

  # Only insert the text after the latest .
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/partial_completions.cfg"),
      position=Position(1, 24),
      context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert [c.insertText for c in completions if c.label == 'sect.ion.three'
         ] == ['.ion.three']


@pytest.mark.asyncio
async def test_goto_definition(server: LanguageServer):
  params = TextDocumentPositionParams(
      TextDocumentIdentifier(uri='file:///extended/with_references.cfg'),
      Position(5, 23),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == [
      Location(
          uri='file:///buildout.cfg',
          range=Range(start=Position(5, 9), end=Position(5, 31)))
  ]


@pytest.mark.asyncio
async def test_complete_buildout_options(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked,)
  # complete known buildout options
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/empty_buildout.cfg"),
      position=Position(1, 0),
      context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert 'extends' in [c.label for c in completions]
  assert 'parts' in [c.label for c in completions]
  assert 'allow-hosts' in [c.label for c in completions]
  assert 'allow-picked-versions' in [c.label for c in completions]


@pytest.mark.asyncio
async def test_complete_buildout_parts(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked,)
  # complete buildout:parts with existing parts
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/buildout.cfg"),
      position=Position(1, 8),
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
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked,)
  # complete buildout:extends with local files
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/buildout.cfg"),
      position=Position(2, 12),
      context=context)

  completions = await lsp_completion(server, params)
  assert completions is not None
  assert "buildout.cfg" in [c.label for c in completions]
  assert "not_buildout.txt" not in [c.label for c in completions]
  assert "../buildout.cfg" in [c.label for c in completions]
  assert "../symbol/buildout.cfg" in [c.label for c in completions]
  assert "../symbol/buildout.cfg" in [c.label for c in completions]

  # multi lines
  params = CompletionParams(
      text_document=TextDocumentIdentifier(
          uri="file:///completions/buildout.cfg"),
      position=Position(7, 7),
      context=context)
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert "buildout.cfg" in [c.label for c in completions]
  assert "not_buildout.txt" not in [c.label for c in completions]
  assert "../buildout.cfg" in [c.label for c in completions]
  assert "../symbol/buildout.cfg" in [c.label for c in completions]
  assert "../symbol/buildout.cfg" in [c.label for c in completions]


@pytest.mark.asyncio
async def test_goto_definition_unknown_option(server: LanguageServer):
  # location option in ${section1:location} is not explicitly defined,
  # in this case we jump to the section header
  params = TextDocumentPositionParams(
      TextDocumentIdentifier(uri='file:///extended/with_references.cfg'),
      Position(6, 35),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == [
      Location(
          uri='file:///buildout.cfg',
          range=Range(start=Position(3, 0), end=Position(4, 0)))
  ]


@pytest.mark.asyncio
async def test_goto_definition_unknown_section(server: LanguageServer):
  params = TextDocumentPositionParams(
      TextDocumentIdentifier(uri='file:///broken/reference.cfg'),
      Position(1, 21),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == []


@pytest.mark.asyncio
async def test_goto_definition_macro(server: LanguageServer):
  params = TextDocumentPositionParams(
      TextDocumentIdentifier(uri='file:///extended/macros/buildout.cfg'),
      Position(9, 6),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == [
      Location(
          uri='file:///extended/macros/buildout.cfg',
          range=Range(start=Position(0, 0), end=Position(1, 0)))
  ]


@pytest.mark.asyncio
async def test_goto_definition_extended_profile(server: LanguageServer):
  params = TextDocumentPositionParams(
      TextDocumentIdentifier(uri='file:///extended/buildout.cfg'),
      Position(2, 5),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == [
      Location(
          uri='file:///extended/another/buildout.cfg',
          range=Range(start=Position(0, 0), end=Position(1, 0)))
  ]


@pytest.mark.asyncio
async def test_document_link(server: LanguageServer):
  params = DocumentLinkParams(
      text_document=TextDocumentIdentifier(uri="file:///extended/buildout.cfg"))
  links = sorted(
      await lsp_document_link(server, params), key=lambda l: l.range.start)
  assert [l.target for l in links] == [
      'file:///extended/another/buildout.cfg', 'file:///extended/extended.cfg'
  ]
  assert [l.range for l in links] == [
      Range(Position(2, 4), Position(2, 26)),
      Range(Position(3, 4), Position(3, 16)),
  ]

  # no links
  params = DocumentLinkParams(
      text_document=TextDocumentIdentifier(uri="file:///buildout.cfg"))
  links = sorted(
      await lsp_document_link(server, params), key=lambda l: l.range.start)
  assert links == []

  # harder one
  params = DocumentLinkParams(
      text_document=TextDocumentIdentifier(uri="file:///extended/harder.cfg"))
  links = await lsp_document_link(server, params)
  links = sorted(
      await lsp_document_link(server, params), key=lambda l: l.range.start)
  assert [l.target for l in links] == [
      'file:///extended/another/buildout.cfg',
      'https://example.com/buildout.cfg',
      'file:///buildout.cfg',
  ]
  assert [l.range for l in links] == [
      Range(Position(5, 4), Position(5, 37)),
      Range(Position(7, 4), Position(7, 36)),
      Range(Position(9, 4), Position(9, 19)),
  ]


@pytest.mark.asyncio
async def test_hover(server: LanguageServer):
  # on referenced option, hover show the option value
  hover = await lsp_hover(
      server,
      TextDocumentPositionParams(
          text_document=TextDocumentIdentifier(uri="file:///buildout.cfg"),
          position=Position(13, 25)))
  assert hover is not None
  assert hover.contents == '```\necho install section1\n```'

  # on referenced section, hover show the section recipe
  hover = await lsp_hover(
      server,
      TextDocumentPositionParams(
          text_document=TextDocumentIdentifier(uri="file:///buildout.cfg"),
          position=Position(13, 16)))
  assert hover is not None
  assert hover.contents == '```\nplone.recipe.command\n```'

  # on most places hover show nothing.
  hover = await lsp_hover(
      server,
      TextDocumentPositionParams(
          text_document=TextDocumentIdentifier(uri="file:///buildout.cfg"),
          position=Position(4, 4)))
  assert hover is not None
  assert hover.contents == '```\n\n```'


@pytest.mark.asyncio
async def test_references_on_section_header(server: LanguageServer):
  references = await lsp_references(
      server,
      TextDocumentPositionParams(
          text_document=TextDocumentIdentifier(
              uri="file:///references/referenced.cfg"),
          position=Position(4, 10)))

  def sort_key(l: Location):
    return l.range.start

  reference1, reference2 = sorted(references, key=lambda l: l.range.start)
  assert reference1.uri.endswith('/references/buildout.cfg')
  assert reference1.range == Range(Position(8, 10), Position(8, 29))

  # this one is a <= macro
  assert reference2.uri.endswith('/references/buildout.cfg')
  assert reference2.range == Range(Position(11, 2), Position(11, 21))


@pytest.mark.asyncio
async def test_references_on_option_definition(server: LanguageServer):
  # ${referenced_section1:value1} is referenced once
  references = await lsp_references(
      server,
      TextDocumentPositionParams(
          text_document=TextDocumentIdentifier(
              uri="file:///references/referenced.cfg"),
          position=Position(1, 2)))
  reference, = references
  assert reference.uri.endswith('/references/buildout.cfg')
  assert reference.range == Range(Position(5, 30), Position(5, 36))

  # ${referenced_section1:value2} is not referenced
  references = await lsp_references(
      server,
      TextDocumentPositionParams(
          text_document=TextDocumentIdentifier(
              uri="file:///references/referenced.cfg"),
          position=Position(2, 2)))
  assert references == []


@pytest.mark.asyncio
async def test_references_on_option_reference(server: LanguageServer):
  references = await lsp_references(
      server,
      TextDocumentPositionParams(
          text_document=TextDocumentIdentifier(
              uri="file:///references/buildout.cfg"),
          position=Position(5, 20)))
  reference, = references
  assert reference.uri.endswith('/references/buildout.cfg')
  assert reference.range == Range(Position(5, 10), Position(5, 29))


@pytest.mark.asyncio
async def test_references_on_section_reference(server: LanguageServer):
  references = await lsp_references(
      server,
      TextDocumentPositionParams(
          text_document=TextDocumentIdentifier(
              uri="file:///references/buildout.cfg"),
          position=Position(5, 32)))
  reference, = references
  assert reference.uri.endswith('/references/buildout.cfg')
  assert reference.range == Range(Position(5, 30), Position(5, 36))
