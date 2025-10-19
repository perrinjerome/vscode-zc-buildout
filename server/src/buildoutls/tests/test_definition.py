from lsprotocol.types import (
  Location,
  Position,
  Range,
  TextDocumentIdentifier,
  TextDocumentPositionParams,
)
from pygls.lsp.server import LanguageServer

from ..server import lsp_definition


async def test_goto_definition(server: LanguageServer):
  params = TextDocumentPositionParams(
    text_document=TextDocumentIdentifier(uri="file:///extended/with_references.cfg"),
    position=Position(line=5, character=23),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == [
    Location(
      uri="file:///buildout.cfg",
      range=Range(
        start=Position(line=5, character=9), end=Position(line=5, character=31)
      ),
    )
  ]


async def test_goto_definition_unknown_option(server: LanguageServer):
  # location option in ${section1:location} is not explicitly defined,
  # in this case we jump to the section header
  params = TextDocumentPositionParams(
    text_document=TextDocumentIdentifier(uri="file:///extended/with_references.cfg"),
    position=Position(line=6, character=35),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == [
    Location(
      uri="file:///buildout.cfg",
      range=Range(
        start=Position(line=3, character=0), end=Position(line=4, character=0)
      ),
    )
  ]


async def test_goto_definition_unknown_section(server: LanguageServer):
  params = TextDocumentPositionParams(
    text_document=TextDocumentIdentifier(uri="file:///diagnostics/reference.cfg"),
    position=Position(line=1, character=21),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == []


async def test_goto_definition_macro(server: LanguageServer):
  params = TextDocumentPositionParams(
    text_document=TextDocumentIdentifier(uri="file:///extended/macros/buildout.cfg"),
    position=Position(line=9, character=6),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == [
    Location(
      uri="file:///extended/macros/buildout.cfg",
      range=Range(
        start=Position(line=0, character=0), end=Position(line=1, character=0)
      ),
    )
  ]


async def test_goto_definition_extended_profile(server: LanguageServer):
  params = TextDocumentPositionParams(
    text_document=TextDocumentIdentifier(uri="file:///extended/buildout.cfg"),
    position=Position(line=2, character=5),
  )
  definitions = await lsp_definition(server, params)
  assert definitions == [
    Location(
      uri="file:///extended/another/buildout.cfg",
      range=Range(
        start=Position(line=0, character=0), end=Position(line=1, character=0)
      ),
    )
  ]
