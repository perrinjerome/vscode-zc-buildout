import os
import urllib.parse
from unittest import mock
import pytest
import responses

from typing import Any
from pygls.workspace import Document, Workspace

from ..buildout import _resolved_buildout_cache, _parse_cache, _extends_dependency_graph, parse

from .. import server as _server_module


@pytest.fixture
def mocked_responses():
  with responses.RequestsMock() as rsps:
    yield rsps


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

    publish_diagnostics = mock.Mock()
    show_message = mock.Mock()
    show_message_log = mock.Mock()

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

  def clearCaches() -> None:
    _resolved_buildout_cache.clear()
    _parse_cache.clear()
    _extends_dependency_graph.clear()

  clearCaches()
  old_debounce_delay = _server_module.DEBOUNCE_DELAY
  _server_module.DEBOUNCE_DELAY = 0
  yield server
  _server_module.DEBOUNCE_DELAY = old_debounce_delay
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
