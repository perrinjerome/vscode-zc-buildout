import asyncio
import datetime
import logging
from typing import AsyncIterable, Dict, Optional, Tuple, cast

import aiohttp
import cachetools
import packaging.version
import pkg_resources

from . import aiohttp_session
from .types import KnownVulnerability, VersionNotFound, ProjectNotFound
import cattrs

converter = cattrs.Converter()

logger = logging.getLogger(__name__)

# type aliases
Project = str
VersionStr = str
ProjectAndVersionStr = Tuple[Project, VersionStr]
OptionalVersion = Optional[packaging.version.Version]


class PyPIClient:
  def __init__(self, package_index_url: str = 'https://pypi.org'):
    self._package_index_url = package_index_url
    self.__get_latest_version_cache = cast(
        Dict[ProjectAndVersionStr, OptionalVersion],
        cachetools.TTLCache(
            maxsize=2 << 10,
            ttl=datetime.timedelta(hours=2).total_seconds(),
        ))
    self.__get_known_vulnerabilities_cache = cast(
        Dict[ProjectAndVersionStr, Tuple[KnownVulnerability, ...]],
        cachetools.TTLCache(
            maxsize=2 << 10,
            ttl=datetime.timedelta(hours=2).total_seconds(),
        ))

  async def get_latest_version(
      self,
      project: str,
      version: str,
      semaphore: asyncio.Semaphore,
  ) -> OptionalVersion:
    try:
      return self.__get_latest_version_cache[project, version]
    except KeyError:
      pass
    async with semaphore:
      latest_version = await self.__get_latest_version(project, version)
    try:
      self.__get_latest_version_cache[project, version] = latest_version
    except ValueError:
      pass
    return latest_version

  async def __get_latest_version(
      self,
      project: str,
      version: str,
  ) -> OptionalVersion:
    try:
      # https://warehouse.pypa.io/api-reference/json.html#project
      async with aiohttp_session.get_session().get(
          f'{self._package_index_url}/pypi/{project}/json') as resp:
        project_data = await resp.json()
    except (aiohttp.ClientError, ValueError, asyncio.TimeoutError):
      logger.warning(
          'Error fetching latest version for %s',
          project,
          exc_info=True,
      )
      return None
    if 'info' not in project_data:
      raise ProjectNotFound(project)
    if version not in project_data['releases']:
      version = '0'
    current = pkg_resources.parse_version(version)
    latest = pkg_resources.parse_version(project_data['info']['version'])
    if latest > current:
      return cast(packaging.version.Version, latest)
    return None

  async def get_known_vulnerabilities(
      self,
      project: str,
      version: str,
      semaphore: asyncio.Semaphore,
  ) -> Tuple[KnownVulnerability, ...]:
    try:
      return self.__get_known_vulnerabilities_cache[project, version]
    except KeyError:
      pass
    vulnerabilities = tuple([
        v async for v in self.__get_known_vulnerabilities(
            project, version, semaphore)
    ])
    try:
      self.__get_known_vulnerabilities_cache[project,
                                             version] = vulnerabilities
    except ValueError:
      pass
    return vulnerabilities

  async def __get_known_vulnerabilities(
      self,
      project: str,
      version: str,
      semaphore: asyncio.Semaphore,
  ) -> AsyncIterable[KnownVulnerability]:
    try:
      # https://warehouse.pypa.io/api-reference/json.html#release
      async with semaphore:
        async with aiohttp_session.get_session().get(
            f'{self._package_index_url}/pypi/{project}/{version}/json',
        ) as resp:
          project_data = await resp.json()
    except (aiohttp.ClientError, ValueError, asyncio.TimeoutError):
      logger.warning(
          'Error fetching project release %s %s',
          project,
          version,
          exc_info=True,
      )
    else:
      if 'info' not in project_data:
        raise VersionNotFound((project, version))
      parsed_version = pkg_resources.parse_version(version)
      for vulnerability in (converter.structure(v, KnownVulnerability)
                            for v in project_data.get('vulnerabilities', ())):
        for fixed_in in (pkg_resources.parse_version(f)
                         for f in vulnerability.fixed_in):
          if fixed_in > parsed_version:
            yield vulnerability
            break

  def get_home_page_url(self, project: str, version: str) -> str:
    return f'{self._package_index_url}/project/{project}/{version}/'
