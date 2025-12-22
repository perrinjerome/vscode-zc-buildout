from lsprotocol.types import (
  Position,
  TextDocumentIdentifier,
  TextDocumentPositionParams,
)
from pygls.lsp.server import LanguageServer

from ..server import lsp_hover


async def test_hover(server: LanguageServer):
  # on option from a known recipe, show the option documentation
  hover = await lsp_hover(
    server,
    TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(uri="file:///buildout.cfg"),
      position=Position(line=26, character=4),
    ),
  )
  assert hover is not None
  assert hover.contents == "Command to run when the buildout part is installed."

  # on `recipe` option, show the recipe definition
  hover = await lsp_hover(
    server,
    TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(uri="file:///buildout.cfg"),
      position=Position(line=8, character=10),
    ),
  )
  assert hover is not None
  assert (
    hover.contents
    == """## `plone.recipe.command`

---
The `plone.recipe.command` buildout recipe allows you to run a command when a buildout part is installed or updated."""
  )

  # on referenced option, hover show the option value
  hover = await lsp_hover(
    server,
    TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(uri="file:///buildout.cfg"),
      position=Position(line=13, character=25),
    ),
  )
  assert hover is not None
  assert hover.contents == "```\necho install section1\n```"

  # on section header or referenced section, hover show the section documentation
  for pos in (
    Position(line=3, character=4),
    Position(line=13, character=16),
  ):
    hover = await lsp_hover(
      server,
      TextDocumentPositionParams(
        text_document=TextDocumentIdentifier(uri="file:///buildout.cfg"), position=pos
      ),
    )
    assert hover is not None
    assert (
      hover.contents
      == """## `plone.recipe.command`

---
The `plone.recipe.command` buildout recipe allows you to run a command when a buildout part is installed or updated.

---
```ini
recipe = plone.recipe.command
command = echo install section1
```"""
    )

  # on most places hover show nothing.
  for pos in (
    Position(line=4, character=4),
    Position(line=6, character=13),
    Position(line=28, character=5),
    Position(line=35, character=5),
  ):
    hover = await lsp_hover(
      server,
      TextDocumentPositionParams(
        text_document=TextDocumentIdentifier(uri="file:///buildout.cfg"),
        position=pos,
      ),
    )
    assert hover is not None
    assert hover.contents == ""


async def test_hover_jinja_section_name(server: LanguageServer):
  # hovering on a jinja section name like [{{ section }}] should not crash
  hover = await lsp_hover(
    server,
    TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(
        uri="file:///diagnostics/jinja-sections.cfg"
      ),
      position=Position(line=6, character=3),  # on [{{ section }}]
    ),
  )
  assert hover is not None
