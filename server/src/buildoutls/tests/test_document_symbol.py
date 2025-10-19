import pytest
from lsprotocol.types import (
  DocumentSymbolParams,
  Position,
  Range,
  TextDocumentIdentifier,
)
from pygls.lsp.server import LanguageServer

from ..server import lsp_symbols


@pytest.mark.asyncio
async def test_symbol(server: LanguageServer):
  params = DocumentSymbolParams(
    text_document=TextDocumentIdentifier(uri="file:///symbol/buildout.cfg")
  )

  symbols = await lsp_symbols(server, params)
  assert [s.name for s in symbols] == [
    "section1",
    "section2",
    "section3",
  ]
  assert [s.range for s in symbols] == [
    Range(start=Position(line=0, character=0), end=Position(line=1, character=0)),
    Range(start=Position(line=3, character=0), end=Position(line=5, character=0)),
    Range(start=Position(line=7, character=0), end=Position(line=12, character=0)),
  ]
  assert [s.detail for s in symbols] == [
    "",
    "",
    "plone.recipe.command",
  ]
  assert symbols[1].children is not None
  assert [o.name for o in symbols[1].children] == [
    "option2",
    "option3",
  ]
  assert [o.detail for o in symbols[1].children] == [
    "${section1:option1}",
    "${section2:option2} ${section3:option4}",
  ]
  assert [s.range for s in symbols[1].children] == [
    Range(start=Position(line=4, character=0), end=Position(line=4, character=0)),
    Range(start=Position(line=5, character=0), end=Position(line=5, character=0)),
  ]

  assert symbols[2].children is not None
  assert [o.name for o in symbols[2].children] == [
    "recipe",
    "multi-line-option",
    "command",
  ]
  assert [s.range for s in symbols[2].children] == [
    Range(start=Position(line=8, character=0), end=Position(line=8, character=0)),
    Range(start=Position(line=9, character=0), end=Position(line=11, character=0)),
    Range(start=Position(line=12, character=0), end=Position(line=12, character=0)),
  ]

  params = DocumentSymbolParams(
    text_document=TextDocumentIdentifier(uri="file:///symbol/with_default_section.cfg")
  )

  symbols = await lsp_symbols(server, params)
  assert [s.name for s in symbols] == [
    "buildout",
  ]
  assert [s.range for s in symbols] == [
    Range(start=Position(line=0, character=0), end=Position(line=2, character=0)),
  ]

  assert symbols[0].children is not None
  assert [o.name for o in symbols[0].children] == [
    "option1",
    "option2",
  ]
  assert [o.range for o in symbols[0].children] == [
    Range(start=Position(line=1, character=0), end=Position(line=1, character=0)),
    Range(start=Position(line=2, character=0), end=Position(line=2, character=0)),
  ]

  params = DocumentSymbolParams(
    text_document=TextDocumentIdentifier(uri="file:///symbol/broken.cfg")
  )
  symbols = await lsp_symbols(server, params)
  assert symbols[0].children is not None
  assert [s.name for s in symbols] == ["a", "c"]
  assert [o.name for o in symbols[0].children] == ["b"]
