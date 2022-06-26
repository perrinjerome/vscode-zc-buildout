import logging
import typing

import aiohttp

logger = logging.getLogger(__name__)
_session: typing.Optional[aiohttp.ClientSession] = None


def get_session() -> aiohttp.ClientSession:
  global _session
  if _session is None:
    logging.info("init")
    _session = aiohttp.ClientSession()
  return _session


async def close_session() -> None:
  global _session
  logging.info("closing")
  if _session is not None:
    await _session.close()
    _session = None