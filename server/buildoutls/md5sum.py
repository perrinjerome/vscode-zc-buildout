import hashlib
import time
import uuid

from lsprotocol.types import (
    Location,
    MessageType,
    Position,
    Range,
    TextEdit,
    WorkDoneProgressBegin,
    WorkDoneProgressEnd,
    WorkDoneProgressReport,
    WorkspaceEdit,
)
from pygls.server import LanguageServer

from . import aiohttp_session, buildout
from .types import UpdateMD5SumCommandParams


async def update_md5sum(
    ls: LanguageServer,
    params: UpdateMD5SumCommandParams,
) -> None:
  profile = await buildout.open(ls, params['document_uri'])
  assert isinstance(profile, buildout.BuildoutProfile)
  section = profile[params['section_name']]
  url = profile.resolve_value(params['section_name'], "url")

  token = str(uuid.uuid4())
  await ls.progress.create_async(token)
  ls.progress.begin(
      token,
      WorkDoneProgressBegin(
          cancellable=True,  # TODO actually support cancellation
          title=f"Updating md5sum for {url}",
      ))

  start = time.time()
  m = hashlib.md5()

  async with aiohttp_session.get_session().get(url) as resp:

    if not resp.ok:
      ls.show_message(
          f"Could not update md5sum: {url} had status code {resp.status}",
          MessageType.Error,
      )
      ls.progress.end(token, WorkDoneProgressEnd(kind='end'))
      return

    download_total_size = int(resp.headers.get('content-length', '-1'))
    downloaded_size = 0
    async for chunk in resp.content.iter_chunked(2 << 14):
      m.update(chunk)
      downloaded_size += len(chunk)

      elapsed_time = time.time() - start
      percentage = (downloaded_size / download_total_size * 100)
      ls.progress.report(
          token,
          WorkDoneProgressReport(
              message=f"{percentage:0.2f}% in {elapsed_time:0.2f}s",
              percentage=max(0, int(percentage)),
          ))

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

  ls.progress.end(token, WorkDoneProgressEnd())
  ls.apply_edit(
      WorkspaceEdit(
          changes={
              md5sum_location.uri:
              [TextEdit(
                  range=md5sum_location.range,
                  new_text=new_text,
              )]
          }))
