import datetime
import logging
from typing import Iterable, Optional

import cachetools
import packaging.version
import pkg_resources
import requests

from .types import KnownVulnerability

logger = logging.getLogger(__name__)


class PyPIClient:
  def __init__(self, package_index_url: str = 'https://pypi.org'):
    self._package_index_url = package_index_url
    self._session = requests.Session()

  @cachetools.cached(
      cachetools.TTLCache(
          maxsize=2 << 10,
          ttl=datetime.timedelta(hours=2).total_seconds(),
      ))
  def get_latest_version(
      self,
      project: str,
      version: str,
  ) -> Optional[packaging.version.Version]:
    try:
      # https://warehouse.pypa.io/api-reference/json.html#project
      project_data = self._session.get(
          f'{self._package_index_url}/pypi/{project}/json').json()
    except (requests.RequestException, ValueError):
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

  @cachetools.cached(
      cachetools.TTLCache(
          maxsize=2 << 10,
          ttl=datetime.timedelta(hours=2).total_seconds(),
      ))
  def get_known_vulnerabilities(
      self,
      project: str,
      version: str,
  ) -> Iterable[KnownVulnerability]:
    return tuple(self.__get_known_vulnerabilities(project, version))

  def __get_known_vulnerabilities(
      self,
      project: str,
      version: str,
  ) -> Iterable[KnownVulnerability]:
    try:
      # https://warehouse.pypa.io/api-reference/json.html#release
      project_data = self._session.get(
          f'{self._package_index_url}/pypi/{project}/{version}/json').json()
    except (requests.RequestException, ValueError):
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
