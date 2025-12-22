import pytest
from lsprotocol.types import (
  Position,
  Range,
  TextDocumentIdentifier,
  ReferenceParams,
  ReferenceContext,
)
from pygls.lsp.server import LanguageServer

from ..server import lsp_references


@pytest.mark.usefixtures("bad_encoding_file")
async def test_references_on_section_header(server: LanguageServer):
  references = await lsp_references(
    server,
    ReferenceParams(
      context=ReferenceContext(include_declaration=False),
      text_document=TextDocumentIdentifier(uri="file:///references/referenced.cfg"),
      position=Position(line=4, character=10),
    ),
  )

  reference1, reference2 = sorted(references, key=lambda loc: loc.range.start)
  assert reference1.uri.endswith("/references/buildout.cfg")
  assert reference1.range == Range(
    start=Position(line=8, character=10), end=Position(line=8, character=29)
  )

  # this one is a <= macro
  assert reference2.uri.endswith("/references/buildout.cfg")
  assert reference2.range == Range(
    start=Position(line=11, character=2), end=Position(line=11, character=21)
  )


@pytest.mark.usefixtures("bad_encoding_file")
async def test_references_on_option_definition(server: LanguageServer):
  # ${referenced_section1:value1} is referenced once
  references = await lsp_references(
    server,
    ReferenceParams(
      context=ReferenceContext(include_declaration=False),
      text_document=TextDocumentIdentifier(uri="file:///references/referenced.cfg"),
      position=Position(line=1, character=2),
    ),
  )
  (reference,) = references
  assert reference.uri.endswith("/references/buildout.cfg")
  assert reference.range == Range(
    start=Position(line=5, character=30), end=Position(line=5, character=36)
  )

  # ${referenced_section1:value2} is not referenced
  references = await lsp_references(
    server,
    ReferenceParams(
      context=ReferenceContext(include_declaration=False),
      text_document=TextDocumentIdentifier(uri="file:///references/referenced.cfg"),
      position=Position(line=2, character=2),
    ),
  )
  assert references == []


@pytest.mark.usefixtures("bad_encoding_file")
async def test_references_on_option_reference(server: LanguageServer):
  references = await lsp_references(
    server,
    ReferenceParams(
      context=ReferenceContext(include_declaration=False),
      text_document=TextDocumentIdentifier(uri="file:///references/buildout.cfg"),
      position=Position(line=5, character=20),
    ),
  )
  (reference,) = references
  assert reference.uri.endswith("/references/buildout.cfg")
  assert reference.range == Range(
    start=Position(line=5, character=10), end=Position(line=5, character=29)
  )


@pytest.mark.usefixtures("bad_encoding_file")
async def test_references_on_section_reference(server: LanguageServer):
  references = await lsp_references(
    server,
    ReferenceParams(
      context=ReferenceContext(include_declaration=False),
      text_document=TextDocumentIdentifier(uri="file:///references/buildout.cfg"),
      position=Position(line=5, character=32),
    ),
  )
  (reference,) = references
  assert reference.uri.endswith("/references/buildout.cfg")
  assert reference.range == Range(
    start=Position(line=5, character=30), end=Position(line=5, character=36)
  )


@pytest.mark.usefixtures("bad_encoding_file")
async def test_references_from_parts(server: LanguageServer):
  references = await lsp_references(
    server,
    ReferenceParams(
      context=ReferenceContext(include_declaration=False),
      text_document=TextDocumentIdentifier(uri="file:///references/parts.cfg"),
      position=Position(line=5, character=4),
    ),
  )
  (reference,) = references
  assert reference.uri.endswith("/references/parts.cfg")
  assert reference.range == Range(
    start=Position(line=2, character=4), end=Position(line=2, character=22)
  )
