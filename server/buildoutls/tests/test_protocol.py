import asyncio
import os
import pathlib
import threading

import unittest.mock
import pygls.protocol
import pygls.server
import pytest

from pygls.lsp.methods import (CANCEL_REQUEST, COMPLETION, INITIALIZE,
                               TEXT_DOCUMENT_DID_OPEN)
from pygls.lsp.types import ClientCapabilities, InitializeParams
from pygls.lsp.types.basic_structures import (Position, TextDocumentIdentifier,
                                              TextDocumentItem)
from pygls.lsp.types.language_features.completion import CompletionParams
from pygls.lsp.types.workspace import DidOpenTextDocumentParams

from buildoutls.server import server

CALL_TIMEOUT = 3

root_path = pathlib.Path(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            '..',
            '..',
            'profiles',
        )))


class ClientServer:
  def __init__(self):
    # Client to Server pipe
    csr, csw = os.pipe()
    # Server to client pipe
    scr, scw = os.pipe()

    self._read_fds = (
        csr,
        scr,
    )

    # Setup Server: use the initialized server with methods registered,
    # but give it a new loop because this loop will be closed at server
    # shutdown.
    self.server = server
    self.server.loop = asyncio.new_event_loop()
    self.server_thread = threading.Thread(
        target=self.server.start_io,
        args=(os.fdopen(csr, 'rb'), os.fdopen(scw, 'wb')),
        name="Server",
    )
    self.server_thread.daemon = True

    # Setup client
    self.client = pygls.server.LanguageServer(asyncio.new_event_loop())
    self.client_thread = threading.Thread(
        target=self.client.start_io,
        args=(os.fdopen(scr, 'rb'), os.fdopen(csw, 'wb')),
        name="Client",
    )
    self.client_thread.daemon = True

  def start(self):
    self.server_thread.start()
    self.server.thread_id = self.server_thread.ident

    self.client_thread.start()

    self.initialize()

  def stop(self):
    # XXX setting a shutdown message does not seem to stop properly,
    # for now we close the file input fds
    for fd in self._read_fds:
      os.close(fd)
    self.server_thread.join()
    self.client_thread.join()

  def initialize(self):
    response = self.client.lsp.send_request(
        INITIALIZE,
        InitializeParams(
            process_id=os.getpid(),
            root_uri=root_path.as_uri(),
            capabilities=ClientCapabilities())).result(timeout=CALL_TIMEOUT)

    assert 'capabilities' in response

  def __iter__(self):
    yield self.client
    yield self.server


@pytest.fixture
def client_server():
  """ A fixture to setup a client/server """
  client_server = ClientServer()
  client_server.start()
  client, server = client_server
  yield client, server
  client_server.stop()


def test_completion_cancellation(client_server):
  client, _ = client_server

  fname = root_path / 'buildout.cfg'
  uri = fname.as_uri()
  language_id = 'zc-buildout'
  version = 1
  with open(fname) as f:
    text = f.read()

  client.lsp.notify(
      method=TEXT_DOCUMENT_DID_OPEN,
      params=DidOpenTextDocumentParams(text_document=TextDocumentItem(
          uri=uri,
          language_id=language_id,
          version=version,
          text=text,
      )))
  with unittest.mock.patch('pygls.protocol.uuid.uuid4',
                           return_value='first-completion'):
    req1 = client.lsp.send_request(
        method=COMPLETION,
        params=CompletionParams(
            position=Position(line=14, character=42),
            text_document=TextDocumentIdentifier(uri=uri),
        ))

  client.lsp.notify(
      method=CANCEL_REQUEST,
      params=dict(id='first-completion'),
  )

  req2 = client.lsp.send_request(
      method=COMPLETION,
      params=CompletionParams(
          position=Position(line=14, character=42),
          text_document=TextDocumentIdentifier(uri=uri),
      ))

  with pytest.raises(
      pygls.exceptions.JsonRpcRequestCancelled,
      match="Request Cancelled",
  ):
    assert req1.result(timeout=CALL_TIMEOUT)

  assert req2.result(timeout=CALL_TIMEOUT)
