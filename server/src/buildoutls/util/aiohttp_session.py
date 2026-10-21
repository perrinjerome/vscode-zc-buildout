from __future__ import annotations

import logging

import aiohttp

logger = logging.getLogger(__name__)
_session: aiohttp.ClientSession | None = None


def get_session() -> aiohttp.ClientSession:
  global _session
  if _session is None:
    logger.info("init")
    _session = aiohttp.ClientSession()
  return _session


async def close_session() -> None:
  global _session
  logger.info("closing")
  if _session is not None:
    await _session.close()
    _session = None
