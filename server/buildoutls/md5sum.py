import hashlib

import requests
from pygls.lsp.types import (
    Location,
    MessageType,
    Position,
    Range,
    TextEdit,
    WorkspaceEdit,
)
from pygls.server import LanguageServer

from . import buildout
from .types import UpdateMD5SumCommandParams


async def update_md5sum(
    ls: LanguageServer,
    params: UpdateMD5SumCommandParams,
) -> None:
  profile = await buildout.open(ls, params.document.uri)
  assert isinstance(profile, buildout.BuildoutProfile)
  section = profile[params.section_name]
  url = profile.resolve_value(params.section_name, "url")

  m = hashlib.md5()
  resp = requests.get(url, stream=True)
  if not resp.ok:
    ls.show_message(
        f"Could not update md5sum: {url} had status code {resp.status_code}",
        MessageType.Error,
    )
    return
  for chunk in resp.iter_content(2 << 12):
    m.update(chunk)
  hexdigest = m.hexdigest()

  if 'md5sum' in section:
    md5sum_location = section['md5sum'].location
    new_text = " " + hexdigest
  else:
    # if no md5sum option in profile, insert a line just below url
    url_location = section['url'].location
    md5sum_location = Location(
        uri=url_location.uri,
        range=Range(
            start=Position(
                line=url_location.range.start.line + 1,
                character=0,
            ),
            end=Position(
                line=url_location.range.start.line + 1,
                character=0,
            ),
        ),
    )
    new_text = f"md5sum = {hexdigest}\n"

  ls.apply_edit(
      WorkspaceEdit(
          changes={
              md5sum_location.uri:
              [TextEdit(
                  range=md5sum_location.range,
                  new_text=new_text,
              )]
          }))
