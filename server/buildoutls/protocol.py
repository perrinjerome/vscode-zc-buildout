import asyncio
import collections
import logging
import time
from typing import Any, Deque, Set, Union
from typing_extensions import TypeAlias
from pygls.exceptions import JsonRpcRequestCancelled
from pygls.lsp.methods import CANCEL_REQUEST
from pygls.protocol import LanguageServerProtocol
from pygls.lsp.types import (JsonRpcMessage, JsonRPCNotification,
                             JsonRPCRequestMessage, JsonRPCResponseMessage)
from pygls.server import LanguageServer

logger = logging.getLogger(__name__)

handler = logging.FileHandler('/tmp/cancellations.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logger.addHandler(handler)

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
  _queue: Deque[CancellableQueueItemType]
  _early_cancellations: Set[Union[int, str]]
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
        #logger.debug('👍 Cancelled pending request %s', msg_id)
        break
    else:
      logger.debug(
          'Received cancellation for request %s not found in the queue (queue len: %s, early cancel: %s)',
          msg_id, len(self._queue), len(self._early_cancellations))
      self._early_cancellations.add(msg_id)

  def _init(self, maxsize: int) -> None:
    self._queue = collections.deque()
    self._early_cancellations = set()

  def _get(self) -> CancellableQueueItemType:
    return self._queue.popleft()

  def _put(self, item: CancellableQueueItemType) -> None:
    try:
      self._xput(item)
    except:
      logger.exception('putte')

  def _xput(self, item: CancellableQueueItemType) -> None:
    if hasattr(item, 'id'):
      msg_id = item.id
      if msg_id in self._early_cancellations:
        self._early_cancellations.remove(msg_id)
        logger.info("👍 not putting already cancelled %s", msg_id)
        item = CancelledJsonRPCRequestMessage(
            jsonrpc=item.jsonrpc,
            id=msg_id,
            method=item.method,
        )
    self._queue.append(item)


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
    self._server.loop.create_task(self._worker())
    def handler(exc, *args, **kw):
      logger.critical((exc, args, kw))
    self._server.loop.set_exception_handler(handler)


  def _procedure_handler(
      self,
      message: Union[JsonRPCNotification, JsonRPCRequestMessage,
                     JsonRPCResponseMessage],
  ) -> None:
    if isinstance(message, JsonRPCNotification) and message.method == CANCEL_REQUEST:
      self._job_queue.cancel(message.params.id)
    self._job_queue.put_nowait(message)

  # def X_handle_cancel_notification(self, msg_id: Union[int, str]) -> None:
  #   self._job_queue.cancel(msg_id)
  #   super()._handle_cancel_notification(msg_id)  # type: ignore
  async def _worker(self) -> None:
    while True:
      try:
        await self._xxx_worker()
      except Exception:
        logger.exception("oh merde")

  async def _xxx_worker(self) -> None:
    # TODO: cleanup
    def job_desc(job:CancellableQueueItemType) -> str:
      job_id = getattr(job, 'id', '-')
      return f'{job_id:>3} {job.method}'
    if 1:
      # with concurrent.futures.ProcessPoolExecutor() as pool:
      while not self._shutdown:
        # process protocol messages first
        while True:
          await asyncio.sleep(0.01)
          start = time.perf_counter_ns()
          try:
            job = await asyncio.wait_for(self._job_queue.get(), 0.3)
          except asyncio.TimeoutError:
            # logger.info("timeout getting a job in in %0.4f", (time.perf_counter_ns() - start) / 1e9)
            break
          logger.info(
              "got %s in in %0.4f %s",
              "cancelled 👍 job" if isinstance(job, CancelledJsonRPCRequestMessage) else "job", 
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
                error=JsonRpcRequestCancelled(),
            )
          else:
            super()._procedure_handler(job)  # type: ignore
          self._job_queue.task_done()

          logger.info("done in %0.4f %s", (time.perf_counter_ns() - start) / 1e9, job_desc(job))
        

        # once all protocol messages are done, process the tasks from notifications
        while True:
          start = time.perf_counter_ns()
          try:
            uri = self._diagnostic_queue.get_nowait()
          except asyncio.QueueEmpty:
            # logger.info("no diagnostic to do")
            break
          d = await self._server.do_diagnostic(uri)
          self._diagnostic_queue.task_done()
          logger.info("🔖(%d) done in %0.4f %s", d, (time.perf_counter_ns() - start) / 1e9, uri)
