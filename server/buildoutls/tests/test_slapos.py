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

from ..server import (
    lsp_completion,
    lsp_definition,
    lsp_document_link,
    lsp_hover,
    lsp_references,
    lsp_symbols,
    parseAndSendDiagnostics,
)

from ..buildout import (
    BuildoutProfile,
    open,
)
from unittest import mock


@pytest.mark.asyncio
async def test_complete_slapos_instance_software(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked,)
  # complete ${ with software
  params = CompletionParams(
      text_document=TextDocumentIdentifier(uri="file:///slapos/instance.cfg"),
      position=Position(14, 27),
      context=context)

  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
      'buildout',
      'instance',
      'software',
  ]


@pytest.mark.asyncio
async def test_complete_slapos_instance_instance(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked,)
  # complete $${ with instance
  params = CompletionParams(
      text_document=TextDocumentIdentifier(uri="file:///slapos/instance.cfg"),
      position=Position(15, 28),
      context=context)

  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
      'buildout',
      'directory',
      'publish',
      'service',
      'slap-connection',
      'slap-network-information',
      'template',
  ]


@pytest.mark.asyncio
async def test_complete_slapos_instance_template(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked,)

  # complete ${ in instance's template with instance
  params = CompletionParams(
      text_document=TextDocumentIdentifier(uri="file:///slapos/template.in"),
      position=Position(0, 75),
      context=context)

  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
      '_buildout_section_name_',
      '_profile_base_location_',
      'etc',
      'home',
      'inside_jinja',
      'recipe',
  ]


@pytest.mark.asyncio
async def test_goto_definition_slapos_instance_software(server: LanguageServer):
  definitions = await lsp_definition(
      server,
      TextDocumentPositionParams(
          TextDocumentIdentifier(uri='file:///slapos/instance.cfg'),
          Position(13, 23),
      ))
  assert definitions == [
      Location(
          uri='file:///slapos/software.cfg',
          range=Range(Position(5, 0), Position(6, 0)))
  ]


@pytest.mark.asyncio
async def test_goto_definition_slapos_instance_instance(server: LanguageServer):
  definitions = await lsp_definition(
      server,
      TextDocumentPositionParams(
          TextDocumentIdentifier(uri='file:///slapos/instance.cfg'),
          Position(12, 26),
      ))
  assert definitions == [
      Location(
          uri='file:///slapos/instance.cfg',
          range=Range(Position(7, 5), Position(7, 20)))
  ]


@pytest.mark.asyncio
async def test_goto_definition_slapos_instance_software_empty_section(
    server: LanguageServer):
  definitions = await lsp_definition(
      server,
      TextDocumentPositionParams(
          TextDocumentIdentifier(uri='file:///slapos/instance.cfg'),
          Position(7, 12),
      ))
  assert definitions == [
      Location(
          uri='file:///slapos/instance.cfg',
          range=Range(Position(6, 6), Position(6, 29)))
  ]


@pytest.mark.asyncio
async def test_goto_definition_slapos_instance_template(server: LanguageServer):
  definitions = await lsp_definition(
      server,
      TextDocumentPositionParams(
          TextDocumentIdentifier(uri='file:///slapos/template.in'),
          Position(0, 75),
      ))
  assert definitions == [
      Location(
          uri='file:///slapos/instance.cfg',
          range=Range(Position(6, 6), Position(6, 29)))
  ]


@pytest.mark.asyncio
async def test_open_instance_type(server: LanguageServer):
  assert isinstance(
      await open(ls=server, uri='file:///slapos/instance.cfg'),
      BuildoutProfile,
  )


@pytest.mark.asyncio
async def test_diagnostic_instance(server) -> None:
  await parseAndSendDiagnostics(server, 'file:///slapos/instance.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///slapos/instance.cfg',
      [],
  )