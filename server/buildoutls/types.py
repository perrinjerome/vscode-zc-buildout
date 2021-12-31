from typing import List

from pygls.lsp.types import TextDocumentIdentifier

import pydantic


class KnownVulnerability(pydantic.BaseModel):
  aliases: List[str]
  details: str
  fixed_in: List[str]
  id: str
  link: str
  source: str


class PyPIPackageInfo(pydantic.BaseModel):
  latest_version: str
  url: str
  known_vulnerabilities: List[KnownVulnerability]


class OpenPypiPageCommandParams(pydantic.BaseModel):
  url: str


class UpdateMD5SumCommandParams(pydantic.BaseModel):
  document: TextDocumentIdentifier
  section_name: str
