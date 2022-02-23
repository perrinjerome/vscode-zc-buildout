import asyncio
import datetime
import itertools
import logging
import os
import pathlib
import re
import urllib.parse
from asyncio import Future
from typing import Any, Iterable, List, Optional, Tuple, Union

import pydantic
import pygls.protocol
from pygls.lsp.methods import (CODE_ACTION, COMPLETION, DEFINITION,
                               DOCUMENT_LINK, DOCUMENT_SYMBOL, HOVER,
                               REFERENCES, TEXT_DOCUMENT_DID_CHANGE,
                               TEXT_DOCUMENT_DID_OPEN,
                               WORKSPACE_DID_CHANGE_WATCHED_FILES)
from pygls.lsp.types import (
    CodeAction, CodeActionKind, CodeActionOptions, CodeActionParams, Command,
    CompletionItem, CompletionItemKind, CompletionOptions, CompletionParams,
    DidChangeTextDocumentParams, DidChangeWatchedFilesParams,
    DidOpenTextDocumentParams, DocumentLink, DocumentLinkParams,
    DocumentSymbol, DocumentSymbolParams, Hover, Location, MarkupContent,
    MarkupKind, Position, Range, SymbolKind, TextDocumentPositionParams,
    TextEdit)
from pygls.lsp.types.window import ShowDocumentParams
from pygls.server import LanguageServer
from pygls.workspace import Document

from . import (
    buildout,
    code_actions,
    commands,
    diagnostic,
    md5sum,
    recipes,
    types,
    utils,
)


class CallStat(pydantic.BaseModel):
  feature_name: str
  timestamp: datetime.datetime
  duration: Optional[datetime.timedelta] = None
  msgid: Optional[Union[int, str]] = None
  cancelled: bool = False


class StatsCollectingLanguageServerProtocol(
    pygls.protocol.LanguageServerProtocol):
  def __init__(self, server: LanguageServer):
    super().__init__(server)


# https://microsoft.github.io/language-server-protocol/specifications/specification-current/#cancelRequest
# A request that got canceled still needs to return from the server and send a
# response back. It can not be left open / hanging. This is in line with the
# JSON RPC protocol that requires that every request sends a response back.
# In addition it allows for returning partial results on cancel. If the request
# returns an error response on cancellation it is advised to set the error code
# to ErrorCodes.RequestCancelled.

from pygls.lsp.types.basic_structures import (JsonRpcMessage,
                                              JsonRPCNotification,
                                              JsonRPCRequestMessage,
                                              JsonRPCResponseMessage)

JsonRPCMessageType = Union[JsonRPCNotification, JsonRPCRequestMessage,
                           JsonRPCResponseMessage]

class CancelledJsonRPCRequestMessage(JsonRpcMessage):
  """A request that was cancelled"""
  id: Union[int, str]
  method: str


CancellableQueueItemType = Union[JsonRPCMessageType,
                                           CancelledJsonRPCRequestMessage]
class CancellableQueue(asyncio.Queue[CancellableQueueItemType]):
  """LIFO queue 
  """
  _queue: List[CancellableQueueItemType]

  def cancel(self, msg_id: Union[int, str]) -> None:
    """Mark a message in the queue as cancelled.
    """
    for i, item in enumerate(self._queue):
      if isinstance(item, JsonRPCRequestMessage) and item.id == msg_id:
        self._queue[i] = CancelledJsonRPCRequestMessage(
            jsonrpc=item.jsonrpc,
            id=msg_id,
            method=item.method,
        )
        logger.debug('Cancelled pending request %s', msg_id)
        break
    else:
      logger.debug(
          'Warning: received cancellation for request %s not in the queue',
          msg_id)

  def _init(self, maxsize: int) -> None:
    self._queue = []

  def _put(self, item: CancellableQueueItemType) -> None:
    self._queue.append(item)

  def _get(self) -> CancellableQueueItemType:
    return self._queue.pop()


class CancellableQueueLanguageServerProtocol(
    pygls.protocol.LanguageServerProtocol):
  """Extension to pygls default LanguageServerProtocol with better support for
  request cancelled by the client.
  
  The general approach is that we use a LIFO queue of messages and a worker
  coroutine to process the messages.
  When a new request, notification or response message is received, instead
  of processing it directly, we put it in the queue and keep reading next
  messages.

  If the notification is a cancel notification, we go through the queue to
  mark the message as cancelled before it get processed.
  """
  _server: LanguageServer

  def __init__(self, server: LanguageServer):
    super().__init__(server)
    self._job_queue = CancellableQueue()
    self._server.loop.create_task(self.worker())

  def _procedure_handler(
      self,
      message: Union[JsonRPCNotification, JsonRPCRequestMessage,
                     JsonRPCResponseMessage],
  ) -> None:
    self._job_queue.put_nowait(message)

  def _handle_cancel_notification(self, msg_id: Union[int, str]) -> None:
    self._job_queue.cancel(msg_id)
    super()._handle_cancel_notification(msg_id) # type: ignore

  async def worker(self) -> None:
    # TODO: cleanup
    import concurrent.futures
    while not self._shutdown:
      with concurrent.futures.ProcessPoolExecutor() as pool:

        job = await self._job_queue.get()
        await asyncio.sleep(0.01)
        if isinstance(job, CancelledJsonRPCRequestMessage):
          self._send_response(  # type: ignore
              job.id,
              result=None,
              error=pygls.exceptions.JsonRpcRequestCancelled(), # xxxtype: ignore
          )
        else:
          super()._procedure_handler(job)  # type: ignore
        self._job_queue.task_done()


server = LanguageServer(max_workers=10,
                        protocol_cls=CancellableQueueLanguageServerProtocol)


@server.command('dumpDebugStats')
def dump_debug_stats(ls: LanguageServer) -> None:
  ls.dump_debug_stats()  # type: ignore


reference_start = '${'
reference_re = re.compile(
    r'\${(?P<section>[-a-zA-Z0-9 ._]*):(?P<option>[-a-zA-Z0-9 ._]+)}')
logger = logging.getLogger(__name__)


def getOptionValue(
    option: Union[buildout.BuildoutOptionDefinition, str]) -> str:
  # Options read with our patch remember the position and have their values in
  # .value but options added by buildout for default values does not.
  # We normalize this here.
  if isinstance(option, str):
    return option
  return option.value


@utils.singleton_task
async def parseAndSendDiagnostics(
    ls: LanguageServer,
    uri: str,
) -> None:
  diagnostics = []
  await asyncio.sleep(0.1)
  async for diag in diagnostic.getDiagnostics(ls, uri):
    diagnostics.append(diag)
  ls.publish_diagnostics(uri, diagnostics)


@server.command(commands.COMMAND_OPEN_PYPI_PAGE)
async def command_open_pypi_page(
    ls: LanguageServer,
    args: List[types.OpenPypiPageCommandParams],
) -> None:
  await ls.show_document_async(
      ShowDocumentParams(
          uri=args[0].url,
          external=True,
      ))


@server.command(commands.COMMAND_UPDATE_MD5SUM)
async def command_update_md5sum(
    ls: LanguageServer,
    args: List[types.UpdateMD5SumCommandParams],
) -> None:
  await md5sum.update_md5sum(ls, args[0])


@server.feature(
    CODE_ACTION,
    CodeActionOptions(resolve_provider=False,
                      code_action_kinds=[
                          CodeActionKind.QuickFix,
                      ]),
)
#@utils.singleton_task
async def lsp_code_action(
    ls: LanguageServer,
    params: CodeActionParams) -> Optional[List[Union[Command, CodeAction]]]:
  return await code_actions.getCodeActions(ls, params)


@server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(
    ls: LanguageServer,
    params: DidOpenTextDocumentParams,
) -> None:
  await parseAndSendDiagnostics(ls, params.text_document.uri)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
async def did_change(
    ls: LanguageServer,
    params: DidChangeTextDocumentParams,
) -> None:
  buildout.clearCache(params.text_document.uri)
  await parseAndSendDiagnostics(ls, params.text_document.uri)


@server.feature(WORKSPACE_DID_CHANGE_WATCHED_FILES)
async def did_change_watched_file(
    ls: LanguageServer,
    params: DidChangeWatchedFilesParams,
) -> None:
  for change in params.changes:
    buildout.clearCache(change.uri)


@server.feature(DOCUMENT_SYMBOL)
#@utils.singleton_task
async def lsp_symbols(
    ls: LanguageServer,
    params: DocumentSymbolParams,
) -> List[DocumentSymbol]:
  symbols: List[DocumentSymbol] = []

  parsed = await buildout.parse(
      ls=ls,
      uri=params.text_document.uri,
      allow_errors=True,
  )

  for section_name, section_value in parsed.items():
    section_header_location = parsed.section_header_locations[section_name]
    # don't include implicit sections such as [buildout] unless defined in this profile.
    if section_header_location.uri != params.text_document.uri:
      continue
    children: List[DocumentSymbol] = []
    for option_name, option_value in section_value.items():
      if option_value.default_value:
        continue
      option_range = Range(
          start=Position(line=min(r.range.start.line
                                  for r in option_value.locations),
                         character=0),
          end=Position(line=max(r.range.end.line
                                for r in option_value.locations),
                       character=0))
      detail = getOptionValue(option_value)
      if len(detail.splitlines()) > 1:
        #  vscode does not like too long multi-lines detail
        detail = '{} ...'.format(detail.splitlines()[0])
      children.append(
          DocumentSymbol(name=option_name,
                         kind=SymbolKind.Field,
                         range=option_range,
                         selection_range=option_range,
                         detail=detail,
                         children=[]))
    section_range = Range(
        start=section_header_location.range.start,
        end=Position(
            line=max(s.range.end.line for s in children)
            if children else section_header_location.range.end.line,
            character=0,
        ),
    )

    symbols.append(
        DocumentSymbol(
            name=section_name,
            kind=SymbolKind.Class,
            range=section_range,
            selection_range=section_range,
            detail=getOptionValue(section_value.get('recipe', '')),
            children=children,
        ))
  return symbols


@server.feature(COMPLETION, CompletionOptions(trigger_characters=["{", ":"]))
#@utils.singleton_task
async def lsp_completion(
    ls: LanguageServer,
    params: CompletionParams,
) -> Optional[List[CompletionItem]]:
  items: List[CompletionItem] = []
  doc = ls.workspace.get_document(params.text_document.uri)
  await asyncio.sleep(0.02)

  def getSectionReferenceCompletionTextEdit(
      doc: Document,
      pos: Position,
      new_text: str,
  ) -> TextEdit:
    """Calculate the edition to insert ${section: in ${section:option}
    """
    words_split = re.compile(r'\$\{[-a-zA-Z0-9 ._]*')
    line = doc.lines[pos.line]
    index = 0
    while True:
      match = words_split.search(line, index)
      assert match
      if match.start() <= pos.character <= match.end():
        start = match.start()
        end = match.end()
        return TextEdit(
            range=Range(start=Position(line=pos.line, character=start),
                        end=Position(line=pos.line, character=end)),
            new_text=new_text,
        )
      index = max(match.start(), index + 1)

    return TextEdit(
        Range(
            start=Position(line=pos.line, character=pos.character),
            end=Position(line=pos.line, character=pos.character),
        ),
        new_text=new_text,
    )

  def getOptionReferenceTextEdit(
      doc: Document,
      pos: Position,
      new_text: str,
  ) -> TextEdit:
    """Calculate the edition to insert option} a ${section:option}
    """
    words_split = re.compile(
        r'(?P<section>\${[-a-zA-Z0-9 ._]*\:)(?P<option>[-a-zA-Z0-9._]*\}{0,1})'
    )
    line = doc.lines[pos.line]
    index = 0
    while True:
      match = words_split.search(line, index)
      assert match
      section_len = len(match.group('section'))
      if match.start() + section_len <= pos.character <= match.end():
        start = match.start() + section_len
        end = match.end()
        return TextEdit(
            range=Range(start=Position(line=pos.line, character=start),
                        end=Position(line=pos.line, character=end)),
            new_text=new_text,
        )
      index = max(match.start(), index + 1)

    return TextEdit(
        range=Range(
            start=Position(line=pos.line, character=pos.character),
            end=Position(line=pos.line, character=pos.character),
        ),
        new_text=new_text,
    )

  def getDefaultTextEdit(
      doc: Document,
      pos: Position,
      new_text: str,
  ) -> TextEdit:
    """Calculate the edition to replace the current token at position by the new text.
    """
    # regex to split the current token, basically we consider everything a word
    # but stop at substitution start and end.
    words_split = re.compile(r'[-a-zA-Z0-9\._\$\{\/]*')
    line = ''
    if len(doc.lines) > pos.line:
      line = doc.lines[pos.line]
    if not line.strip():
      return TextEdit(
          range=Range(
              start=Position(line=pos.line, character=pos.character),
              end=Position(line=pos.line, character=pos.character),
          ),
          new_text=new_text,
      )
    index = 0
    while True:
      match = words_split.search(line, index)
      assert match
      if match.start() <= pos.character <= match.end():
        start = match.start()
        end = match.end()
        # if end was a '}', erase it
        if (line + '  ')[end] == '}':
          end += 1
        # TODO: test
        return TextEdit(
            range=Range(start=Position(line=pos.line, character=start),
                        end=Position(line=pos.line, character=end)),
            new_text=new_text,
        )
      index = max(match.start(), index + 1)

  parsed = await buildout.open(ls, params.text_document.uri)
  if parsed is None:
    return None
  symbol = await parsed.getSymbolAtPosition(params.position)
  logger.debug("getting completions on %s", symbol)
  if symbol:
    if symbol.kind == buildout.SymbolKind.Comment:
      return None
    if symbol.kind == buildout.SymbolKind.SectionReference:
      for buildout_section_name, section_items in symbol._buildout.items():
        documentation = '```ini\n{}\n```'.format(
            '\n'.join('{} = {}'.format(k, v.value)
                      for (k, v) in section_items.items()
                      if v and not v.default_value), )
        if section_items.get('recipe'):
          recipe = section_items.getRecipe()
          if recipe:
            documentation = f'{recipe.documentation}\n\n---\n{documentation}'
          else:
            documentation = f'## `{section_items["recipe"].value}`\n\n---\n{documentation}'

        items.append(
            CompletionItem(label=buildout_section_name,
                           text_edit=getSectionReferenceCompletionTextEdit(
                               doc,
                               params.position,
                               '${' + buildout_section_name,
                           ),
                           filter_text='${' + buildout_section_name,
                           kind=CompletionItemKind.Class,
                           documentation=MarkupContent(
                               kind=MarkupKind.Markdown,
                               value=documentation,
                           )))
    elif symbol.kind == buildout.SymbolKind.OptionReference:
      # complete referenced option:
      #   [section]
      #   option = ${another_section:|
      valid_option_references: Iterable[Tuple[str, str]] = []

      # We include the options of `another_section`
      if symbol.referenced_section:
        valid_option_references = [
            (k, f'```\n{getOptionValue(v)}```')
            for k, v in symbol.referenced_section.items()
        ]
      # also if `another_section` uses a known recipe, includes
      # the generated options of this recipe.
      recipe = symbol.referenced_section_recipe
      if recipe:
        valid_option_references = itertools.chain(
            valid_option_references,
            ((k, v.documentation)
             for k, v in recipe.generated_options.items()),
        )
      for buildout_option_name, buildout_option_value in valid_option_references:
        items.append(
            CompletionItem(label=buildout_option_name,
                           text_edit=getOptionReferenceTextEdit(
                               doc,
                               params.position,
                               buildout_option_name + '}',
                           ),
                           kind=CompletionItemKind.Property,
                           documentation=MarkupContent(
                               kind=MarkupKind.Markdown,
                               value=buildout_option_value,
                           )))
    elif symbol.kind == buildout.SymbolKind.BuildoutOptionKey:
      # complete options of a section, ie:
      #   [section]
      #   opt|
      assert isinstance(parsed, buildout.BuildoutProfile)

      # complete with existing options from this sections, to override
      # options and for [buildout]
      for option_name, option_default_value in symbol.current_section.items():
        # skip some options that are not supposed to be defined, only referenced
        if option_name in (
            '_buildout_section_name_',
            '_profile_base_location_',
        ):
          continue
        items.append(
            CompletionItem(label=option_name,
                           text_edit=getDefaultTextEdit(
                               doc,
                               params.position,
                               option_name + ' = ',
                           ),
                           kind=CompletionItemKind.Variable,
                           documentation=MarkupContent(
                               kind=MarkupKind.Markdown,
                               value=f'`{option_default_value.value}`',
                           )))

      # if section is buildout, completes extends & parts which are usually
      # multi lines already with an extra \n
      if symbol.current_section_name == 'buildout':
        for option_name, option_documentation in (
            ('extends', 'Profiles extended by this buildout'),
            ('parts', 'Parts that will be installed'),
        ):
          items.append(
              CompletionItem(label=option_name,
                             text_edit=getDefaultTextEdit(
                                 doc,
                                 params.position,
                                 option_name + ' =\n    ',
                             ),
                             kind=CompletionItemKind.Variable,
                             documentation=MarkupContent(
                                 kind=MarkupKind.Markdown,
                                 value=option_documentation,
                             )))
      else:
        # if section uses a known recipe, complete with the options of this recipe.
        recipe = symbol.current_section_recipe
        if recipe:
          for k, v in recipe.options.items():
            items.append(
                CompletionItem(label=k,
                               text_edit=getDefaultTextEdit(
                                   doc,
                                   params.position,
                                   k + ' = ',
                               ),
                               kind=CompletionItemKind.Variable,
                               documentation=MarkupContent(
                                   kind=MarkupKind.Markdown,
                                   value=v.documentation,
                               )))
        else:
          # section has no recipe, complete `recipe` as an option name
          items.append(
              CompletionItem(label='recipe',
                             text_edit=getDefaultTextEdit(
                                 doc,
                                 params.position,
                                 'recipe = ',
                             ),
                             kind=CompletionItemKind.Variable))
    elif symbol.kind == buildout.SymbolKind.BuildoutOptionValue:
      # complete option = |
      assert isinstance(parsed, buildout.BuildoutProfile)

      if symbol.current_option_name == 'recipe':
        # complete recipe = | with known recipes
        for recipe_name, recipe in recipes.registry.items():
          items.append(
              CompletionItem(label=recipe_name,
                             text_edit=getDefaultTextEdit(
                                 doc, params.position, recipe_name),
                             kind=CompletionItemKind.Constructor,
                             documentation=MarkupContent(
                                 kind=MarkupKind.Markdown,
                                 value=recipe.documentation,
                             )))
      if symbol.current_option_name == '<':
        # complete <= | with parts
        for section_name in symbol._buildout:
          if section_name != 'buildout':
            items.append(
                CompletionItem(label=section_name,
                               text_edit=getDefaultTextEdit(
                                   doc, params.position, section_name),
                               kind=CompletionItemKind.Function))
      if symbol.current_section_recipe:
        # complete with recipe options if recipe is known
        for k, v in symbol.current_section_recipe.options.items():
          if k == symbol.current_option_name:
            for valid in v.valid_values:
              items.append(
                  CompletionItem(label=valid,
                                 text_edit=getDefaultTextEdit(
                                     doc, params.position, valid),
                                 kind=CompletionItemKind.Keyword))
      if symbol.current_section_name == 'buildout':
        # complete options of [buildout]
        if symbol.current_option_name == 'extends':
          # complete extends = | with local files
          doc_path = pathlib.Path(doc.path)
          root_path = pathlib.Path(ls.workspace.root_path)
          for profile in itertools.chain(root_path.glob('**/*.cfg'),
                                         root_path.glob('*.cfg')):
            profile_relative_path = os.path.relpath(profile, doc_path.parent)
            items.append(
                CompletionItem(
                    label=profile_relative_path,
                    text_edit=getDefaultTextEdit(
                        doc,
                        params.position,
                        profile_relative_path,
                    ),
                    kind=CompletionItemKind.File,
                    # make current directory show first
                    sort_text='{}{}'.format(
                        'Z' if profile_relative_path.startswith('.') else 'A',
                        profile_relative_path)))
        if symbol.current_option_name == 'parts':
          # complete parts = | with sections
          for section in parsed.keys():
            if section != 'buildout':
              items.append(
                  CompletionItem(label=section,
                                 text_edit=getDefaultTextEdit(
                                     doc,
                                     params.position,
                                     section + '\n',
                                 ),
                                 kind=CompletionItemKind.Function))

  return items


@server.feature(DEFINITION)
#@utils.singleton_task
async def lsp_definition(
    ls: LanguageServer,
    params: TextDocumentPositionParams,
) -> List[Location]:
  parsed = await buildout.open(ls, params.text_document.uri)
  if parsed is None:
    return []
  symbol = await parsed.getSymbolAtPosition(params.position)
  logger.debug('definition @%s -> %s', params.position, symbol)
  locations: List[Location] = []
  if symbol:
    if symbol.kind in (
        buildout.SymbolKind.SectionReference,
        buildout.SymbolKind.OptionReference,
    ):
      assert symbol.referenced_section_name
      if symbol.referenced_option:
        locations.extend(symbol.referenced_option.locations)
      else:
        l = symbol._buildout.section_header_locations.get(
            symbol.referenced_section_name)
        if l:
          locations.append(l)
    elif symbol.kind == buildout.SymbolKind.BuildoutOptionValue:
      assert isinstance(parsed, buildout.BuildoutProfile)
      if symbol.current_option_name == '<':
        l = parsed.section_header_locations.get(symbol.value)
        if l:
          locations.append(l)
      elif symbol.current_section_name == 'buildout' and symbol.current_option_name == 'extends':
        extend = symbol.value
        if not buildout._isurl(extend):
          uri = params.text_document.uri
          base = uri[:uri.rfind('/')] + '/'
          locations.append(
              Location(uri=urllib.parse.urljoin(base, extend),
                       range=Range(start=Position(line=0, character=0),
                                   end=Position(line=1, character=0))))
  return locations


@server.feature(REFERENCES)
#@utils.singleton_task
async def lsp_references(
    server: LanguageServer,
    params: TextDocumentPositionParams,
) -> List[Location]:
  references: List[Location] = []
  searched_document = await buildout.parse(server, params.text_document.uri)
  assert searched_document is not None
  searched_symbol = await searched_document.getSymbolAtPosition(params.position
                                                                )
  if searched_symbol is not None:
    searched_option = None
    if searched_symbol.kind in (
        buildout.SymbolKind.SectionDefinition,
        buildout.SymbolKind.BuildoutOptionKey,
    ):
      searched_section = searched_symbol.current_section_name
      if searched_symbol.kind == buildout.SymbolKind.BuildoutOptionKey:
        searched_option = searched_symbol.current_option_name
    else:
      searched_section = searched_symbol.referenced_section_name
      if searched_symbol.kind == buildout.SymbolKind.OptionReference:
        searched_option = searched_symbol.referenced_option_name
    logger.debug("Looking for references for %s ${%s:%s}", searched_symbol,
                 searched_section, searched_option)
    assert searched_section
    for profile_path in pathlib.Path(
        server.workspace.root_path).glob('**/*.cfg'):
      profile = await buildout.parse(server, profile_path.as_uri())
      if profile is not None:
        assert isinstance(profile, buildout.BuildoutProfile)

        # listing a section in ${buildout:parts} is a reference
        parts = profile['buildout'].get('parts')
        if parts is not None and searched_section in parts.value:
          for option_text, option_range in profile.getOptionValues(
              'buildout', 'parts'):
            if searched_section == option_text:
              references.append(Location(uri=profile.uri, range=option_range))

        async for symbol in profile.getAllOptionReferenceSymbols():
          if symbol.referenced_section_name == searched_section:
            if searched_option is None:
              references.append(
                  Location(uri=profile.uri, range=symbol.section_range))
            elif symbol.referenced_option_name == searched_option:
              references.append(
                  Location(uri=profile.uri, range=symbol.option_range))

        if searched_option is None:
          # find references in <= macros
          for options in profile.values():
            for option_key, option_value in options.items():
              if option_key == '<':
                if option_value.value == searched_section:
                  loc = option_value.locations[-1]
                  assert loc.uri == profile.uri
                  references.append(loc)
  return references


@server.feature(HOVER)
#@utils.singleton_task
async def lsp_hover(
    ls: LanguageServer,
    params: TextDocumentPositionParams,
) -> Optional[Hover]:
  parsed = await buildout.open(ls, params.text_document.uri)
  if parsed is None:
    return None
  symbol = await parsed.getSymbolAtPosition(params.position)
  hover_text = ''
  if symbol:
    if symbol.kind == buildout.SymbolKind.OptionReference:
      assert symbol.referenced_section_name
      if symbol.referenced_option:
        hover_text = symbol.referenced_option.value
    if symbol.kind == buildout.SymbolKind.SectionReference:
      assert symbol.referenced_section_name
      recipe = symbol.referenced_section_recipe
      if recipe:
        hover_text = recipe.name
  return Hover(contents=f'```\n{hover_text}\n```')


@server.feature(DOCUMENT_LINK)
#@utils.singleton_task
async def lsp_document_link(
    ls: LanguageServer,
    params: DocumentLinkParams,
) -> List[DocumentLink]:
  links: List[DocumentLink] = []
  uri = params.text_document.uri
  parsed_buildout = await buildout.parse(ls, uri)
  base = uri[:uri.rfind('/')] + '/'

  if 'extends' in parsed_buildout['buildout']:
    for extend, extend_range in parsed_buildout.getOptionValues(
        'buildout', 'extends'):
      target = extend
      if target:
        if not buildout._isurl(extend):
          target = urllib.parse.urljoin(base, extend)
        links.append(DocumentLink(range=extend_range, target=target))
  return links
