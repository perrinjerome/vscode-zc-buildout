import logging
from typing import List, Optional, Union

from pygls.lsp.types import (
    CodeAction,
    CodeActionKind,
    CodeActionParams,
    Command,
    TextEdit,
    WorkspaceEdit,
)
from pygls.server import LanguageServer

from .commands import COMMAND_OPEN_PYPI_PAGE, COMMAND_UPDATE_MD5SUM
from .types import OpenPypiPageCommandParams, PyPIPackageInfo, UpdateMD5SumCommandParams

logger = logging.getLogger(__name__)

from . import buildout, pypi

pypi_client = pypi.PyPIClient()


async def getCodeActions(
    ls: LanguageServer,
    params: CodeActionParams,
) -> Optional[List[Union[Command, CodeAction]]]:
  current_line = params.range.start.line

  code_actions: List[Union[Command, CodeAction]] = []

  parsed = await buildout.open(ls, params.text_document.uri)
  if not isinstance(parsed, buildout.BuildoutProfile):
    return None
  symbol = await parsed.getSymbolAtPosition(params.range.end)
  if not symbol:
    return None
  if symbol.current_option_name is None or symbol.current_section_name is None:
    return None

  try:
    value = parsed.resolve_value(
        symbol.current_section_name,
        symbol.current_option_name,
    )
  except KeyError:
    return None
  logger.debug(
      "getting code actions resolved value=%s symbol=%s",
      value,
      symbol,
  )
  if symbol.current_section_name == 'versions' and symbol.current_option_name:
    url = pypi_client.get_home_page_url(
        symbol.current_option_name,
        symbol.value,
    )
    code_actions.append(
        CodeAction(
            title=f"View on pypi {url}",
            command=Command(
                title="View on pypi",
                command=COMMAND_OPEN_PYPI_PAGE,
                arguments=[OpenPypiPageCommandParams(url=url)],
            ),
        ), )
  elif symbol.current_option_name in ("url", "md5sum") \
        and "url" in symbol.current_section:
    return [
        CodeAction(
            title="Update md5sum",
            kind=CodeActionKind.QuickFix,
            command=Command(
                title="Update md5sum",
                command=COMMAND_UPDATE_MD5SUM,
                arguments=[
                    UpdateMD5SumCommandParams(
                        document=params.text_document,
                        section_name=symbol.current_section_name,
                    )
                ],
            ),
        )
    ]

  for diagnostic in params.context.diagnostics:
    if diagnostic.data and diagnostic.range.start.line == current_line:
      try:
        package_info = PyPIPackageInfo(**diagnostic.data)
      except Exception:
        logging.debug(
            "Unable to convert diagnostic data %s",
            diagnostic.data,
            exc_info=True,
        )
        return None
      edit = WorkspaceEdit(
          changes={
              params.text_document.uri: [
                  TextEdit(
                      range=diagnostic.range,
                      new_text=' ' + package_info.latest_version,
                  ),
              ]
          })
      code_actions.insert(
          0,
          CodeAction(
              title=f"Use version {package_info.latest_version}",
              kind=CodeActionKind.QuickFix,
              edit=edit,
              is_preferred=True,
          ),
      )
  return code_actions
