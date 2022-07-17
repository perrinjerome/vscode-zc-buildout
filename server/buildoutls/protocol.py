import asyncio
import collections
import logging
import time
from typing import TYPE_CHECKING, Any, Deque, Set, Union

from pygls.exceptions import JsonRpcRequestCancelled
from pygls.lsp.methods import CANCEL_REQUEST
from pygls.lsp.types import (
    JsonRpcMessage,
    JsonRPCNotification,
    JsonRPCRequestMessage,
    JsonRPCResponseMessage,
)
from pygls.protocol import LanguageServerProtocol
from pygls.server import LanguageServer
from typing_extensions import TypeAlias

logger = logging.getLogger(__name__)

JsonRPCMessageId: TypeAlias = Union[int, str]


class CancelledJsonRPCRequestMessage(JsonRpcMessage):
  """A request that was cancelled"""
  id: JsonRPCMessageId
  method: str


JsonRPCMessage: TypeAlias = Union[JsonRPCNotification, JsonRPCRequestMessage,
                                  JsonRPCResponseMessage]

# Type for items
CancellableQueueItem: TypeAlias = Union[JsonRPCMessage,
                                        CancelledJsonRPCRequestMessage]


if TYPE_CHECKING:
  BaseQueue: TypeAlias = asyncio.Queue[CancellableQueueItem]
else:
  BaseQueue = asyncio.Queue

class CancellableQueue(BaseQueue):
  _queue: Deque[CancellableQueueItem]

  # TODO: _early_cancellations might not be needed
  _early_cancellations: Set[JsonRPCMessageId]

  def cancel(self, msg_id: JsonRPCMessageId) -> None:
    """Mark a message in the queue as cancelled.
    """
    for i, item in enumerate(self._queue):
      if isinstance(item, JsonRPCRequestMessage) and item.id == msg_id:
        self._queue[i] = CancelledJsonRPCRequestMessage(
            jsonrpc=item.jsonrpc,
            id=msg_id,
            method=item.method,
        )
        break
    else:
      logger.debug(
          'Received cancellation for request %s not found in the queue (queue len: %s, early cancel: %s)',
          msg_id, len(self._queue), len(self._early_cancellations))
      self._early_cancellations.add(msg_id)

  def _init(self, maxsize: int) -> None:
    self._queue = collections.deque()
    self._early_cancellations = set()

  def _get(self) -> CancellableQueueItem:
    return self._queue.popleft()

  def _put(self, item: CancellableQueueItem) -> None:
    if isinstance(item, (JsonRPCRequestMessage, JsonRPCResponseMessage)):
      msg_id = item.id
      if msg_id in self._early_cancellations:
        self._early_cancellations.remove(msg_id)
        logger.debug("👍 not putting already cancelled %s", msg_id)
        item = CancelledJsonRPCRequestMessage(
            jsonrpc=item.jsonrpc,
            id=msg_id,
            method=getattr(item, 'method', '-'),
        )
    self._queue.append(item)


class CancellableQueueLanguageServerProtocol(LanguageServerProtocol):
  """Extension to pygls default LanguageServerProtocol with better support for
  request cancelled by the client.
  
  The general approach is that we use a queue of messages and a worker
  coroutine to process the messages.
  When a new request, notification or response message is received, instead
  of processing it directly, we put it in the queue and keep reading next
  messages.

  If the notification is a cancel notification, we go through the queue to
  mark the message as cancelled before it get processed.
  """
  _server: LanguageServer
  _diagnostic_queue: Any

  def __init__(self, server: LanguageServer):
    super().__init__(server)  # type: ignore
    self._job_queue = CancellableQueue()
    self._worker_started = False

  def _procedure_handler(
      self,
      message: Union[JsonRPCNotification, JsonRPCRequestMessage,
                     JsonRPCResponseMessage],
  ) -> None:
    if not self._worker_started:
      self._server.loop.create_task(self._worker())
      self._worker_started = True

    if isinstance(message,
                  JsonRPCNotification) and message.method == CANCEL_REQUEST:
      self._job_queue.cancel(message.params.id)
    self._job_queue.put_nowait(message)

  async def _worker(self) -> None:
    def job_desc(job: CancellableQueueItem) -> str:
      job_id = getattr(job, 'id', '-')
      job_method = getattr(job, 'method', '-')
      return f'{job_id:>3} {job_method}'

    while not self._server._stop_event.is_set():
      # process protocol messages first
      while True:
        await asyncio.sleep(0.1)
        start = time.perf_counter_ns()
        try:
          # TODO: we don't need wait for here ?
          job = await asyncio.wait_for(self._job_queue.get(), 0.3)
        except asyncio.TimeoutError:
          # logger.info("timeout getting a job in in %0.4f", (time.perf_counter_ns() - start) / 1e9)
          break
        logger.info(
            "got %s in in %0.4f %s",
            "cancelled 👍 job"
            if isinstance(job, CancelledJsonRPCRequestMessage) else "job",
            (time.perf_counter_ns() - start) / 1e9,
            job_desc(job),
        )

        start = time.perf_counter_ns()
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
              error=JsonRpcRequestCancelled(),  # type: ignore
          )
        else:
          super()._procedure_handler(job)  # type: ignore
        self._job_queue.task_done()

        logger.debug("done in %0.4f %s",
                     (time.perf_counter_ns() - start) / 1e9, job_desc(job))

      # once all protocol messages are done, process the tasks from notifications
      while True:
        start = time.perf_counter_ns()
        try:
          uri = self._diagnostic_queue.get_nowait()
        except asyncio.QueueEmpty:
          break

        # TODO
        d = await self._server.do_diagnostic(uri)  # type: ignore
        self._diagnostic_queue.task_done()
        logger.debug("🔖(%d) done in %0.4f %s", d,
                     (time.perf_counter_ns() - start) / 1e9, uri)
