# This module contain modified code from zc.buildout http://www.buildout.org/en/latest/
# which has this copyright
##############################################################################
#
# Copyright (c) 2005-2009 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import collections
import copy
import io
import logging
import os
import re
import sys
import textwrap
import enum
import urllib.parse
import pathlib

from typing import TYPE_CHECKING, Dict, List, Iterator, Tuple, Optional, Set, TextIO, Union, Match, cast, AsyncIterator

from zc.buildout.buildout import _buildout_default_options
from zc.buildout.configparser import (
    Error,
    MissingSectionHeaderError,
    ParsingError,
    leading_blank_lines,
    option_start,
    section_header,
)
from . import recipes

from pygls.server import LanguageServer
from pygls.types import Position, Range, Location

logger = logging.getLogger(__name__)

# Matches a reference like ${section:option}
# We also tolerate ${section: without option or the ending } to generate completions.
option_reference_re = re.compile(
    r'\${(?P<section>[-a-zA-Z0-9 ._]*):(?P<option>[-a-zA-Z0-9 ._]*)')

# Matches of an unterminated ${section:
section_reference_re = re.compile(r'.*\$\{(?P<section>[-a-zA-Z0-9 ._]*)[^:]*$')

# Matches an option definition, ie option = value in:
#   [section]
#   option = value
option_definition_re = re.compile(
    r'^(?P<option>[^=]*)\s*=\s*(?P<option_value>.*)$')

# Filenames of slapos instances, that might be a buildout profile as a buildout template
slapos_instance_profile_filename_re = re.compile(
    r'.*\/instance[^\/]*\.cfg[^\/]*')

### type definitions ###
URI = str  # type alias


class ResolveError(Exception):
  """Error when resolving buildout
  """


class RecursiveIncludeError(ResolveError):
  """Loop in profile extensions.
  """


class RecursiveMacroError(ResolveError):
  """Loop in macros, like in ::

  ```
    [a]
    <=b
    [b]
    <=a
  ```
  """


class MissingExtendedSection(ResolveError):
  """Extending a non existing section::

  ```
    [a]
    <= not_exists
  ```
  
  """


class BuildoutOptionDefinition:
  def __init__(
      self,
      locations: List[Location],
      value: str,
      implicit_option: bool = False,
  ):
    self.locations = locations
    self.value = value
    self.implicit_option = implicit_option

  def __repr__(self):
    locations = ' '.join(
        ['{} {}'.format(l.uri, l.range) for l in self.locations])
    return '{} ({})'.format(self.value, locations)


class _BuildoutSection(Dict[str, BuildoutOptionDefinition]):
  """Section of a buildout.
  """
  def getRecipe(self) -> Optional[recipes.Recipe]:
    recipe_option = self.get('recipe')
    if recipe_option is not None:
      return recipes.registry.get(recipe_option.value)
    return None


# Inherit from OrderDict so that we can instanciate BuildoutSection.
# Only do this at runtime, so that during typecheck we have proper types on dict
# methods.
if TYPE_CHECKING:
  BuildoutSection = _BuildoutSection
else:

  class BuildoutSection(
      collections.OrderedDict,
      _BuildoutSection,
  ):
    pass


class SymbolKind(enum.Enum):
  """Types of symbols.

  One of:
    * ``SectionDefinition``: section in::

        [section]

    * ``BuildoutOptionKey``: option in::

        [section]
        option = value

    * ``BuildoutOptionValue``: value in::

        [section]
        option = value
    * ``SectionReference``: a specialised version of ``BuildoutOptionValue`` where
       the position is on ``section`` from ``${section:option}``.
    * ``OptionReference``: a specialised version of ``BuildoutOptionValue`` where
       the position is on ``option`` from ``${section:option}``.

  """
  SectionDefinition = 0
  BuildoutOptionKey = 1
  BuildoutOptionValue = 2
  SectionReference = 3
  OptionReference = 4


class Symbol:
  """A buildout symbol, can be of any SymbolKind
  """
  def __init__(
      self,
      buildout: 'BuildoutProfile',
      kind: SymbolKind,
      value: str,
      current_section_name: Optional[str] = None,
      current_option_name: Optional[str] = None,
      referenced_section_name: Optional[str] = None,
      referenced_option_name: Optional[str] = None,
  ):
    self._buildout = buildout
    self.kind = kind
    self.value = value
    self.current_section_name = current_section_name
    self.current_option_name = current_option_name
    self.referenced_section_name = referenced_section_name
    self.referenced_option_name = referenced_option_name

  def __repr__(self):
    referenced = ""
    if self.referenced_section_name:
      referenced = f"referenced=${{{self.referenced_section_name}:{self.referenced_option_name}}}"
    return (
        f"<Symbol kind={self.kind} "
        f"buildout={self._buildout.uri!r} "
        f"value={self.value!r} "
        f"current=${{{self.current_section_name}:{self.current_option_name}}} "
        f"{referenced}>")

  @property
  def current_section(self) -> BuildoutSection:
    assert self.current_section_name
    return self._buildout[self.current_section_name]

  @property
  def current_option(self) -> Optional[BuildoutOptionDefinition]:
    if self.current_option_name:
      return self.current_section.get(self.current_option_name)
    return None

  @property
  def current_section_recipe(self) -> Optional[recipes.Recipe]:
    return self.current_section.getRecipe() if self.current_section else None

  @property
  def referenced_section(self) -> Optional[BuildoutSection]:
    if self.referenced_section_name:
      return self._buildout.get(self.referenced_section_name)
    return None

  @property
  def referenced_section_recipe_name(self) -> Optional[str]:
    if self.referenced_section:
      recipe = self.referenced_section.get('recipe')
      if recipe:
        return (recipe.value)
    return None

  @property
  def referenced_section_recipe(self) -> Optional[recipes.Recipe]:
    referenced_section_recipe_name = self.referenced_section_recipe_name
    if referenced_section_recipe_name:
      return recipes.registry.get(referenced_section_recipe_name)
    return None

  @property
  def referenced_option(self) -> Optional[BuildoutOptionDefinition]:
    referenced_section = self.referenced_section
    if referenced_section and self.referenced_option_name:
      return referenced_section.get(self.referenced_option_name)
    return None


class OptionReferenceSymbolWithPosition(Symbol):
  """An Symbol of kind OptionReference with ranges already calculated.
  """
  section_range: Range
  option_range: Range


class BuildoutTemplate:
  """A text document where ${}-style values can be substitued.
  This also supports $${}-style substitutions.
  """
  def __init__(
      self,
      uri: URI,
      source: str,
      buildout: 'BuildoutProfile',
      second_level_buildout: Optional['BuildoutProfile'] = None,
  ):
    self.uri = uri
    self.source = source
    # where the ${ substitution values are read
    self.buildout = buildout
    # where the $${ substitution values are read
    self.second_level_buildout = second_level_buildout

  def _getSymbolAtPosition(
      self,
      position: Position,
      current_section_name: Optional[str] = None,
      current_option_name: Optional[str] = None,
  ) -> Optional[Symbol]:

    lines = self.source.splitlines()
    # extract line for the position.
    line = ''
    if position.line < len(lines):
      line = lines[position.line]

    line_offset = 0
    remaining_line = line
    while remaining_line:
      remaining_line = line[line_offset:]

      option_reference_match = option_reference_re.match(remaining_line)
      section_reference_match = section_reference_re.match(remaining_line)
      if option_reference_match:
        logger.debug("got an option_reference_match %s", option_reference_match)
        referenced_buildout = self.buildout
        if (option_reference_match.start() + line_offset > 0 and
            line[option_reference_match.start() + line_offset - 1] == '$'):
          if self.second_level_buildout:
            referenced_buildout = self.second_level_buildout
          else:
            return None

        if (option_reference_match.start() <=
            (position.character - line_offset) <= option_reference_match.end()):
          # the position is in ${section:option}, find out wether it is in section or option
          position_on_option = (
              line_offset + option_reference_match.start() + len('${') +
              len(option_reference_match.group('section'))) < position.character
          referenced_section_name = option_reference_match.group('section')
          referenced_option_name = option_reference_match.group('option')

          return Symbol(
              kind=SymbolKind.OptionReference
              if position_on_option else SymbolKind.SectionReference,
              buildout=referenced_buildout,
              value=referenced_option_name
              if position_on_option else referenced_section_name,
              current_section_name=current_section_name,
              current_option_name=current_option_name,
              referenced_section_name=referenced_section_name or
              current_section_name,
              referenced_option_name=referenced_option_name,
          )
        else:
          logger.debug("option_reference_match was not in range, advancing")
          line_offset += option_reference_match.start()

      if section_reference_match:
        logger.debug("got a section_reference_match %s",
                     section_reference_match)
        referenced_buildout = self.buildout

        if section_reference_match.span('section')[0] > 3 and remaining_line[
            section_reference_match.span('section')[0] - 3] == '$':
          if self.second_level_buildout:
            referenced_buildout = self.second_level_buildout
          else:
            return None
        if (section_reference_match.start() <=
            (position.character - line_offset) <=
            section_reference_match.end()):
          referenced_section_name = section_reference_match.group('section')
          return Symbol(
              kind=SymbolKind.SectionReference,
              buildout=referenced_buildout,
              value=referenced_section_name,
              current_section_name=current_section_name,
              current_option_name=current_option_name,
              referenced_section_name=referenced_section_name or
              current_section_name,
          )
        else:
          logger.debug("section_reference_match was not in range, advancing")
          line_offset += section_reference_match.start()

      line_offset += 1

    return None

  async def getSymbolAtPosition(self, position: Position) -> Optional[Symbol]:
    """Return the symbol at given position.
    """
    return self._getSymbolAtPosition(position)

  async def getAllOptionReferenceSymbols(
      self) -> AsyncIterator[OptionReferenceSymbolWithPosition]:
    """Return all symbols of kind OptionReference in this profile.
    """
    for lineno, line in enumerate(self.source.splitlines()):
      if line and line[0] in '#;':
        continue
      for match in option_reference_re.finditer(line):

        referenced_buildout = self.buildout
        if match.start() > 0 and line[match.start() - 1] == '$':
          if self.second_level_buildout:
            referenced_buildout = self.second_level_buildout
          else:
            continue
        symbol = OptionReferenceSymbolWithPosition(
            buildout=referenced_buildout,
            kind=SymbolKind.OptionReference,
            value=match.string[slice(*match.span())],
            referenced_section_name=match.group('section'),
            referenced_option_name=match.group('option'),
        )
        symbol.section_range = Range(
            Position(
                lineno,
                match.start() + 2,  # the ${ was captured
            ),
            Position(
                lineno,
                match.end() - len(match.group('option')) - 1,
            ),
        )
        symbol.option_range = Range(
            Position(
                lineno,
                match.end() - len(match.group('option')),
            ),
            Position(
                lineno,
                match.end(),
            ),
        )
        yield symbol


class BuildoutProfile(Dict[str, BuildoutSection], BuildoutTemplate):
  """A parsed buildout file, without extends.
  """
  def __init__(self, uri: URI, source: str):
    BuildoutTemplate.__init__(
        self,
        uri=uri,
        source=source,
        buildout=self,
    )
    self.section_header_locations: Dict[str,
                                        Location] = collections.OrderedDict()
    """The locations for each section, keyed by section names.
    """

  async def getTemplate(
      self,
      ls: LanguageServer,
      uri: URI,
  ) -> Optional[BuildoutTemplate]:
    """Returns the template from this uri, if it is a template for this profile.

    One exception is for profiles names software.cfg or buildout.cfg - we just assume
    that the template is valid for these profiles. For other profiles, we check if
    the profile really uses this template.
    XXX this might not be good, but we don't resolve subsitutions inside buildout now.
    """

    # uri can be passed as relative or absolute. Let's build a set of absolute
    # and relative uris.
    uris = set((uri,))

    if not _isurl(uri):
      base = self.uri[:self.uri.rfind('/')] + '/'
      uri = urllib.parse.urljoin(base, uri)
      uris.add(uri)
    else:
      assert uri.startswith('file://')
      assert self.uri.startswith('file://')
      uri_path = pathlib.Path(uri[len('file://'):])
      uris.add(
          str(
              uri_path.relative_to(
                  pathlib.Path(self.uri[len('file://'):]).parent)))

    document = ls.workspace.get_document(uri)
    if not os.path.exists(document.path):
      return None

    for section_value in self.values():
      recipe = section_value.getRecipe()
      if recipe is not None:

        for template_option_name in recipe.template_options:
          template_option_value = section_value.get(template_option_name)
          if (template_option_value is not None and
              template_option_value.value in uris or
              self.uri.endswith('/buildout.cfg') or
              self.uri.endswith('/software.cfg')):

            if slapos_instance_profile_filename_re.match(uri):
              # a slapos "buildout profile as a template"
              slapos_instance_profile = await open(
                  ls,
                  uri,
                  allow_errors=True,
                  open_as_buildout_profile=True,
              )
              assert isinstance(slapos_instance_profile, BuildoutProfile)
              slapos_instance_profile.second_level_buildout = slapos_instance_profile
              slapos_instance_profile.buildout = self

              # Add slapos instance generated sections.
              slapos_instance_profile.section_header_locations.setdefault(
                  'slap-connection',
                  Location(uri='', range=Range(Position(), Position())))
              slapos_instance_profile.setdefault(
                  'slap-connection',
                  BuildoutSection(
                      **{
                          'computer-id':
                              BuildoutOptionDefinition(
                                  locations=[],
                                  value='',
                                  implicit_option=True,
                              ),
                          'partition-id':
                              BuildoutOptionDefinition(
                                  locations=[],
                                  value='',
                                  implicit_option=True,
                              ),
                          'server-url':
                              BuildoutOptionDefinition(
                                  locations=[],
                                  value='',
                                  implicit_option=True,
                              ),
                          'software-release-url':
                              BuildoutOptionDefinition(
                                  locations=[],
                                  value='',
                                  implicit_option=True,
                              ),
                      }))
              slapos_instance_profile.section_header_locations.setdefault(
                  'slap-network-information',
                  Location(uri='', range=Range(Position(), Position())))
              slapos_instance_profile.setdefault(
                  'slap-network-information',
                  BuildoutSection(
                      **{
                          'local-ipv4':
                              BuildoutOptionDefinition(
                                  locations=[],
                                  value='',
                                  implicit_option=True,
                              ),
                          'global-ipv6':
                              BuildoutOptionDefinition(
                                  locations=[],
                                  value='',
                                  implicit_option=True,
                              ),
                          'network-interface':
                              BuildoutOptionDefinition(
                                  locations=[],
                                  value='',
                                  implicit_option=True,
                              ),
                          'tap-ipv4':
                              BuildoutOptionDefinition(
                                  locations=[],
                                  value='',
                                  implicit_option=True,
                              ),
                          'tap-gateway':
                              BuildoutOptionDefinition(
                                  locations=[],
                                  value='',
                                  implicit_option=True,
                              ),
                          'tap-netmask':
                              BuildoutOptionDefinition(
                                  locations=[],
                                  value='',
                                  implicit_option=True,
                              ),
                          'tap-network':
                              BuildoutOptionDefinition(
                                  locations=[],
                                  value='',
                                  implicit_option=True,
                              ),
                          'global-ipv4-network':
                              BuildoutOptionDefinition(
                                  locations=[],
                                  value='',
                                  implicit_option=True,
                              ),
                      }))
              return slapos_instance_profile
            return BuildoutTemplate(
                uri=uri,
                source=document.source,
                buildout=self,
            )
    return None

  async def getSymbolAtPosition(self, position: Position) -> Optional[Symbol]:
    """Return the symbol at given position.
    """

    lines = self.source.splitlines()
    # parse until this line to find out what is the current section.
    buildout_for_current_section = await _parse(
        uri=self.uri,
        fp=io.StringIO('\n'.join(lines[:position.line + 1])),
        allow_errors=True,
    )
    current_section_name, current_section_value = \
            buildout_for_current_section.popitem()
    # find current option in current_section
    current_option_name = None
    for k, v in current_section_value.items():
      for l in v.locations:
        if (l.range.start.line <= position.line <= l.range.end.line):
          current_option_name = k
          break
    logger.debug("current_section_name: %s current_option_name: %s",
                 current_section_name, current_option_name)

    symbol = self._getSymbolAtPosition(
        position,
        current_section_name=current_section_name,
        current_option_name=current_option_name,
    )
    if symbol is not None:
      return symbol

    # extract line for the position.
    line = ''
    if position.line < len(lines):
      line = lines[position.line]

    line_offset = 0
    remaining_line = line
    while remaining_line:
      remaining_line = line[line_offset:]

      logger.debug("trying line from %s >%s<", line_offset, remaining_line)
      option_value_definition_match = option_definition_re.search(
          remaining_line)

      if line_offset == 0:
        # we can be in the following cases (> denotes beginning of lines)
        # - a section header
        #   [section]
        # - a single line option and value:
        #   >option = value
        # - an option without value:
        #   >option
        #   an empty option is also valid case, but we handled it outside of
        #   the `if remaining_line`
        # - a value only, like in a multi line option. In this case we should
        #   have a leading space.
        #   >  value
        section_header_match = section_header(line)  # reuse buildout's regexp
        if section_header_match:
          return Symbol(
              kind=SymbolKind.SectionDefinition,
              buildout=self,
              value=section_header_match.group('name'),
              current_section_name=section_header_match.group('name'),
          )
        if option_value_definition_match:
          # Single line option and value. The position might be on option
          # or value
          logger.debug("got a option_definition_match %s",
                       option_value_definition_match)

          if (option_value_definition_match.start() <=
              (position.character - line_offset) <=
              option_value_definition_match.end()):

            option = option_value_definition_match.group('option')
            option_value = option_value_definition_match.group('option_value')
            # is the position on option or option value ?
            position_on_option = position.character < (
                line_offset + option_value_definition_match.start() +
                len(option_value_definition_match.group('option')))

            logger.debug("option_value_definition_match, position on option %s",
                         position_on_option)
            return Symbol(
                kind=SymbolKind.BuildoutOptionKey
                if position_on_option else SymbolKind.BuildoutOptionValue,
                buildout=self,
                value=option.strip()
                if position_on_option else option_value.strip(),
                current_section_name=current_section_name,
                current_option_name=current_option_name,
            )
        elif not (line.startswith(' ') or line.startswith('\t')):
          # Option without value
          if not line.startswith('['):
            return Symbol(
                kind=SymbolKind.BuildoutOptionKey,
                buildout=self,
                value=line.strip(),
                current_section_name=current_section_name,
                current_option_name=line.strip(),
            )
        else:
          # Value only, like in a multi line option.
          return Symbol(
              kind=SymbolKind.BuildoutOptionValue,
              buildout=self,
              value=line.strip(),
              current_section_name=current_section_name,
              current_option_name=current_option_name,
          )
      line_offset += 1

    if line_offset == 0:
      # an empty line is also an option without value
      return Symbol(
          kind=SymbolKind.BuildoutOptionKey,
          buildout=self,
          value=line.strip(),
          current_section_name=current_section_name,
          current_option_name=line.strip(),
      )
    return None

  async def getAllOptionReferenceSymbols(
      self) -> AsyncIterator[OptionReferenceSymbolWithPosition]:
    """Return all symbols of kind OptionReference in this profile.
    
    In a buildout profile, we also resolve the current section name
    in ${:option}.
    """
    async for symbol in super().getAllOptionReferenceSymbols():
      if not symbol.referenced_section_name:
        sap = await symbol._buildout.getSymbolAtPosition(
            symbol.section_range.start)
        assert sap is not None
        symbol.referenced_section_name = sap.current_section_name
      yield symbol


class ResolvedBuildout(BuildoutProfile):
  """A buildout where extends and section macros <= have been extended.
  """


### cache ###

# a cache of un-resolved buildouts by uri
_parse_cache: Dict[URI, BuildoutProfile] = {}
# a cache of resolved buildouts by uri
_resolved_buildout_cache: Dict[URI, ResolvedBuildout] = {}
# a mapping of dependencies between extends, so that we can clear caches when
# a profile is modified.
_extends_dependency_graph: Dict[URI, Set[URI]] = collections.defaultdict(set)


def clearCache(uri: URI):
  """Clear all caches for uri.

  This is to be called when the document is modified.
  """
  logger.debug("Clearing cache for %s", uri)
  _parse_cache.pop(uri, None)
  _clearExtendCache(uri, set())


def _clearExtendCache(uri: URI, done: Set[URI]):
  """Clear the `extends` cache for URI.

  This is to be called for all URIs extended by `uri`.
  """
  if uri in done:
    return
  done.add(uri)
  _resolved_buildout_cache.pop(uri, None)
  logger.debug(
      "Clearing extends cache for %s Dependencies: %s",
      uri,
      _extends_dependency_graph[uri],
  )
  for dependend_uri in _extends_dependency_graph[uri]:
    _resolved_buildout_cache.pop(dependend_uri, None)
    _clearExtendCache(dependend_uri, done)
  _extends_dependency_graph[uri].clear()


### buildout copied & modified functions ###

_isurl = re.compile('([a-zA-Z0-9+.-]+)://').match


async def parse(
    ls: LanguageServer,
    uri: URI,
    allow_errors=True,
) -> BuildoutProfile:
  """
  Parse a sectioned setup file and return a non-resolved buildout.

  This is a wrapper over _parse which uses language server's workspace to access documents.
  Returned value changed to a BuildoutProfile instance.

  """
  if uri in _parse_cache:
    return copy.deepcopy(_parse_cache[uri])

  document = ls.workspace.get_document(uri)
  try:
    fp = io.StringIO(document.source)
  except IOError:
    if not allow_errors:
      raise
    fp = io.StringIO('')
  parsed = await _parse(
      fp,
      uri,
      allow_errors,
  )
  _parse_cache[uri] = copy.deepcopy(parsed)
  return parsed


async def _parse(
    fp: TextIO,
    uri: URI,
    allow_errors,
) -> BuildoutProfile:
  """Parse a sectioned setup file and return a non-resolved buildout.

  This is equivalent to buildout's zc.buildout.configparser.parse with the
  following differences:

  This is patched here in order to:
      - allow to parse with errors
      - keep track of options overloaded in same file
      - record the line numbers
      - don't execute section conditions.
      - return ordered dicts in the same order as the input text.
      - optionally resolve extends directly here
      - ignore jinja contexts
    
  The returned value changed to a BuildoutProfile instance.

  """
  sections = BuildoutProfile(uri, fp.read())
  fp.seek(0)

  # buildout default values
  sections['buildout'] = BuildoutSection()
  for k, v in _buildout_default_options.items():
    sections['buildout'][k] = BuildoutOptionDefinition(
        value=v.value,
        locations=[Location(uri=uri, range=Range(Position(0), Position(0)))],
        implicit_option=True,
    )
  sections['buildout']['directory'] = BuildoutOptionDefinition(
      value='.',
      locations=[Location(uri=uri, range=Range(Position(0), Position(0)))],
      implicit_option=True,
  )

  sections.section_header_locations['buildout'] = Location(
      uri="",
      range=Range(Position(), Position()),
  )

  in_jinja_context = False
  cursect: Optional[Dict[str, BuildoutOptionDefinition]] = None
  blockmode = False
  optname: Optional[str] = None
  lineno = -1
  e: Optional[ParsingError] = None
  while True:
    line = fp.readline()
    if not line:
      break  # EOF

    lineno = lineno + 1

    if line[0] in '#;':
      continue  # comment

    if line.startswith('{') or in_jinja_context:
      in_jinja_context = '}' in line
    if in_jinja_context:
      continue

    if line[0].isspace() and (cursect is not None) and optname:
      _line = line
      # continuation line
      if blockmode:
        line = line.rstrip()
      else:
        line = line.strip()
        if not line:
          continue
      assert cursect is not None
      assert optname is not None
      option_def = cursect[optname]
      option_def.locations[-1].range.end.line = lineno
      option_def.locations[-1].range.end.character = len(_line) - 1
      option_def.value = ("%s\n%s" % (option_def.value, line))
      cursect[optname] = option_def

    else:
      header = section_header(line)
      if header:
        sectname = header.group('name')
        sections.section_header_locations[sectname] = Location(
            uri=uri, range=Range(
                Position(lineno, 0),
                Position(lineno + 1, 0),
            ))
        if sectname in sections:
          cursect = sections[sectname]
        else:
          sections[sectname] = cursect = BuildoutSection()
          # initialize buildout default options
          cursect['_buildout_section_name_'] = BuildoutOptionDefinition(
              locations=[
                  Location(
                      uri=uri, range=Range(Position(0, 0), Position(0, 0)))
              ],
              value=sectname,
              implicit_option=True,
          )
          # this is a slapos.buildout extension
          cursect['_profile_base_location_'] = BuildoutOptionDefinition(
              locations=[
                  Location(
                      uri=uri, range=Range(Position(0, 0), Position(0, 0)))
              ],
              value=uri,
              implicit_option=True,
          )

        # So sections can't start with a continuation line
        optname = None
      elif cursect is None:
        if not line.strip():
          continue
        # no section header in the file?
        if allow_errors:
          continue
        raise MissingSectionHeaderError(uri, lineno, line)
      else:
        if line[:2] == '=>':
          line = '<part-dependencies> = ' + line[2:]
        mo = option_start(line)
        if mo:
          # option start line
          optname, optval = mo.group('name', 'value')
          assert optname
          optname = optname.rstrip()
          optval = optval.strip()
          option_def = cursect.get(
              optname, BuildoutOptionDefinition(value=optval, locations=[]))
          option_def.value = optval

          option_def.locations.append(
              Location(
                  uri=uri,
                  range=Range(
                      start=Position(
                          line=lineno, character=len(mo.groups()[0]) + 1),
                      end=Position(line=lineno, character=len(line) - 1),
                  )))
          option_def.implicit_option = False
          cursect[optname] = option_def
          blockmode = not optval
        elif not (optname or line.strip()):
          # blank line after section start
          continue
        else:
          # a non-fatal parsing error occurred.  set up the
          # exception but keep going. the exception will be
          # raised at the end of the file and will contain a
          # list of all bogus lines
          if not e:
            e = ParsingError(uri)
          e.append(lineno, repr(line))

  # if any parsing errors occurred, raise an exception
  if e and not allow_errors:
    raise e

  # normalize spaces
  for section in sections.values():
    for name in section:
      value = section[name].value
      if value[:1].isspace():
        section[name].value = leading_blank_lines.sub(
            '', textwrap.dedent(value.rstrip()))

  return sections


async def open(
    ls: LanguageServer,
    uri: URI,
    allow_errors: bool = True,
    open_as_buildout_profile: bool = False,
) -> Optional[Union[BuildoutTemplate, ResolvedBuildout]]:
  """Open an URI and returnes either a buildout or a profile connected to buildout.

  In the case of slapos buildout templates (instance.cfg.in), it is both.

  For buildout, it is a wrapper over _open which uses language server's workspace
  """
  document = ls.workspace.get_document(uri)
  logger.debug("open %s", uri)
  if not open_as_buildout_profile:
    # First, try to read as a template, because buildout profiles can be templates.
    if slapos_instance_profile_filename_re.match(
        uri) or not uri.endswith('.cfg'):
      logger.debug('Trying to open %s as a template', uri)
      for buildout_path in sorted(
          pathlib.Path(document.path).parent.glob('*.cfg'),
          # we try buildout.cfg and software.cfg at last, because getTemplate
          # returns a valid template for any file.
          key=lambda path: path.name in ('buildout.cfg', 'software.cfg')):

        # We don't use  buildout_path.resolve().as_uri(), because we have fake uri -> path mapping in tests
        buildout_uri = str(buildout_path.resolve()).replace(
            ls.workspace.root_path,
            ls.workspace.root_uri,
            1,
        )
        logger.debug("Trying to find templates's buildout with %s -> %s",
                     buildout_path, buildout_uri)
        buildout = await _open(
            ls,
            '',
            buildout_uri,
            [],
            allow_errors=allow_errors,
        )

        assert isinstance(buildout, BuildoutProfile)
        template = await buildout.getTemplate(ls, uri)
        if template is not None:
          return template

  if uri.endswith('.cfg') or open_as_buildout_profile:
    fp = io.StringIO(document.source)
    return await _open(ls, '', uri, [], allow_errors=allow_errors)

  return None


async def _open(
    ls: LanguageServer,
    base: str,
    uri: URI,
    seen: List[str],
    allow_errors: bool,
) -> ResolvedBuildout:
  """Open a configuration file and return the result as a dictionary,

  Recursively open other files based on buildout options found.

  This is equivalent of zc.buildout.buildout._open
  """
  logger.debug("_open %r %r", base, uri)

  if not _isurl(uri):
    assert base
    uri = urllib.parse.urljoin(base, uri)
  if uri in _resolved_buildout_cache:
    logger.debug("_open %r was in cache", uri)
    return copy.deepcopy(_resolved_buildout_cache[uri])
  base = uri[:uri.rfind('/')] + '/'

  if uri in seen:
    if allow_errors:
      return ResolvedBuildout(uri, '')
    raise RecursiveIncludeError("Recursive file include", seen, uri)

  root_config_file = not seen
  seen.append(uri)

  non_extended = result = await parse(ls, uri, allow_errors=allow_errors)

  extends_option = result['buildout'].pop(
      'extends', None) if 'buildout' in result else None

  if extends_option:
    extends = extends_option.value.split()
    if extends:
      # extends, as absolute URI that we can use as cache key
      absolute_extends = tuple(urllib.parse.urljoin(base, x) for x in extends)
      eresult = await _open(ls, base, extends.pop(0), seen, allow_errors)
      for fname in extends:
        _update(eresult, await _open(ls, base, fname, seen, allow_errors))
      for absolute_extend in absolute_extends:
        _extends_dependency_graph[absolute_extend].add(uri)

      result = _update(eresult, result)

  seen.pop()

  for section_name, options in result.items():
    if '<' in options:
      try:
        result[section_name] = _do_extend_raw(
            section_name,
            options,
            result,
            [],
        )
      except ResolveError:
        # this happens with non top-level buildout
        pass

  resolved = cast(ResolvedBuildout, result)
  _resolved_buildout_cache[uri] = resolved
  return copy.deepcopy(resolved)


def _update_section(
    s1: BuildoutSection,
    s2: BuildoutSection,
) -> BuildoutSection:
  """Update s1 with values from s2.
  """
  s2 = copy.deepcopy(s2)
  for k, v in s2.items():
    if k.endswith('-'):
      k = k.rstrip(' -')
      # Find v1 in s2 first; it may have been set by a += operation first
      option_def = s2.get(k, s1.get(k, v))
      # same logic as as SectionKey.removeFromValue
      option_def.value = '\n'.join(
          new_v for new_v in option_def.value.split('\n')
          if new_v not in v.value.split('\n'))
      option_def.locations.extend(v.locations)
      s1[k] = option_def
    elif k.endswith('+'):
      k = k.rstrip(' +')
      # Find v1 in s2 first; it may have been defined locally too.
      option_def = s2.get(k, s1.get(k, v))
      # same logic as as SectionKey.addToValue
      option_def.value = '\n'.join(
          option_def.value.split('\n') + v.value.split('\n'))
      option_def.locations.extend(v.locations)
      s1[k] = option_def
    else:
      s1[k] = v
  return s1


def _update(d1: BuildoutProfile, d2: BuildoutProfile) -> BuildoutProfile:
  """update d1 with values from d2
  """
  d1.uri = d2.uri
  d1.source = d2.source
  for section in d2:
    d1.section_header_locations[section] = d2.section_header_locations[section]
    if section in d1:
      d1[section] = _update_section(d1[section], d2[section])
    else:
      d1[section] = d2[section]
  return d1


def _do_extend_raw(
    name: str,
    section: BuildoutSection,
    buildout: BuildoutProfile,
    doing: List[str],
) -> BuildoutSection:
  """Extends macros:

      [macro]
      [user]
      <= macro

  this is zc.buildout.buildout.Option._do_extend_raw    
  """
  if name == 'buildout':
    return section
  if name in doing:
    raise RecursiveMacroError("Infinite extending loop %r" % name)
  doing.append(name)

  try:
    to_do = section.get('<', None)
    if to_do is None:
      return section
    __doing__ = 'Loading input sections for %r', name

    result = BuildoutSection()
    for iname in to_do.value.split('\n'):
      iname = iname.strip()
      if not iname:
        continue
      raw = buildout.get(iname)
      if raw is None:
        raise MissingExtendedSection("No section named %r" % iname)
      result.update(_do_extend_raw(iname, raw, buildout, doing))

    _update_section(result, copy.deepcopy(section))
    result.pop('<', None)
    return result
  finally:
    assert doing.pop() == name
