from __future__ import annotations

import collections
import concurrent.futures
import json
import pathlib
import textwrap
from typing import List, cast
from unittest import mock

import aioresponses
import pytest
from lsprotocol.types import (
  ApplyWorkspaceEditParams,
  CodeAction,
  CodeActionContext,
  CodeActionKind,
  CodeActionParams,
  Command,
  Diagnostic,
  DiagnosticSeverity,
  Position,
  PublishDiagnosticsParams,
  Range,
  ShowDocumentParams,
  TextDocumentIdentifier,
  TextEdit,
  WorkspaceEdit,
)

from ..commands import COMMAND_OPEN_PYPI_PAGE, COMMAND_UPDATE_MD5SUM
from ..server import (
  command_open_pypi_page,
  command_update_md5sum,
  lsp_code_action,
  parseAndSendDiagnostics,
  server,
)
from ..types import OpenPypiPageCommandParams, UpdateMD5SumCommandParams


@pytest.fixture
def sampleproject_json_response(mocked_responses: aioresponses.aioresponses) -> None:
  with open(pathlib.Path(__file__).parent / "testdata" / "sampleproject.json") as f:
    response_json = json.load(f)
  mocked_responses.get(
    "https://pypi.org/pypi/sampleproject/json",
    payload=response_json,
  )


@pytest.fixture
def notfound_json_response(mocked_responses: aioresponses.aioresponses) -> None:
  with open(pathlib.Path(__file__).parent / "testdata" / "notfound.json") as f:
    response_json = json.load(f)
  mocked_responses.get(
    "https://pypi.org/pypi/notfound/json",
    payload=response_json,
  )


@pytest.fixture
def notfound_0_0_1_json_response(mocked_responses: aioresponses.aioresponses) -> None:
  with open(pathlib.Path(__file__).parent / "testdata" / "notfound-0.0.1.json") as f:
    response_json = json.load(f)
  mocked_responses.get(
    "https://pypi.org/pypi/notfound/0.0.1/json",
    payload=response_json,
  )


@pytest.fixture
def sampleproject_1_2_0_json_response(
  mocked_responses: aioresponses.aioresponses,
) -> None:
  with open(
    pathlib.Path(__file__).parent / "testdata" / "sampleproject-1.2.0.json"
  ) as f:
    response_json = json.load(f)
  mocked_responses.get(
    "https://pypi.org/pypi/sampleproject/1.2.0/json",
    payload=response_json,
  )


@pytest.fixture
def sampleproject_1_3_0_json_response(
  mocked_responses: aioresponses.aioresponses,
) -> None:
  with open(
    pathlib.Path(__file__).parent / "testdata" / "sampleproject-1.3.0.json"
  ) as f:
    response_json = json.load(f)
  mocked_responses.get(
    "https://pypi.org/pypi/sampleproject/1.3.0/json",
    payload=response_json,
  )


@pytest.fixture
def sampleproject_2_0_0_json_response(
  mocked_responses: aioresponses.aioresponses,
) -> None:
  with open(
    pathlib.Path(__file__).parent / "testdata" / "sampleproject-2.0.0.json"
  ) as f:
    response_json = json.load(f)
  mocked_responses.get(
    "https://pypi.org/pypi/sampleproject/2.0.0/json",
    payload=response_json,
  )


@pytest.fixture
def sampleproject_9_9_9_json_response(
  mocked_responses: aioresponses.aioresponses,
) -> None:
  with open(
    pathlib.Path(__file__).parent / "testdata" / "sampleproject-9.9.9.json"
  ) as f:
    response_json = json.load(f)
  mocked_responses.get(
    "https://pypi.org/pypi/sampleproject/9.9.9/json",
    payload=response_json,
  )


def _dump_and_load(param: CodeActionParams) -> CodeActionParams:
  """Simulate a code action params going through pygls protocol."""
  dumped = json.dumps(param, default=server.protocol._serialize_message)
  return server.protocol._converter.structure(json.loads(dumped), CodeActionParams)


async def test_diagnostic_and_versions_code_action_newer_version_available(
  server,
  sampleproject_json_response,
  sampleproject_1_3_0_json_response,
) -> None:
  await parseAndSendDiagnostics(
    server,
    "file:///code_actions/newer_version_available.cfg",
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///code_actions/newer_version_available.cfg",
      diagnostics=[mock.ANY],
    ),
  )
  diagnostic: Diagnostic
  (diagnostic,) = server.text_document_publish_diagnostics.call_args[0][0].diagnostics
  assert diagnostic.severity == DiagnosticSeverity.Hint
  assert diagnostic.range == Range(
    start=Position(line=1, character=15), end=Position(line=1, character=21)
  )
  assert diagnostic.message == "Newer version available (2.0.0)"

  code_action_params = CodeActionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///code_actions/newer_version_available.cfg"
    ),
    range=Range(
      start=Position(line=1, character=15), end=Position(line=1, character=21)
    ),
    context=CodeActionContext(
      diagnostics=[
        diagnostic,
      ]
    ),
  )
  code_actions = await lsp_code_action(
    server,
    _dump_and_load(code_action_params),
  )
  assert isinstance(code_actions, list)
  assert code_actions[0] == CodeAction(
    title="Use version 2.0.0",
    kind=CodeActionKind.QuickFix,
    is_preferred=True,
    edit=WorkspaceEdit(
      changes={
        "file:///code_actions/newer_version_available.cfg": [
          TextEdit(
            range=Range(
              start=Position(line=1, character=15), end=Position(line=1, character=21)
            ),
            new_text=" 2.0.0",
          ),
        ]
      }
    ),
  )

  assert code_actions[1] == CodeAction(
    title="View on pypi https://pypi.org/project/sampleproject/1.3.0/",
    command=Command(
      title="View on pypi",
      command=COMMAND_OPEN_PYPI_PAGE,
      arguments=[
        OpenPypiPageCommandParams(url="https://pypi.org/project/sampleproject/1.3.0/")
      ],
    ),
  )

  assert len(code_actions) == 2


async def test_diagnostic_and_versions_code_action_known_vulnerabilities(
  server,
  sampleproject_json_response,
  sampleproject_1_2_0_json_response,
) -> None:
  await parseAndSendDiagnostics(
    server, "file:///code_actions/known_vulnerabilities.cfg"
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///code_actions/known_vulnerabilities.cfg",
      diagnostics=[mock.ANY],
    ),
  )
  diagnostic: Diagnostic
  (diagnostic,) = server.text_document_publish_diagnostics.call_args[0][0].diagnostics
  assert diagnostic.severity == DiagnosticSeverity.Warning
  assert diagnostic.range == Range(
    start=Position(line=1, character=15), end=Position(line=1, character=21)
  )
  assert diagnostic.message == textwrap.dedent("""\
      sampleproject 1.2.0 has some known vulnerabilities:
      EXAMPLE-VUL
      An example vulnerability
      https://example.org/vulnerability/EXAMPLE-VUL""")

  code_action_params = CodeActionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///code_actions/newer_version_available.cfg"
    ),
    range=Range(
      start=Position(line=1, character=15), end=Position(line=1, character=21)
    ),
    context=CodeActionContext(
      diagnostics=[
        diagnostic,
      ]
    ),
  )
  code_actions = await lsp_code_action(
    server,
    _dump_and_load(code_action_params),
  )
  assert isinstance(code_actions, list)
  assert code_actions[0] == CodeAction(
    title="Use version 2.0.0",
    kind=CodeActionKind.QuickFix,
    is_preferred=True,
    edit=WorkspaceEdit(
      changes={
        "file:///code_actions/newer_version_available.cfg": [
          TextEdit(
            range=Range(
              start=Position(line=1, character=15), end=Position(line=1, character=21)
            ),
            new_text=" 2.0.0",
          ),
        ]
      }
    ),
  )

  assert code_actions[1] == CodeAction(
    title="View on pypi https://pypi.org/project/sampleproject/1.3.0/",
    command=Command(
      title="View on pypi",
      command=COMMAND_OPEN_PYPI_PAGE,
      arguments=[
        OpenPypiPageCommandParams(url="https://pypi.org/project/sampleproject/1.3.0/")
      ],
    ),
  )

  assert len(code_actions) == 2


async def test_diagnostic_and_versions_code_action_version_not_exists(
  server, sampleproject_9_9_9_json_response, sampleproject_json_response
) -> None:
  await parseAndSendDiagnostics(
    server, "file:///code_actions/package_version_not_exists.cfg"
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///code_actions/package_version_not_exists.cfg",
      diagnostics=[mock.ANY],
    ),
  )
  diagnostic: Diagnostic
  (diagnostic,) = server.text_document_publish_diagnostics.call_args[0][0].diagnostics
  assert diagnostic.severity == DiagnosticSeverity.Warning
  assert repr(diagnostic.range) == "1:15-1:20"

  assert diagnostic.message == "Version 9.9.9 does not exist for sampleproject"

  code_action_params = CodeActionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///code_actions/package_version_not_exists.cfg"
    ),
    range=Range(
      start=Position(line=1, character=15), end=Position(line=1, character=20)
    ),
    context=CodeActionContext(
      diagnostics=[
        diagnostic,
      ]
    ),
  )
  code_actions = await lsp_code_action(
    server,
    _dump_and_load(code_action_params),
  )
  assert isinstance(code_actions, list)
  assert code_actions[0] == CodeAction(
    title="Use version 2.0.0",
    kind=CodeActionKind.QuickFix,
    is_preferred=True,
    edit=WorkspaceEdit(
      changes={
        "file:///code_actions/package_version_not_exists.cfg": [
          TextEdit(
            range=Range(
              start=Position(line=1, character=15), end=Position(line=1, character=20)
            ),
            new_text=" 2.0.0",
          ),
        ]
      }
    ),
  )

  assert code_actions[1] == CodeAction(
    title="View on pypi https://pypi.org/project/sampleproject/9.9.9/",
    command=Command(
      title="View on pypi",
      command=COMMAND_OPEN_PYPI_PAGE,
      arguments=[
        OpenPypiPageCommandParams(url="https://pypi.org/project/sampleproject/9.9.9/")
      ],
    ),
  )

  assert len(code_actions) == 2


async def test_diagnostic_and_versions_code_action_package_not_exists(
  server, notfound_0_0_1_json_response, notfound_json_response
) -> None:
  await parseAndSendDiagnostics(server, "file:///code_actions/package_not_exists.cfg")
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///code_actions/package_not_exists.cfg",
      diagnostics=[mock.ANY],
    ),
  )
  diagnostic: Diagnostic
  (diagnostic,) = server.text_document_publish_diagnostics.call_args[0][0].diagnostics
  assert diagnostic.severity == DiagnosticSeverity.Warning
  assert repr(diagnostic.range) == "1:10-1:16"

  code_action_params = CodeActionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///code_actions/package_not_exists.cfg"
    ),
    range=Range(
      start=Position(line=1, character=11), end=Position(line=1, character=16)
    ),
    context=CodeActionContext(
      diagnostics=[
        diagnostic,
      ]
    ),
  )

  code_actions = await lsp_code_action(
    server,
    _dump_and_load(code_action_params),
  )
  assert isinstance(code_actions, list)
  assert code_actions == [
    CodeAction(
      title="View on pypi https://pypi.org/project/notfound/0.0.1/",
      command=Command(
        title="View on pypi",
        command=COMMAND_OPEN_PYPI_PAGE,
        arguments=[
          OpenPypiPageCommandParams(url="https://pypi.org/project/notfound/0.0.1/")
        ],
      ),
    )
  ]
  assert isinstance(code_actions[0].command, Command)
  assert code_actions[0].command.arguments
  await command_open_pypi_page(
    server, *cast(List[OpenPypiPageCommandParams], code_actions[0].command.arguments)
  )
  server.window_show_document_async.assert_called_with(
    ShowDocumentParams(
      uri="https://pypi.org/project/notfound/0.0.1/",
      external=True,
    )
  )


@pytest.mark.parametrize(
  "_range",
  (
    # on value
    Range(start=Position(line=1, character=15), end=Position(line=1, character=21)),
    # on option
    Range(start=Position(line=1, character=4), end=Position(line=1, character=8)),
  ),
)
async def test_diagnostic_and_versions_code_action_latest_version(
  server,
  sampleproject_json_response,
  sampleproject_2_0_0_json_response,
  _range,
) -> None:
  await parseAndSendDiagnostics(
    server,
    "file:///code_actions/latest_version.cfg",
  )
  server.text_document_publish_diagnostics.assert_called_once_with(
    PublishDiagnosticsParams(
      uri="file:///code_actions/latest_version.cfg",
      diagnostics=[],
    ),
  )

  code_action_params = CodeActionParams(
    text_document=TextDocumentIdentifier(uri="file:///code_actions/latest_version.cfg"),
    range=_range,
    context=CodeActionContext(diagnostics=[]),
  )

  code_actions = await lsp_code_action(
    server,
    _dump_and_load(code_action_params),
  )
  assert isinstance(code_actions, list)
  assert code_actions == [
    CodeAction(
      title="View on pypi https://pypi.org/project/sampleproject/2.0.0/",
      command=Command(
        title="View on pypi",
        command=COMMAND_OPEN_PYPI_PAGE,
        arguments=[
          OpenPypiPageCommandParams(url="https://pypi.org/project/sampleproject/2.0.0/")
        ],
      ),
    )
  ]
  assert isinstance(code_actions[0].command, Command)
  assert code_actions[0].command.arguments
  await command_open_pypi_page(
    server, *cast(List[OpenPypiPageCommandParams], code_actions[0].command.arguments)
  )


@pytest.fixture
def example_com_response(mocked_responses: aioresponses.aioresponses) -> None:
  mocked_responses.get(
    "https://example.com",
    body=b"hello",
  )


@pytest.mark.parametrize(
  "range_",
  [
    # on `url` value
    Range(start=Position(line=1, character=11), end=Position(line=1, character=12)),
    Range(start=Position(line=1, character=12), end=Position(line=1, character=26)),
    # on `md5sum` value
    Range(start=Position(line=2, character=10), end=Position(line=2, character=14)),
    Range(start=Position(line=2, character=14), end=Position(line=2, character=14)),
  ],
)
async def test_update_md5sum_code_action(
  range_,
  server,
  example_com_response,
) -> None:
  code_action_params = CodeActionParams(
    text_document=TextDocumentIdentifier(uri="file:///code_actions/update_md5sum.cfg"),
    range=range_,
    context=CodeActionContext(diagnostics=[]),
  )

  code_actions = await lsp_code_action(
    server,
    _dump_and_load(code_action_params),
  )
  assert isinstance(code_actions, list)
  assert code_actions == [
    CodeAction(
      title="Update md5sum",
      kind=CodeActionKind.QuickFix,
      command=Command(
        title="Update md5sum",
        command=COMMAND_UPDATE_MD5SUM,
        arguments=[
          UpdateMD5SumCommandParams(
            document_uri="file:///code_actions/update_md5sum.cfg",
            section_name="section",
          ),
        ],
      ),
    )
  ]
  assert isinstance(code_actions[0].command, Command)
  assert code_actions[0].command.arguments
  await command_update_md5sum(
    server, *cast(List[UpdateMD5SumCommandParams], code_actions[0].command.arguments)
  )
  server.workspace_apply_edit.assert_called_once_with(
    ApplyWorkspaceEditParams(
      edit=WorkspaceEdit(
        changes={
          "file:///code_actions/update_md5sum.cfg": [
            TextEdit(
              range=Range(
                start=Position(
                  line=2,
                  character=8,
                ),
                end=Position(
                  line=2,
                  character=14,
                ),
              ),
              new_text=" 5d41402abc4b2a76b9719d911017c592",
            ),
          ],
        },
      ),
    ),
  )

  server.work_done_progress.create_async.assert_awaited_once()
  server.work_done_progress.begin.assert_called_once()
  server.work_done_progress.report.assert_called()
  server.work_done_progress.end.assert_called_once()


async def test_update_md5sum_code_action_without_md5sum_option(
  server,
  example_com_response,
) -> None:
  code_action_params = CodeActionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///code_actions/update_md5sum_without_md5sum_option.cfg"
    ),
    range=Range(
      start=Position(line=1, character=11), end=Position(line=1, character=12)
    ),
    context=CodeActionContext(diagnostics=[]),
  )

  code_actions = await lsp_code_action(
    server,
    _dump_and_load(code_action_params),
  )
  assert isinstance(code_actions, list)
  assert code_actions == [
    CodeAction(
      title="Update md5sum",
      kind=CodeActionKind.QuickFix,
      command=Command(
        title="Update md5sum",
        command=COMMAND_UPDATE_MD5SUM,
        arguments=[
          UpdateMD5SumCommandParams(
            document_uri="file:///code_actions/update_md5sum_without_md5sum_option.cfg",
            section_name="section",
          ),
        ],
      ),
    )
  ]
  assert isinstance(code_actions[0].command, Command)
  assert code_actions[0].command.arguments
  await command_update_md5sum(
    server, *cast(List[UpdateMD5SumCommandParams], code_actions[0].command.arguments)
  )
  server.workspace_apply_edit.assert_called_once_with(
    ApplyWorkspaceEditParams(
      edit=WorkspaceEdit(
        changes={
          "file:///code_actions/update_md5sum_without_md5sum_option.cfg": [
            TextEdit(
              range=Range(
                start=Position(
                  line=2,
                  character=0,
                ),
                end=Position(
                  line=2,
                  character=0,
                ),
              ),
              new_text="md5sum = 5d41402abc4b2a76b9719d911017c592\n",
            ),
          ],
        },
      ),
    ),
  )


async def test_update_md5sum_code_action_cancelled(
  server,
  example_com_response,
) -> None:
  code_action_params = CodeActionParams(
    text_document=TextDocumentIdentifier(uri="file:///code_actions/update_md5sum.cfg"),
    range=Range(
      start=Position(line=1, character=11), end=Position(line=1, character=12)
    ),
    context=CodeActionContext(diagnostics=[]),
  )

  code_actions = await lsp_code_action(
    server,
    _dump_and_load(code_action_params),
  )
  assert isinstance(code_actions, list)
  assert code_actions == [
    CodeAction(
      title="Update md5sum",
      kind=CodeActionKind.QuickFix,
      command=Command(
        title="Update md5sum",
        command=COMMAND_UPDATE_MD5SUM,
        arguments=[
          UpdateMD5SumCommandParams(
            document_uri="file:///code_actions/update_md5sum.cfg",
            section_name="section",
          ),
        ],
      ),
    )
  ]
  assert isinstance(code_actions[0].command, Command)
  assert code_actions[0].command.arguments

  def cancelled_future() -> concurrent.futures.Future[None]:
    f: concurrent.futures.Future[None] = concurrent.futures.Future()
    f.cancel()
    return f

  server.work_done_progress.tokens = collections.defaultdict(cancelled_future)

  await command_update_md5sum(
    server, *cast(List[UpdateMD5SumCommandParams], code_actions[0].command.arguments)
  )
  server.workspace_apply_edit.assert_not_called()


@pytest.mark.parametrize(
  "range_",
  [
    # option key ( url = )
    Range(
      start=Position(
        line=2,
        character=1,
      ),
      end=Position(
        line=2,
        character=2,
      ),
    ),
    # option value
    Range(
      start=Position(
        line=2,
        character=25,
      ),
      end=Position(
        line=2,
        character=26,
      ),
    ),
    # section reference, but in option value
    Range(
      start=Position(
        line=2,
        character=12,
      ),
      end=Position(
        line=2,
        character=13,
      ),
    ),
    # option reference, but in option value
    Range(
      start=Position(
        line=2,
        character=33,
      ),
      end=Position(
        line=2,
        character=24,
      ),
    ),
  ],
)
async def test_update_md5sum_code_action_with_substitutions(
  server,
  range_,
  example_com_response,
) -> None:
  code_action_params = CodeActionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///code_actions/update_md5sum_code_action_with_substitutions.cfg"
    ),
    range=range_,
    context=CodeActionContext(
      diagnostics=[],
    ),
  )

  code_actions = await lsp_code_action(
    server,
    _dump_and_load(code_action_params),
  )
  assert isinstance(code_actions, list)
  assert code_actions == [
    CodeAction(
      title="Update md5sum",
      kind=CodeActionKind.QuickFix,
      command=Command(
        title="Update md5sum",
        command=COMMAND_UPDATE_MD5SUM,
        arguments=[
          UpdateMD5SumCommandParams(
            document_uri="file:///code_actions/update_md5sum_code_action_with_substitutions.cfg",
            section_name="section",
          ),
        ],
      ),
    )
  ]
  assert isinstance(code_actions[0].command, Command)
  assert code_actions[0].command.arguments
  await command_update_md5sum(
    server, *cast(List[UpdateMD5SumCommandParams], code_actions[0].command.arguments)
  )
  server.workspace_apply_edit.assert_called_once_with(
    ApplyWorkspaceEditParams(
      edit=WorkspaceEdit(
        changes={
          "file:///code_actions/update_md5sum_code_action_with_substitutions.cfg": [
            TextEdit(
              range=Range(
                start=Position(
                  line=3,
                  character=8,
                ),
                end=Position(
                  line=4,
                  character=0,
                ),
              ),
              new_text=" 5d41402abc4b2a76b9719d911017c592",
            ),
          ],
        },
      ),
    ),
  )
