import pytest

from pygls.server import LanguageServer
from pygls.lsp.types import (
    Position,
    TextDocumentIdentifier,
    TextDocumentPositionParams,
)

from ..server import lsp_hover


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
