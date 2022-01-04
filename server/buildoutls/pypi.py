import datetime
import logging
from typing import AsyncIterable, Iterable, List, Optional, TYPE_CHECKING

import cachetools
if TYPE_CHECKING:
  import cachetools as asyncache
else:
  import asyncache
import packaging.version
import pkg_resources
import aiohttp

from .types import KnownVulnerability

logger = logging.getLogger(__name__)


class PyPIClient:
  def __init__(self, package_index_url: str = 'https://pypi.org'):
    self._package_index_url = package_index_url
    self._session = aiohttp.ClientSession()

  @asyncache.cached(
      cachetools.TTLCache(
          maxsize=2 << 10,
          ttl=datetime.timedelta(hours=2).total_seconds(),
      ))
  async def get_latest_version(
      self,
      project: str,
      version: str,
  ) -> Optional[packaging.version.Version]:
    try:
      # https://warehouse.pypa.io/api-reference/json.html#project
      async with self._session as session:
        resp = await session.get(
            f'{self._package_index_url}/pypi/{project}/json')
        project_data = await resp.json()
    except (aiohttp.ClientError, ValueError):
      logger.warning(
          'Error fetching latest version for %s',
          project,
          exc_info=True,
      )
      return None
    current = pkg_resources.parse_version(version)
    latest = pkg_resources.parse_version(project_data['info']['version'])
    if latest > current:
      return latest
    return None

  @asyncache.cached(
      cachetools.TTLCache(
          maxsize=2 << 10,
          ttl=datetime.timedelta(hours=2).total_seconds(),
      ))
  async def get_known_vulnerabilities(
      self,
      project: str,
      version: str,
  ) -> Iterable[KnownVulnerability]:
    kvs: List[KnownVulnerability] = []
    async for kv in self.__get_known_vulnerabilities(project, version):
      kvs.append(kv)
    return tuple(kvs)

  async def __get_known_vulnerabilities(
      self,
      project: str,
      version: str,
  ) -> AsyncIterable[KnownVulnerability]:
    try:
      # https://warehouse.pypa.io/api-reference/json.html#release
      async with self._session as session:
        resp = await session.get(
            f'{self._package_index_url}/pypi/{project}/{version}/json')
        project_data = await resp.json()
    except (aiohttp.ClientError, ValueError):
      logger.warning(
          'Error fetching project release %s %s',
          project,
          version,
          exc_info=True,
      )
    else:
      parsed_version = pkg_resources.parse_version(version)
      for vulnerability in (KnownVulnerability(**v)
                            for v in project_data['vulnerabilities']):
        for fixed_in in (pkg_resources.parse_version(f)
                         for f in vulnerability.fixed_in):
          if fixed_in > parsed_version:
            yield vulnerability
            break

  def get_home_page_url(self, project: str, version: str) -> str:
    return f'{self._package_index_url}/project/{project}/{version}/'
