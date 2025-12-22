import collections
import concurrent.futures
import os
import urllib.parse
from typing import Any
from unittest import mock

import aioresponses
import pygls.progress
import pytest
from lsprotocol.types import TextDocumentSyncKind
from pygls.workspace import TextDocument, Workspace

from ..buildout import (
  _extends_dependency_graph,
  _parse_cache,
  _resolved_buildout_cache,
  _resolved_extends_cache,
  parse,
)
from ..util.aiohttp_session import close_session


@pytest.fixture(autouse=True)
async def close_aiohttp_session():
  yield
  await close_session()


@pytest.fixture
def mocked_responses():
  with aioresponses.aioresponses() as m:
    yield m


@pytest.fixture
def server() -> Any:
  root_path = os.path.abspath(
    os.path.join(
      os.path.dirname(__file__),
      "..",
      "..",
      "..",
      "..",
      "profiles",
    )
  )

  window_show_document_async = mock.AsyncMock()
  text_document_publish_diagnostics = mock.Mock()
  window_show_message = mock.Mock()
  window_log_message = mock.Mock()
  workspace_apply_edit = mock.Mock()
  work_done_progress = mock.create_autospec(pygls.progress.Progress)
  work_done_progress.tokens = collections.defaultdict(concurrent.futures.Future)

  class FakeServer:
    """We don't need real server to unit test features."""

    def __init__(self):
      self.workspace = Workspace("", TextDocumentSyncKind.Full)
      self.workspace._root_path = (
        root_path if root_path.endswith("/") else root_path + "/"
      )
      self.workspace._root_uri = "file:///"
      self.window_show_document_async = window_show_document_async
      self.text_document_publish_diagnostics = text_document_publish_diagnostics
      self.window_show_message = window_show_message
      self.window_log_message = window_log_message
      self.workspace_apply_edit = workspace_apply_edit
      self.work_done_progress = work_done_progress

  server = FakeServer()

  def get_text_document(uri) -> TextDocument:
    parsed_uri = urllib.parse.urlparse(uri)
    assert parsed_uri.scheme == "file"
    assert parsed_uri.path[0] == "/"
    document = TextDocument(uri=uri)
    if not os.path.exists(document.path):
      document.path = os.path.join(root_path, parsed_uri.path[1:])
    return document

  server.workspace.get_text_document = mock.Mock(side_effect=get_text_document)

  def os_path_exists(path: str) -> bool:
    if path.startswith("/"):
      path = path.replace("/", root_path + "/", 1)
    return os.path.exists(path)

  os_path_exists_patcher = mock.patch(
    "buildoutls.diagnostic.os_path_exists", side_effect=os_path_exists
  )

  def clearCaches() -> None:
    _resolved_buildout_cache.clear()
    _resolved_extends_cache.clear()
    _parse_cache.clear()
    _extends_dependency_graph.clear()

  clearCaches()
  with os_path_exists_patcher:
    yield server
  server.text_document_publish_diagnostics.reset_mock()
  server.window_show_message.reset_mock()
  server.window_log_message.reset_mock()
  server.workspace.get_text_document.reset_mock()

  clearCaches()


@pytest.fixture
async def buildout(server) -> Any:
  return await parse(
    ls=server,
    uri="file:///buildout.cfg",
  )


@pytest.fixture
async def template(server) -> Any:
  parsed = await parse(
    ls=server,
    uri="file:///buildout.cfg",
  )
  return await parsed.getTemplate(server, "template.in")


@pytest.fixture(params=[True, False])
def bad_encoding_file(request: pytest.FixtureRequest):
  """Fixture that optionally creates a bad_encoding.cfg file.

  Parameterized to run tests both with and without the file.
  """
  import pathlib

  profiles_dir = pathlib.Path(__file__).resolve().parents[4] / "profiles"
  bad_file = None
  if request.param:
    bad_file = profiles_dir / "bad_encoding.cfg"
    bad_file.write_bytes(b"\xff\xfe[section]\noption = value\n")

  try:
    yield request.param
  finally:
    if bad_file:
      bad_file.unlink()
