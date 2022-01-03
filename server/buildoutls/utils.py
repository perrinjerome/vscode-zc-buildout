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

    _previous_singleton_task = asyncio.create_task(f(*args, **kw))
    return await _previous_singleton_task

  return wrapped
