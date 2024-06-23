from typing import List, Sequence

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
  """The project does not exists on pypi"""


class VersionNotFound(Exception):
  """The version does not exists on pypi"""


@attrs.define
class PyPIPackageInfo:
  latest_version: str
  url: str
  known_vulnerabilities: Sequence[KnownVulnerability]


# XXX command params are passed as dict in pygls 1.0
class OpenPypiPageCommandParams(TypedDict):
  url: str


class UpdateMD5SumCommandParams(TypedDict):
  document_uri: str
  section_name: str


# https://microsoft.github.io/language-server-protocol/specifications/lsp/3.18/specification/#textDocument_semanticTokens

SEMANTIC_TOKEN_TYPES = [
  "comment",
  "string",
  "number",
  "keyword",
  "class",
  "function",
  "variable",
  "type",
]
