import asyncio
import functools
from typing import Callable, Coroutine, Optional, TypeVar

import sys
if sys.version_info >= (3, 10):
  from typing import ParamSpec
else:
  from typing_extensions import ParamSpec

T = TypeVar('T')
P = ParamSpec('P')

import time
import logging

logger = logging.getLogger(__name__)

#logging.getLogger('pygls.protocol').setLevel(logging.CRITICAL)
logging.getLogger('pygls.server').setLevel(logging.CRITICAL)
logging.getLogger('buildoutls.server').setLevel(logging.CRITICAL)
logging.getLogger('buildoutls.buildout').setLevel(logging.CRITICAL)

# TODO:
# complete on ${}|  cause match error
# at least on   A=BC ${}d de e e e e ezdzdze ${}|


def singleton_task(
    f: Callable[P, Coroutine[None, None, T]]
) -> Callable[P, Coroutine[None, None, T]]:
  """Wrap couroutine `f` in a task that will be executed only once at a time,
  cancelling the previous execution if it is still pending. 
  """
  _previous_singleton_task: Optional[asyncio.Task[T]] = None

  @functools.wraps(f)
  async def wrapped(*args: P.args, **kw: P.kwargs) -> T:
    nonlocal _previous_singleton_task
    if _previous_singleton_task is not None:
      _previous_singleton_task.cancel()
    if 0:
      logger.critical("executing %r [_previous_singleton_task=%r]", f,
                    _previous_singleton_task)

    _previous_singleton_task = asyncio.create_task(f(*args, **kw))
    start = time.perf_counter()
    try:
      return await _previous_singleton_task
    except asyncio.CancelledError:
      logger.critical(
          "cancelled %r in %0.3f",
          f,
          time.perf_counter() - start,
         # exc_info=True,
      )
      raise
    finally:
      pass
      if 0:
        logger.critical(
          "executed %r in %0.3f",
          f,
          time.perf_counter() - start,
      )
  #return f
  return wrapped
