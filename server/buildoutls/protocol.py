import asyncio
import logging
from typing import List, Union
from typing_extensions import TypeAlias
from pygls.exceptions import JsonRpcRequestCancelled
from pygls.protocol import LanguageServerProtocol
from pygls.lsp.types import (JsonRpcMessage, JsonRPCNotification,
                             JsonRPCRequestMessage, JsonRPCResponseMessage)
from pygls.server import LanguageServer

logger = logging.getLogger(__name__)


class CancelledJsonRPCRequestMessage(JsonRpcMessage):
  """A request that was cancelled"""
  id: Union[int, str]
  method: str


JsonRPCMessageType: TypeAlias = Union[JsonRPCNotification,
                                      JsonRPCRequestMessage,
                                      JsonRPCResponseMessage]

# Type for items
CancellableQueueItemType: TypeAlias = Union[JsonRPCMessageType,
                                            CancelledJsonRPCRequestMessage]


class CancellableQueue(asyncio.Queue[CancellableQueueItemType]):
  """LIFO queue 
  """
  _queue: List[CancellableQueueItemType]

  def cancel(self, msg_id: Union[int, str]) -> None:
    """Mark a message in the queue as cancelled.
    """
    for i, item in enumerate(self._queue):
      if isinstance(item, JsonRPCRequestMessage) and item.id == msg_id:
        self._queue[i] = CancelledJsonRPCRequestMessage(
            jsonrpc=item.jsonrpc,
            id=msg_id,
            method=item.method,
        )
        logger.debug('Cancelled pending request %s', msg_id)
        break
    else:
      logger.debug(
          'Warning: received cancellation for request %s not in the queue',
          msg_id)

  def _init(self, maxsize: int) -> None:
    self._queue = []

  def _put(self, item: CancellableQueueItemType) -> None:
    self._queue.append(item)

  def _get(self) -> CancellableQueueItemType:
    return self._queue.pop()


class CancellableQueueLanguageServerProtocol(LanguageServerProtocol):
  """Extension to pygls default LanguageServerProtocol with better support for
  request cancelled by the client.
  
  The general approach is that we use a LIFO queue of messages and a worker
  coroutine to process the messages.
  When a new request, notification or response message is received, instead
  of processing it directly, we put it in the queue and keep reading next
  messages.

  If the notification is a cancel notification, we go through the queue to
  mark the message as cancelled before it get processed.
  """
  _server: LanguageServer

  def __init__(self, server: LanguageServer):
    super().__init__(server)
    self._job_queue = CancellableQueue()
    self._server.loop.create_task(self.worker())

  def _procedure_handler(
      self,
      message: Union[JsonRPCNotification, JsonRPCRequestMessage,
                     JsonRPCResponseMessage],
  ) -> None:
    self._job_queue.put_nowait(message)

  def _handle_cancel_notification(self, msg_id: Union[int, str]) -> None:
    self._job_queue.cancel(msg_id)
    super()._handle_cancel_notification(msg_id)  # type: ignore

  async def worker(self) -> None:
    # TODO: cleanup
    import concurrent.futures
    with concurrent.futures.ProcessPoolExecutor() as pool:
      while not self._shutdown:

        job = await self._job_queue.get()
        await asyncio.sleep(0.01)

        if isinstance(job, CancelledJsonRPCRequestMessage):
          # according to https://microsoft.github.io/language-server-protocol/specifications/specification-current/#cancelRequest
          # A request that got canceled still needs to return from the server
          # and send a response back. It can not be left open / hanging. This
          # is in line with the JSON RPC protocol that requires that every
          # request sends a response back. In addition it allows for returning
          # partial results on cancel. If the request returns an error response
          # on cancellation it is advised to set the error code to
          # ErrorCodes.RequestCancelled.
          self._send_response(  # type: ignore
              job.id,
              result=None,
              error=JsonRpcRequestCancelled(),
          )
        else:
          super()._procedure_handler(job)  # type: ignore
        self._job_queue.task_done()
