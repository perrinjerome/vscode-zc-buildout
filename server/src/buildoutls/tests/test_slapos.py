from lsprotocol.types import (
  CompletionContext,
  CompletionParams,
  CompletionTriggerKind,
  Location,
  Position,
  PublishDiagnosticsParams,
  Range,
  TextDocumentIdentifier,
  TextDocumentPositionParams,
  TextEdit,
)
from pygls.lsp.server import LanguageServer

from ..buildout import BuildoutProfile, open
from ..server import (
  lsp_completion,
  lsp_definition,
  lsp_hover,
  parseAndSendDiagnostics,
)


async def test_complete_slapos_instance_software(server: LanguageServer):
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )
  # complete ${ with software
  params = CompletionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///slapos/instance_as_buildout_profile/instance.cfg"
    ),
    position=Position(line=14, character=27),
    context=context,
  )

  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
    "buildout",
    "instance",
    "software",
  ]


async def test_complete_slapos_instance_instance(server: LanguageServer):
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )
  # complete $${ with instance
  params = CompletionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///slapos/instance_as_buildout_profile/instance.cfg"
    ),
    position=Position(line=15, character=28),
    context=context,
  )

  completions = await lsp_completion(server, params)
  assert completions is not None
  textEditRange = Range(
    start=Position(line=15, character=26), end=Position(line=15, character=28)
  )
  assert sorted(
    [
      (c.text_edit.range, c.text_edit.new_text, c.filter_text, c.label)
      for c in completions
      if isinstance(c.text_edit, TextEdit)
    ]
  ) == [
    (
      textEditRange,
      "${buildout",
      "${buildout",
      "buildout",
    ),
    (
      textEditRange,
      "${directory",
      "${directory",
      "directory",
    ),
    (
      textEditRange,
      "${publish",
      "${publish",
      "publish",
    ),
    (
      textEditRange,
      "${service",
      "${service",
      "service",
    ),
    (
      textEditRange,
      "${slap-connection",
      "${slap-connection",
      "slap-connection",
    ),
    (
      textEditRange,
      "${slap-network-information",
      "${slap-network-information",
      "slap-network-information",
    ),
    (
      textEditRange,
      "${template",
      "${template",
      "template",
    ),
  ]
  params = CompletionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///slapos/instance_as_buildout_profile/instance.cfg"
    ),
    position=Position(line=13, character=61),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  textEditRange = Range(
    start=Position(line=13, character=60), end=Position(line=13, character=71)
  )
  assert sorted(
    [
      (c.text_edit.range, c.text_edit.new_text, c.label)
      for c in completions
      if isinstance(c.text_edit, TextEdit)
    ]
  ) == [
    (
      textEditRange,
      "cert-file}",
      "cert-file",
    ),
    (
      textEditRange,
      "computer-id}",
      "computer-id",
    ),
    (
      textEditRange,
      "key-file}",
      "key-file",
    ),
    (
      textEditRange,
      "partition-id}",
      "partition-id",
    ),
    (
      textEditRange,
      "server-url}",
      "server-url",
    ),
    (
      textEditRange,
      "software-release-url}",
      "software-release-url",
    ),
  ]


async def test_complete_slapos_instance_instance_jinja(server: LanguageServer):
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )
  # in jinja instance, complete ${ with instance
  params = CompletionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///slapos/instance_as_jinja/instance.cfg.in"
    ),
    position=Position(line=18, character=27),
    context=context,
  )

  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
    "buildout",
    "directory",
    "publish",
    "service",
    "slap-connection",
    "slap-network-information",
  ]


async def XXXXtest_complete_slapos_instance_with_unknown_extends(
  server: LanguageServer,
):
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )
  params = CompletionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///slapos/instance_with_unknown_extends/instance.cfg.in"
    ),
    position=Position(line=9, character=12),
    context=context,
  )

  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
    "buildout",
    "directory",
    "publish",
    "service",
    "slap-connection",
    "slap-network-information",
  ]


async def test_hover_slapos_instance(server: LanguageServer):
  hover = await lsp_hover(
    server,
    TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(
        uri="file:///slapos/instance_as_buildout_profile/instance.cfg"
      ),
      position=Position(line=13, character=16),
    ),
  )
  assert hover is not None
  assert (
    hover.contents
    == """## `slapos.recipe.cmmi`

---
The recipe provides the means to compile and install source distributions using configure and make and other similar tools.

---
```ini
recipe = slapos.recipe.cmmi
version = 2.4.41
url = https://archive.apache.org/dist/httpd/httpd-${:version}.tar.bz2
md5sum = dfc674f8f454e3bc2d4ccd73ad3b5f1e
```"""
  )

  hover = await lsp_hover(
    server,
    TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(
        uri="file:///slapos/instance_as_buildout_profile/instance.cfg"
      ),
      position=Position(line=13, character=24),
    ),
  )
  assert hover is not None
  assert hover.contents == ""

  hover = await lsp_hover(
    server,
    TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(
        uri="file:///slapos/instance_as_buildout_profile/instance.cfg"
      ),
      position=Position(line=13, character=42),
    ),
  )
  assert hover is not None
  assert hover.contents == ""

  hover = await lsp_hover(
    server,
    TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(
        uri="file:///slapos/instance_as_buildout_profile/instance.cfg"
      ),
      position=Position(line=13, character=63),
    ),
  )
  assert hover is not None
  assert hover.contents == "```\n\n```"


async def test_complete_slapos_instance_template(server: LanguageServer):
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )

  # complete ${ in instance's template with instance
  params = CompletionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///slapos/instance_as_buildout_profile/template.in"
    ),
    position=Position(line=0, character=75),
    context=context,
  )

  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
    "_buildout_section_name_",
    "_profile_base_location_",
    "etc",
    "home",
    "recipe",
  ]


async def test_goto_definition_slapos_instance_software(server: LanguageServer):
  definitions = await lsp_definition(
    server,
    TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(
        uri="file:///slapos/instance_as_buildout_profile/instance.cfg"
      ),
      position=Position(line=13, character=23),
    ),
  )
  assert definitions == [
    Location(
      uri="file:///slapos/instance_as_buildout_profile/software.cfg",
      range=Range(
        start=Position(line=7, character=0), end=Position(line=8, character=0)
      ),
    )
  ]


async def test_goto_definition_slapos_instance_instance(server: LanguageServer):
  definitions = await lsp_definition(
    server,
    TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(
        uri="file:///slapos/instance_as_buildout_profile/instance.cfg"
      ),
      position=Position(line=12, character=26),
    ),
  )
  assert definitions == [
    Location(
      uri="file:///slapos/instance_as_buildout_profile/instance.cfg",
      range=Range(
        start=Position(line=7, character=5), end=Position(line=7, character=20)
      ),
    )
  ]


async def test_goto_definition_slapos_instance_software_empty_section(
  server: LanguageServer,
):
  definitions = await lsp_definition(
    server,
    TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(
        uri="file:///slapos/instance_as_buildout_profile/instance.cfg"
      ),
      position=Position(line=7, character=12),
    ),
  )
  assert definitions == [
    Location(
      uri="file:///slapos/instance_as_buildout_profile/instance.cfg",
      range=Range(
        start=Position(line=6, character=6), end=Position(line=6, character=29)
      ),
    )
  ]


async def test_goto_definition_slapos_instance_template(server: LanguageServer):
  definitions = await lsp_definition(
    server,
    TextDocumentPositionParams(
      text_document=TextDocumentIdentifier(
        uri="file:///slapos/instance_as_buildout_profile/template.in"
      ),
      position=Position(line=0, character=75),
    ),
  )
  assert definitions == [
    Location(
      uri="file:///slapos/instance_as_buildout_profile/instance.cfg",
      range=Range(
        start=Position(line=6, character=6), end=Position(line=6, character=29)
      ),
    )
  ]


async def test_open_instance_type(server: LanguageServer):
  assert isinstance(
    await open(
      ls=server, uri="file:///slapos/instance_as_buildout_profile/instance.cfg"
    ),
    BuildoutProfile,
  )
  assert isinstance(
    await open(ls=server, uri="file:///slapos/instance_as_jinja/instance.cfg.in"),
    BuildoutProfile,
  )


async def test_diagnostic_instance(server) -> None:
  await parseAndSendDiagnostics(
    server, "file:///slapos/instance_as_buildout_profile/instance.cfg"
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///slapos/instance_as_buildout_profile/instance.cfg",
      diagnostics=[],
    ),
  )
  server.text_document_publish_diagnostics.reset_mock()
  await parseAndSendDiagnostics(
    server, "file:///slapos/instance_as_jinja/instance.cfg.in"
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///slapos/instance_as_jinja/instance.cfg.in",
      diagnostics=[],
    ),
  )
