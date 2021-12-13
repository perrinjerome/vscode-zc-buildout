import json
import pathlib
import textwrap
from unittest import mock

import pytest
import responses
from pygls.lsp.types import (
    CodeAction,
    CodeActionContext,
    CodeActionKind,
    CodeActionParams,
    Command,
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
    TextDocumentIdentifier,
    TextEdit,
    WorkspaceEdit,
)
from pygls.protocol import default_serializer

from ..commands import COMMAND_OPEN_PYPI_PAGE
from ..server import command_open_pypi_page, lsp_code_action, parseAndSendDiagnostics
from ..types import OpenPypiPageCommandParams


@pytest.fixture
def sampleproject_json_response(
    mocked_responses: responses.RequestsMock) -> None:
  with open(pathlib.Path(__file__).parent / 'testdata' /
            'sampleproject.json') as f:
    response_json = json.load(f)
  mocked_responses.add(
      responses.GET,
      'https://pypi.org/pypi/sampleproject/json',
      json=response_json,
  )


@pytest.fixture
def sampleproject_json_1_2_0_response(
    mocked_responses: responses.RequestsMock) -> None:
  with open(
      pathlib.Path(__file__).parent / 'testdata' /
      'sampleproject-1.2.0.json') as f:
    response_json = json.load(f)
  mocked_responses.add(
      responses.GET,
      'https://pypi.org/pypi/sampleproject/1.2.0/json',
      json=response_json,
  )


@pytest.fixture
def sampleproject_json_1_3_0_response(
    mocked_responses: responses.RequestsMock) -> None:
  with open(
      pathlib.Path(__file__).parent / 'testdata' /
      'sampleproject-1.3.0.json') as f:
    response_json = json.load(f)
  mocked_responses.add(
      responses.GET,
      'https://pypi.org/pypi/sampleproject/1.3.0/json',
      json=response_json,
  )


@pytest.fixture
def sampleproject_json_2_0_0_response(
    mocked_responses: responses.RequestsMock) -> None:
  with open(
      pathlib.Path(__file__).parent / 'testdata' /
      'sampleproject-2.0.0.json') as f:
    response_json = json.load(f)
  mocked_responses.add(
      responses.GET,
      'https://pypi.org/pypi/sampleproject/2.0.0/json',
      json=response_json,
  )


def _dump_and_load(param: CodeActionParams) -> CodeActionParams:
  """Simulate a code action params going through pygls protocol.
  """
  dumped = param.json(
      by_alias=True,
      exclude_unset=True,
      encoder=default_serializer,
  )
  return CodeActionParams(**json.loads(dumped))


@pytest.mark.asyncio
async def test_diagnostic_and_versions_code_action_newer_version_available(
    server,
    sampleproject_json_response,
    sampleproject_json_1_3_0_response,
) -> None:
  await parseAndSendDiagnostics(
      server,
      'file:///code_actions/newer_version_available.cfg',
  )
  server.publish_diagnostics.assert_called_once_with(
      'file:///code_actions/newer_version_available.cfg',
      [mock.ANY],
  )
  diagnostic: Diagnostic
  diagnostic, = server.publish_diagnostics.call_args[0][1]
  assert diagnostic.severity == DiagnosticSeverity.Hint
  assert diagnostic.range == Range(start=Position(line=1, character=15),
                                   end=Position(line=1, character=21))
  assert diagnostic.message == \
    "Newer version available (2.0.0)"

  code_action_params = CodeActionParams(
      textDocument=TextDocumentIdentifier(
          uri='file:///code_actions/newer_version_available.cfg'),
      range=Range(start=Position(line=1, character=15),
                  end=Position(line=1, character=21)),
      context=CodeActionContext(diagnostics=(diagnostic, )),
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
              'file:///code_actions/newer_version_available.cfg': [
                  TextEdit(range=Range(start=Position(line=1, character=15),
                                       end=Position(line=1, character=21)),
                           new_text=' 2.0.0'),
              ]
          }))

  assert code_actions[1] == CodeAction(
      title='View on pypi https://pypi.org/project/sampleproject/1.3.0/',
      command=Command(
          title='View on pypi',
          command=COMMAND_OPEN_PYPI_PAGE,
          arguments=[
              OpenPypiPageCommandParams(
                  url='https://pypi.org/project/sampleproject/1.3.0/')
          ]))

  assert len(code_actions) == 2


@pytest.mark.asyncio
async def test_diagnostic_and_versions_code_action_known_vulnerabilities(
    server,
    sampleproject_json_response,
    sampleproject_json_1_2_0_response,
) -> None:
  await parseAndSendDiagnostics(
      server, 'file:///code_actions/known_vulnerabilities.cfg')
  server.publish_diagnostics.assert_called_once_with(
      'file:///code_actions/known_vulnerabilities.cfg',
      [mock.ANY],
  )
  diagnostic: Diagnostic
  diagnostic, = server.publish_diagnostics.call_args[0][1]
  assert diagnostic.severity == DiagnosticSeverity.Warning
  assert diagnostic.range == Range(start=Position(line=1, character=15),
                                   end=Position(line=1, character=21))
  assert diagnostic.message == \
    textwrap.dedent("""\
      sampleproject 1.2.0 has some known vunerabilities:
      EXAMPLE-VUL
      An example vulnerabulity
      https://example.org/vulnerability/EXAMPLE-VUL""")

  code_action_params = CodeActionParams(
      textDocument=TextDocumentIdentifier(
          uri='file:///code_actions/newer_version_available.cfg'),
      range=Range(start=Position(line=1, character=15),
                  end=Position(line=1, character=21)),
      context=CodeActionContext(diagnostics=(diagnostic, )),
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
              'file:///code_actions/newer_version_available.cfg': [
                  TextEdit(range=Range(start=Position(line=1, character=15),
                                       end=Position(line=1, character=21)),
                           new_text=' 2.0.0'),
              ]
          }))

  assert code_actions[1] == CodeAction(
      title='View on pypi https://pypi.org/project/sampleproject/1.3.0/',
      command=Command(
          title='View on pypi',
          command=COMMAND_OPEN_PYPI_PAGE,
          arguments=[
              OpenPypiPageCommandParams(
                  url='https://pypi.org/project/sampleproject/1.3.0/')
          ]))

  assert len(code_actions) == 2


@pytest.mark.asyncio
async def test_diagnostic_and_versions_code_action_latest_version(
    server,
    sampleproject_json_response,
    sampleproject_json_2_0_0_response,
) -> None:
  await parseAndSendDiagnostics(
      server,
      'file:///code_actions/latest_version.cfg',
  )
  server.publish_diagnostics.assert_called_once_with(
      'file:///code_actions/latest_version.cfg',
      [],
  )

  code_action_params = CodeActionParams(
      textDocument=TextDocumentIdentifier(
          uri='file:///code_actions/latest_version.cfg'),
      range=Range(start=Position(line=1, character=15),
                  end=Position(line=1, character=21)),
      context=CodeActionContext(diagnostics=()))

  code_actions = await lsp_code_action(
      server,
      _dump_and_load(code_action_params),
  )
  assert isinstance(code_actions, list)
  assert code_actions == [
      CodeAction(
          title='View on pypi https://pypi.org/project/sampleproject/2.0.0/',
          command=Command(
              title='View on pypi',
              command=COMMAND_OPEN_PYPI_PAGE,
              arguments=[
                  OpenPypiPageCommandParams(
                      url='https://pypi.org/project/sampleproject/2.0.0/')
              ]))
  ]
  assert isinstance(code_actions[0].command, Command)
  assert code_actions[0].command.arguments
  await command_open_pypi_page(server, code_actions[0].command.arguments)
