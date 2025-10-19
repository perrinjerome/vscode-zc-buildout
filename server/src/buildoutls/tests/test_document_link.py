from lsprotocol.types import (
  DocumentLinkParams,
  Position,
  Range,
  TextDocumentIdentifier,
)
from pygls.lsp.server import LanguageServer

from ..server import lsp_document_link


async def test_document_link(server: LanguageServer):
  params = DocumentLinkParams(
    text_document=TextDocumentIdentifier(uri="file:///extended/buildout.cfg")
  )
  links = sorted(
    await lsp_document_link(server, params), key=lambda loc: loc.range.start
  )
  assert [loc.target for loc in links] == [
    "file:///extended/another/buildout.cfg",
    "file:///extended/extended.cfg",
  ]
  assert [loc.range for loc in links] == [
    Range(start=Position(line=2, character=4), end=Position(line=2, character=26)),
    Range(start=Position(line=3, character=4), end=Position(line=3, character=16)),
  ]

  # no links
  params = DocumentLinkParams(
    text_document=TextDocumentIdentifier(uri="file:///buildout.cfg")
  )
  links = sorted(
    await lsp_document_link(server, params), key=lambda loc: loc.range.start
  )
  assert links == []

  # harder one
  params = DocumentLinkParams(
    text_document=TextDocumentIdentifier(uri="file:///extended/harder.cfg")
  )
  links = await lsp_document_link(server, params)
  links = sorted(
    await lsp_document_link(server, params), key=lambda loc: loc.range.start
  )
  assert [loc.target for loc in links] == [
    "file:///extended/another/buildout.cfg",
    "https://example.com/buildout.cfg",
    "file:///buildout.cfg",
  ]
  assert [loc.range for loc in links] == [
    Range(start=Position(line=5, character=4), end=Position(line=5, character=37)),
    Range(start=Position(line=7, character=4), end=Position(line=7, character=36)),
    Range(start=Position(line=9, character=4), end=Position(line=9, character=19)),
  ]
