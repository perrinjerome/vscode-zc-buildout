from typing import List

import attrs
from typing_extensions import TypedDict


@attrs.define
class KnownVulnerability:
  aliases: List[str]
  details: str
  fixed_in: List[str]
  id: str
  link: str
  source: str


class ProjectNotFound(Exception):
  """The project does not exists on pypi
  """


class VersionNotFound(Exception):
  """The version does not exists on pypi
  """


@attrs.define
class PyPIPackageInfo:
  latest_version: str
  url: str
  known_vulnerabilities: List[KnownVulnerability]


# XXX command params are passed as dict in pygls 1.0
class OpenPypiPageCommandParams(TypedDict):
  url: str


class UpdateMD5SumCommandParams(TypedDict):
  document_uri: str
  section_name: str
