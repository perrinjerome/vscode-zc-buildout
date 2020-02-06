import contextlib
import io
import logging
import os
import re
import tempfile
import urllib.parse
import pathlib
from typing import Any, List, Set, Union, Tuple, Iterable, Optional, Sequence

from zc.buildout import configparser
from zc.buildout.buildout import Buildout
from zc.buildout.configparser import MissingSectionHeaderError, ParsingError

from pygls.features import (
    COMPLETION,
    DEFINITION,
    DOCUMENT_SYMBOL,
    DOCUMENT_LINK,
    HOVER,
    REFERENCES,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_SAVE,
    WORKSPACE_DID_CHANGE_WATCHED_FILES,
)
from pygls.server import LanguageServer
from pygls.types import (
    CompletionItem,
    CompletionItemKind,
    CompletionList,
    CompletionParams,
    Diagnostic,
    DiagnosticSeverity,
    DidChangeTextDocumentParams,
    DidChangeWatchedFiles,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    DocumentSymbol,
    DocumentSymbolParams,
    Hover,
    Location,
    MarkupContent,
    MarkupKind,
    MessageType,
    Position,
    Range,
    SymbolKind,
    TextDocumentPositionParams,
    DocumentLink,
    DocumentLinkParams,
    TextEdit,
    WorkspaceEdit,
)

from . import buildout
from . import recipes
from . import jinja
import itertools

server = LanguageServer()

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


async def parseAndSendDiagnostics(
    ls: LanguageServer,
    uri: str,
) -> None:
  diagnostics: List[Diagnostic] = []
  parsed = None

  looks_like_profile = buildout.BuildoutProfile.looksLikeBuildoutProfile(uri)

  if looks_like_profile:
    # parse errors
    try:
      parsed = await buildout.parse(
          ls=ls,
          uri=uri,
          allow_errors=False,
      )
    except ParsingError as e:
      if e.filename != uri:
        logger.debug("skipping error in external file %s", e.filename)
      elif isinstance(e, MissingSectionHeaderError):
        if looks_like_profile:
          diagnostics.append(
              Diagnostic(
                  message=e.message,
                  range=Range(
                      start=Position(e.lineno, 0),
                      end=Position(e.lineno + 1, 0),
                  ),
                  source='buildout',
              ))
      else:
        if looks_like_profile:
          for (lineno, _), msg in zip(e.errors, e.message.splitlines()[1:]):
            msg = msg.split(':', 1)[1].strip()
            diagnostics.append(
                Diagnostic(
                    message=f'ParseError: {msg}',
                    range=Range(
                        start=Position(lineno, 0),
                        end=Position(lineno + 1, 0),
                    ),
                    source='buildout',
                ))

  resolved_buildout = await buildout.open(
      ls=ls,
      uri=uri,
  )
  assert resolved_buildout is not None

  installed_parts: Set[str] = set([])
  if isinstance(resolved_buildout, buildout.BuildoutProfile):
    if 'parts' in resolved_buildout['buildout']:
      installed_parts = set((
          v[0] for v in resolved_buildout.getOptionValues('buildout', 'parts')))

  async for symbol in resolved_buildout.getAllOptionReferenceSymbols():
    if symbol.referenced_section is None:
      diagnostics.append(
          Diagnostic(
              message=f'Section `{symbol.referenced_section_name}` does not exist.',
              range=symbol.section_range,
              source='buildout',
          ))
    elif symbol.referenced_option is None:
      # if we have a recipe, either it's a known recipe where we know
      # all options that this recipe can generate, or it's an unknown
      # recipe and in this case we assume it's OK.
      if (symbol.referenced_section_recipe_name is not None and
          symbol.referenced_section_recipe is None) or (
              symbol.referenced_section_recipe is not None and
              symbol.referenced_option_name in
              symbol.referenced_section_recipe.generated_options):
        continue
      # if a section is a macro, it's OK to self reference ${:missing}
      if symbol.is_same_section_reference and symbol.current_section_name not in installed_parts:
        continue
      diagnostics.append(
          Diagnostic(
              message=f'Option `{symbol.referenced_option_name}` does not exist in `{symbol.referenced_section_name}`.',
              range=symbol.option_range,
              source='buildout',
              severity=DiagnosticSeverity.Warning,
          ))

  if isinstance(resolved_buildout, buildout.BuildoutProfile):
    for section_name, section in resolved_buildout.items():
      if section_name in installed_parts and resolved_buildout.section_header_locations[
          section_name].uri == uri:
        # check for required options
        recipe = section.getRecipe()
        if recipe:
          missing_required_options = recipe.required_options.difference(
              section.keys())
          if missing_required_options:
            missing_required_options_text = ', '.join(
                ['`{}`'.format(o) for o in missing_required_options])
            diagnostics.append(
                Diagnostic(
                    message=f'Missing required options for `{recipe.name}`: {missing_required_options_text}',
                    range=resolved_buildout
                    .section_header_locations[section_name].range,
                    source='buildout',
                    severity=DiagnosticSeverity.Error,
                ),)

    if 'parts' in resolved_buildout['buildout']:
      jinja_parser = jinja.JinjaParser()
      for part_name, part_range in resolved_buildout.getOptionValues(
          'buildout', 'parts'):
        if part_name:
          if part_name.startswith('${'):
            continue  # assume substitutions are OK
          jinja_parser.feed(part_name)
          if jinja_parser.is_in_jinja:
            continue  # ignore anything in jinja context

          if part_name not in resolved_buildout:
            diagnostics.append(
                Diagnostic(
                    message=f'Section `{part_name}` does not exist.',
                    range=part_range,
                    source='buildout',
                    severity=DiagnosticSeverity.Error,
                ),)
          elif 'recipe' not in resolved_buildout[part_name]:
            diagnostics.append(
                Diagnostic(
                    message=f'Section `{part_name}` has no recipe.',
                    range=part_range,
                    source='buildout',
                    severity=DiagnosticSeverity.Error,
                ),)

  ls.publish_diagnostics(
      uri,
      diagnostics,
  )


@server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(
    ls: LanguageServer,
    params: DidOpenTextDocumentParams,
) -> None:
  await parseAndSendDiagnostics(ls, params.textDocument.uri)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
async def did_change(
    ls: LanguageServer,
    params: DidChangeTextDocumentParams,
) -> None:
  buildout.clearCache(params.textDocument.uri)
  await parseAndSendDiagnostics(ls, params.textDocument.uri)


@server.feature(WORKSPACE_DID_CHANGE_WATCHED_FILES)
async def did_change_watched_file(
    ls: LanguageServer,
    params: DidChangeWatchedFiles,
) -> None:
  for change in params.changes:
    buildout.clearCache(change.uri)


@server.feature(DOCUMENT_SYMBOL)
async def lsp_symbols(
    ls: LanguageServer,
    params: DocumentSymbolParams,
) -> List[DocumentSymbol]:
  symbols: List[DocumentSymbol] = []

  parsed = await buildout.parse(
      ls=ls,
      uri=params.textDocument.uri,
      allow_errors=True,
  )

  for section_name, section_value in parsed.items():
    section_header_location = parsed.section_header_locations[section_name]
    # don't include implicit sections such as [buildout] unless defined in this profile.
    if section_header_location.uri != params.textDocument.uri:
      continue
    children: List[DocumentSymbol] = []
    for option_name, option_value in section_value.items():
      if option_value.implicit_option:
        continue
      option_range = Range(
          start=Position(
              min(r.range.start.line for r in option_value.locations)),
          end=Position(max(r.range.end.line for r in option_value.locations)))
      detail = getOptionValue(option_value)
      if len(detail.splitlines()) > 1:
        #  vscode does not like too long multi-lines detail
        detail = '{} ...'.format(detail.splitlines()[0])
      children.append(
          DocumentSymbol(
              name=option_name,
              kind=SymbolKind.Field,
              range=option_range,
              selection_range=option_range,
              detail=detail,
              children=[]))
    section_range = Range(
        start=section_header_location.range.start,
        end=Position(
            max(s.range.end.line for s in children
               ) if children else section_header_location.range.end.line),
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


@server.feature(COMPLETION, trigger_characters=["{", ":"])
async def lsp_completion(
    ls: LanguageServer,
    params: CompletionParams,
) -> Optional[List[CompletionItem]]:
  items: List[CompletionItem] = []
  doc = ls.workspace.get_document(params.textDocument.uri)

  def getInsertText(current_text: str, insert_text: str) -> str:
    """Calculate the text to be inserted.

    When we already have:

      plone.rec|

    and the completion is `plone.recipe.command`, if we return "plone.recipe.command",
    this will be appended to the current word, which is `plone`.
    In this case we want to insert only "recipe.command".

    Note that there is wordPattern in language-configuration.json that is supposed
    to address this, but it seems we cannot include . in word patterns.
    There's also the same problem with -
    """
    for char in ('.', '-'):
      common_leading, _, _ = current_text.rpartition(char)
      if common_leading:
        insert_text = insert_text[len(common_leading) + 1:]
    return insert_text

  parsed = await buildout.open(ls, params.textDocument.uri)
  if parsed is None:
    return None
  symbol = await parsed.getSymbolAtPosition(params.position)
  logger.debug("getting completions on %s", symbol)
  if symbol:
    if symbol.kind == buildout.SymbolKind.SectionReference:
      for buildout_section_name, section_items in symbol._buildout.items():
        documentation = '```ini\n{}\n```'.format(
            '\n'.join('{} = {}'.format(k, v.value)
                      for (k, v) in section_items.items()
                      if v and not v.implicit_option),)
        if section_items.get('recipe'):
          recipe = section_items.getRecipe()
          if recipe:
            documentation = f'{recipe.documentation}\n\n---\n{documentation}'
          else:
            documentation = f'## `{section_items["recipe"].value}`\n\n---\n{documentation}'

        items.append(
            CompletionItem(
                label=buildout_section_name,
                insert_text=getInsertText(
                    symbol.value,
                    buildout_section_name,
                ),
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
            ((k, v.documentation) for k, v in recipe.generated_options.items()),
        )
      for buildout_option_name, buildout_option_value in valid_option_references:
        items.append(
            CompletionItem(
                label=buildout_option_name,
                insert_text=getInsertText(symbol.value, buildout_option_name),
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

      # if section is buildout, completes with buildout known options.
      if symbol.current_section_name == 'buildout':
        # buildout default options
        for option_name, option_default_value in parsed['buildout'].items():
          items.append(
              CompletionItem(
                  label=option_name,
                  insert_text=f'{getInsertText(symbol.value, option_name)} = ',
                  kind=CompletionItemKind.Variable,
                  documentation=MarkupContent(
                      kind=MarkupKind.Markdown,
                      value=f'`{option_default_value.value}`',
                  )))
        # extra buildout options that are usually defined as multi line
        # (so we insert a \n)
        for option_name, option_documentation in (
            ('extends', 'Profiles extended by this buildout'),
            ('parts', 'Parts that will be installed'),
        ):
          items.append(
              CompletionItem(
                  label=option_name,
                  insert_text=f'{getInsertText(symbol.value, option_name)} =\n  ',
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
                CompletionItem(
                    label=k,
                    insert_text=f'{getInsertText(symbol.value, k)} = ',
                    kind=CompletionItemKind.Variable,
                    documentation=MarkupContent(
                        kind=MarkupKind.Markdown,
                        value=v.documentation,
                    )))
        else:
          # section has no recipe, complete `recipe` as an option name
          items.append(
              CompletionItem(
                  label='recipe',
                  insert_text=f'{getInsertText(symbol.value, "recipe")} = ',
                  kind=CompletionItemKind.Variable))
    elif symbol.kind == buildout.SymbolKind.BuildoutOptionValue:
      # complete option = |
      assert isinstance(parsed, buildout.BuildoutProfile)

      if symbol.current_option_name == 'recipe':
        # complete recipe = | with known recipes
        for recipe_name, recipe in recipes.registry.items():
          items.append(
              CompletionItem(
                  label=recipe_name,
                  insert_text=getInsertText(symbol.value, recipe_name),
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
                CompletionItem(
                    label=section_name,
                    insert_text=getInsertText(symbol.value, section_name),
                    kind=CompletionItemKind.Function))
      if symbol.current_section_recipe:
        # complete with recipe options if recipe is known
        for k, v in symbol.current_section_recipe.options.items():
          if k == symbol.current_option_name:
            for valid in v.valid_values:
              items.append(
                  CompletionItem(
                      label=valid,
                      insert_text=getInsertText(symbol.value, valid),
                      kind=CompletionItemKind.Keyword))
      if symbol.current_section_name == 'buildout':
        # complete options of [buildout]
        if symbol.current_option_name == 'extends':
          # complete extends = | with local files
          doc_path = pathlib.Path(doc.path)
          root_path = pathlib.Path(ls.workspace.root_path)
          for profile in itertools.chain(
              root_path.glob('**/*.cfg'), root_path.glob('*.cfg')):
            profile_relative_path = os.path.relpath(profile, doc_path.parent)
            items.append(
                CompletionItem(
                    label=profile_relative_path,
                    insert_text=getInsertText(
                        symbol.value,
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
                  CompletionItem(
                      label=section,
                      insert_text=f'{getInsertText(symbol.value, section)}\n',
                      kind=CompletionItemKind.Function))

  return items


@server.feature(DEFINITION)
async def lsp_definition(
    ls: LanguageServer,
    params: TextDocumentPositionParams,
) -> List[Location]:
  parsed = await buildout.open(ls, params.textDocument.uri)
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
          uri = params.textDocument.uri
          base = uri[:uri.rfind('/')] + '/'
          locations.append(
              Location(
                  uri=urllib.parse.urljoin(base, extend),
                  range=Range(start=Position(0, 0), end=Position(1, 0))))
  return locations


@server.feature(REFERENCES)
async def lsp_references(
    server: LanguageServer,
    params: TextDocumentPositionParams,
) -> List[Location]:
  references: List[Location] = []
  searched_document = await buildout.parse(server, params.textDocument.uri)
  assert searched_document is not None
  searched_symbol = await searched_document.getSymbolAtPosition(params.position)
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

    for profile_path in pathlib.Path(
        server.workspace.root_path).glob('**/*.cfg'):
      profile = await buildout.parse(server, profile_path.as_uri())
      if profile is not None:
        assert isinstance(profile, buildout.BuildoutProfile)
        async for symbol in profile.getAllOptionReferenceSymbols():
          if symbol.referenced_section_name == searched_section:
            if searched_option is None:
              references.append(Location(profile.uri, symbol.section_range))
            elif symbol.referenced_option_name == searched_option:
              references.append(Location(profile.uri, symbol.option_range))

        if searched_option is None:
          # find references in <= macros
          for section, options in profile.items():
            for option_key, option_value in options.items():
              if option_key == '<':
                if option_value.value == searched_section:
                  loc = option_value.locations[-1]
                  assert loc.uri == profile.uri
                  references.append(loc)
  return references


@server.feature(HOVER)
async def lsp_hover(
    ls: LanguageServer,
    params: TextDocumentPositionParams,
) -> Optional[Hover]:
  parsed = await buildout.open(ls, params.textDocument.uri)
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
async def lsp_document_link(
    ls: LanguageServer,
    params: DocumentLinkParams,
) -> List[DocumentLink]:
  links: List[DocumentLink] = []
  uri = params.textDocument.uri
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
