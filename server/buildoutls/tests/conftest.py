import os
import urllib.parse
from typing import Any
from unittest import mock

import pytest
import aioresponses
from pygls.workspace import Document, Workspace
import pygls.progress

from ..buildout import (
    _extends_dependency_graph,
    _parse_cache,
    _resolved_buildout_cache,
    _resolved_extends_cache,
    parse,
)
from ..aiohttp_session import close_session


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
          '..',
          '..',
          '..',
          'profiles',
      ))

  class FakeServer():
    """We don't need real server to unit test features."""
    def __init__(self):
      self.workspace = Workspace('', None)
      self.workspace._root_path = (root_path if root_path.endswith('/') else
                                   root_path + '/')
      self.workspace._root_uri = 'file:///'

    # BBB AsyncMock needs python3.8 , for now we don't assert the actual call args
    async def show_document_async(self, *args, **kw):
      pass

    publish_diagnostics = mock.Mock()
    show_message = mock.Mock()
    show_message_log = mock.Mock()
    apply_edit = mock.Mock()
    progress = mock.create_autospec(pygls.progress.Progress)

  server = FakeServer()

  def get_document(uri) -> Document:
    parsed_uri = urllib.parse.urlparse(uri)
    assert parsed_uri.scheme == "file"
    assert parsed_uri.path[0] == '/'
    document = Document(uri=uri)
    if not os.path.exists(document.path):
      document.path = os.path.join(root_path, parsed_uri.path[1:])
    return document

  server.workspace.get_document = mock.Mock(side_effect=get_document)

  def os_path_exists(path: str) -> bool:
    if path.startswith('/'):
      path = path.replace('/', root_path + '/', 1)
    return os.path.exists(path)

  os_path_exists_patcher = mock.patch('buildoutls.diagnostic.os_path_exists',
                                      side_effect=os_path_exists)

  def clearCaches() -> None:
    _resolved_buildout_cache.clear()
    _resolved_extends_cache.clear()
    _parse_cache.clear()
    _extends_dependency_graph.clear()

  clearCaches()
  with os_path_exists_patcher:
    yield server
  server.publish_diagnostics.reset_mock()
  server.show_message.reset_mock()
  server.show_message_log.reset_mock()
  server.workspace.get_document.reset_mock()

  clearCaches()


@pytest.fixture
async def buildout(server) -> Any:
  return await parse(
      ls=server,
      uri='file:///buildout.cfg',
  )


@pytest.fixture
async def template(server) -> Any:
  parsed = await parse(
      ls=server,
      uri='file:///buildout.cfg',
  )
  return await parsed.getTemplate(server, 'template.in')
