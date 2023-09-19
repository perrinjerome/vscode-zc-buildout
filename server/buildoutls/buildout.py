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
import enum
import io
import logging
import os
import pathlib
import re
import textwrap
import urllib.parse
from typing import (
    TYPE_CHECKING,
    AsyncIterator,
    Dict,
    Iterator,
    List,
    Match,
    Optional,
    Set,
    TextIO,
    Tuple,
    Union,
    cast,
)

import aiohttp.client_exceptions
from lsprotocol.types import Location, Position, Range
from pygls.server import LanguageServer
from pygls.workspace import Document
from typing_extensions import TypeAlias
from zc.buildout.buildout import _buildout_default_options
from zc.buildout.configparser import (
    MissingSectionHeaderError,
    ParsingError,
    leading_blank_lines,
    option_start,
    section_header,
)

from . import aiohttp_session, jinja, recipes

logger = logging.getLogger(__name__)

# Matches a reference like ${section:option}
# We also tolerate ${section: without option or the ending } to generate completions.
option_reference_re = re.compile(
    r'\${(?P<section>[-a-zA-Z0-9 ._]*):(?P<option>[-a-zA-Z0-9 ._]*)')
# In this version, we don't tolerate the missing }
option_reference_strict_re = re.compile(
    r'\${(?P<section>[-a-zA-Z0-9 ._]*):(?P<option>[-a-zA-Z0-9 ._]*)}')

# Matches of an unterminated ${section:
section_reference_re = re.compile(r'.*\$\{(?P<section>[-a-zA-Z0-9 ._]*)[^:]*$')

# Matches an option definition, ie option = value in:
#   [section]
#   option = value
option_definition_re = re.compile(
    r'^(?P<option>[^=]*)\s*=\s*(?P<option_value>.*)$')

# Matches a comment
comment_re = re.compile(r'.*[#;].*')

# Filenames of slapos instances, that might be a buildout profile as a buildout template
slapos_instance_profile_filename_re = re.compile(
    r'.*\/instance[^\/]*\.cfg[^\/]*')

### type definitions ###
URI: TypeAlias = str


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
  """Option definition

  Keep track of the current value as `value` and of the
  `locations` where this value was defined. `values` is
  a list of intermediate values for each of the locations.

  `default_value` are default values that are not defined
  in profiles, but are implicit, such as buildout default
  values or sections added by slapos instance.
  """
  def __init__(
      self,
      value: str,
      location: Location,
      default_value: bool = False,
  ):
    self.locations: Tuple[Location, ...] = (location, )
    self.values: Tuple[str, ...] = (value, )
    self.default_values: Tuple[bool, ...] = (default_value, )

  @property
  def value(self) -> str:
    return self.values[-1]

  @property
  def location(self) -> Location:
    return self.locations[-1]

  @property
  def default_value(self) -> bool:
    return self.default_values[-1]

  def __repr__(self) -> str:
    locations = ' '.join(
        ['{} {}'.format(l.uri, l.range) for l in self.locations])
    return '{} ({})'.format(self.value, locations)

  def overrideValue(self, value: str, location: Location) -> None:
    """Add a value to the list of values."""
    self.values = self.values + (value, )
    self.locations = self.locations + (location, )
    self.default_values = self.default_values + (False, )

  def updateValue(
      self,
      value: str,
      location: Optional[Location] = None,
  ) -> None:
    """Replace the current value, used internally to clean up extra whitespaces."""
    self.values = self.values[:-1] + (value, )
    self.default_values = self.default_values[:-1] + (False, )
    if location is not None:
      self.locations = self.locations[:-1] + (location, )

  def copy(self) -> 'BuildoutOptionDefinition':
    copied = BuildoutOptionDefinition(self.value, self.locations[0])
    copied.locations = self.locations
    copied.values = self.values
    copied.default_values = self.default_values
    return copied


class _BuildoutSection(Dict[str, BuildoutOptionDefinition]):
  """Section of a buildout.
  """
  def getRecipe(self) -> Optional[recipes.Recipe]:
    recipe_option = self.get('recipe')
    if recipe_option is not None:
      return recipes.registry.get(recipe_option.value)
    return None

  if TYPE_CHECKING:

    def copy(self) -> '_BuildoutSection':
      ...


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
    * ``Comment``: when inside a comment

  """
  SectionDefinition = 0
  BuildoutOptionKey = 1
  BuildoutOptionValue = 2
  SectionReference = 3
  OptionReference = 4
  Comment = 5


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
      is_same_section_reference: bool = False,
  ):
    self._buildout = buildout
    self.kind = kind
    self.value = value
    self.current_section_name = current_section_name
    self.current_option_name = current_option_name
    self.referenced_section_name = referenced_section_name
    self.referenced_option_name = referenced_option_name
    self.is_same_section_reference = is_same_section_reference

  def __repr__(self) -> str:
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

  def copy(self) -> 'BuildoutTemplate':
    return self.__class__(
        self.uri,
        self.source,
        self.buildout,
        self.second_level_buildout,
    )

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

    if comment_re.match(line[:position.character]):
      return Symbol(kind=SymbolKind.Comment, buildout=self.buildout, value='')

    line_offset = 0
    remaining_line = line
    while remaining_line:
      remaining_line = line[line_offset:]

      option_reference_match = option_reference_re.match(remaining_line)
      section_reference_match = section_reference_re.match(remaining_line)
      if option_reference_match:
        logger.debug("got an option_reference_match %s",
                     option_reference_match)
        referenced_buildout = self.buildout
        if (option_reference_match.start() + line_offset > 0
            and line[option_reference_match.start() + line_offset - 1] == '$'):
          if self.second_level_buildout:
            referenced_buildout = self.second_level_buildout
          else:
            return None

        if (option_reference_match.start() <=
            (position.character - line_offset) <=
            option_reference_match.end()):
          # the position is in ${section:option}, find out wether it is in section or option
          position_on_option = (line_offset + option_reference_match.start() +
                                len('${') +
                                len(option_reference_match.group('section'))
                                ) < position.character
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
              referenced_section_name=referenced_section_name
              or current_section_name,
              is_same_section_reference=referenced_section_name == '',
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
        if (section_reference_match.start('section') <=
            (position.character - line_offset) <=
            section_reference_match.end('section')):
          referenced_section_name = section_reference_match.group('section')
          return Symbol(
              kind=SymbolKind.SectionReference,
              buildout=referenced_buildout,
              value=referenced_section_name,
              current_section_name=current_section_name,
              current_option_name=current_option_name,
              referenced_section_name=referenced_section_name
              or current_section_name,
              is_same_section_reference=referenced_section_name == '',
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
            is_same_section_reference=match.group('section') == '',
        )
        symbol.section_range = Range(
            start=Position(
                line=lineno,
                character=match.start() + 2,  # the ${ was captured
            ),
            end=Position(
                line=lineno,
                character=match.end() - len(match.group('option')) - 1,
            ),
        )
        symbol.option_range = Range(
            start=Position(
                line=lineno,
                character=match.end() - len(match.group('option')),
            ),
            end=Position(
                line=lineno,
                character=match.end(),
            ),
        )
        yield symbol


class BuildoutProfile(Dict[str, BuildoutSection], BuildoutTemplate):
  """A parsed buildout file, without extends.
  """
  def copy(self) -> 'BuildoutProfile':
    copied = self.__class__(self.uri, self.source)
    copied.section_header_locations = self.section_header_locations.copy()
    copied.has_dynamic_extends = self.has_dynamic_extends
    copied.has_jinja = self.has_jinja
    for k, v in self.items():
      copied[k] = v.copy()
    return copied

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
    self.has_dynamic_extends = False
    """Flag true if this resolved buildout had extends defined dynamically.
    This only happens with SlapOS instance buildout which are templates of profiles.
    """
    self.has_jinja = False
    """Flag true if this resolved buildout is a jinja template.
    This only happens with SlapOS instance buildout which are templates of profiles.
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
    """

    # uri can be passed as relative or absolute. Let's build a set of absolute
    # and relative uris.
    uris = set((uri, ))

    if not _isurl(uri):
      base = self.uri[:self.uri.rfind('/')] + '/'
      uri = urllib.parse.urljoin(base, uri)
      uris.add(uri)
    else:
      if not uri.startswith('file://'):
        # this might be a "virtual" scheme, for example gitlens:// is used in the git
        # history views
        return None
      assert self.uri.startswith('file://'), self.uri
      uri_path = pathlib.Path(uri[len('file://'):])
      uris.add(
          str(
              uri_path.relative_to(
                  pathlib.Path(self.uri[len('file://'):]).parent)))

    document = ls.workspace.get_document(uri)
    if not os.path.exists(document.path):
      return None

    for section_name, section_value in self.items():
      recipe = section_value.getRecipe()
      if recipe is not None:
        for template_option_name in recipe.template_options:
          template_option_value = section_value.get(template_option_name)
          if template_option_value is not None:
            template_option_value_uri = self.resolve_value(
                section_name, template_option_name)

            # Normalize URI path, in case it contain double slashes, ./ or ..
            template_option_value_parsed = urllib.parse.urlparse(
                template_option_value_uri)
            template_option_value_uri = urllib.parse.urlunparse(
                template_option_value_parsed._replace(
                    path=os.path.normpath(template_option_value_parsed.path)))

            if template_option_value_uri in uris:
              if slapos_instance_profile_filename_re.match(uri):
                # a slapos "buildout profile as a template"
                slapos_instance_profile = await open(
                    ls,
                    uri,
                    allow_errors=True,
                    force_open_as_buildout_profile=True,
                )
                assert isinstance(slapos_instance_profile, BuildoutProfile)
                slapos_instance_profile.second_level_buildout = slapos_instance_profile
                slapos_instance_profile.buildout = self
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
        #   >[section]
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

            logger.debug(
                "option_value_definition_match, position on option %s",
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

  def getOptionValues(
      self,
      section_name: str,
      option_name: str,
  ) -> Iterator[Tuple[str, Range]]:
    """Iterate on all values of an option

    When we have:

    ```
    [section]
    value =
      a
      b
      c
    ```

    the iterator yields `"a"`, `"b"`, `"c"` and the range of each value.

    ```
    [section]
    value = a b c
    ```
    """
    option: BuildoutOptionDefinition
    option = self[section_name][option_name]
    location = option.locations[-1]
    if location.uri == self.uri:
      start_line = location.range.start.line
      lines = self.source.splitlines()[start_line:location.range.end.line + 1]
      is_multi_line_option = len(lines) > 1
      for line_offset, option_value_text in enumerate(lines):
        if option_value_text and option_value_text[0] not in '#;':
          start_character = 0

          if option_value_text.startswith(option_name):
            option_name_text, option_value_text = option_value_text.split(
                '=', 1)
            start_character += len(option_name_text) + 1

          start_character += len(option_value_text) - len(
              option_value_text.lstrip())
          option_value_text = option_value_text.strip()
          if option_value_text:
            if is_multi_line_option:
              yield (
                  option_value_text,
                  Range(
                      start=Position(
                          line=start_line + line_offset,
                          character=start_character,
                      ),
                      end=Position(
                          line=start_line + line_offset,
                          character=start_character + len(option_value_text),
                      ),
                  ),
              )
            else:
              for match in re.finditer(r'([^\s]+)', option_value_text):
                yield (match.group(),
                       Range(
                           start=Position(
                               line=start_line + line_offset,
                               character=start_character + match.start(),
                           ),
                           end=Position(
                               line=start_line + line_offset,
                               character=start_character + match.start() +
                               len(match.group()),
                           ),
                       ))

  @staticmethod
  def looksLikeBuildoutProfile(uri: URI) -> bool:
    """Check if this URI looks like a buildout profile URI.
    """
    return (uri.endswith('.cfg') or uri.endswith('.cfg.in')
            or uri.endswith('.cfg.j2') or uri.endswith('.cfg.jinja2'))

  def resolve_value(self, section_name: str, option_name: str) -> str:
    """Get the value of an option, after substituting references.

    If substitution is not possible, the original value is returned.
    """
    def _get_section(section_name: str) -> BuildoutSection:
      section = self[section_name]
      if '<' in section:
        macro = copy.copy(self[section['<'].value])
        macro.update(**section)
        return macro
      return section

    def _resolve_value(
        section_name: str,
        option_name: str,
        value: str,
        seen: Set[Tuple[str, str]],
    ) -> str:
      if (section_name, option_name) in seen:
        return value
      seen.add((section_name, option_name))

      def _sub(match: Match[str]) -> str:
        referenced_section_name = match.group('section') or section_name
        if referenced_section_name in self:
          referenced_section = _get_section(referenced_section_name)
          referenced_option = match.group('option')
          if referenced_option in referenced_section:
            return _resolve_value(
                referenced_section_name,
                referenced_option,
                referenced_section[referenced_option].value,
                seen,
            )
        return value

      return option_reference_strict_re.sub(_sub, value)

    return _resolve_value(
        section_name,
        option_name,
        _get_section(section_name)[option_name].value,
        set(),
    )


class ResolvedBuildout(BuildoutProfile):
  """A buildout where extends and section macros <= have been extended.
  """
  if TYPE_CHECKING:

    def copy(self) -> 'ResolvedBuildout':
      ...


### cache ###

# a cache of un-resolved buildouts by uri
_parse_cache: Dict[URI, BuildoutProfile] = {}
# a cache of resolved buildouts by uri. This is the cache that will be used for most operations
# such as completions, code actions etc.
_resolved_buildout_cache: Dict[URI, ResolvedBuildout] = {}
# a cache of resolved buildouts by list of uris. This is an intermediate cache used to rebuild
# quickly the cach from _resolved__buildout_cache, because the cache from _resolved__buildout_cache
# needs to be flushed each time the document at `uri` is modified. This cache is only flushed if
# ${buildout:extends} is modified.
_resolved_extends_cache: Dict[Tuple[URI, ...], BuildoutProfile] = {}
# a mapping of dependencies between extends, so that we can clear caches when
# a profile is modified.
_extends_dependency_graph: Dict[URI, Set[URI]] = collections.defaultdict(set)


def clearCache(uri: URI) -> None:
  """Clear all caches for uri.

  This is to be called when the document is modified.
  """
  logger.debug("Clearing cache for %s", uri)
  _parse_cache.pop(uri, None)
  _clearExtendCache(uri, set())


def _clearExtendCache(uri: URI, done: Set[URI]) -> None:
  """Clear the `extends` cache for URI.

  This is to be called for all URIs extended by `uri`.
  """
  if uri in done:
    return
  done.add(uri)
  _resolved_buildout_cache.pop(uri, None)
  for uris in list(_resolved_extends_cache):
    if uri in uris:
      _resolved_extends_cache.pop(uris, None)
  logger.debug(
      "Clearing extends cache for %s Dependencies: %s",
      uri,
      _extends_dependency_graph[uri],
  )
  for dependend_uri in _extends_dependency_graph[uri]:
    _resolved_buildout_cache.pop(dependend_uri, None)
    for dependend_uris in list(_resolved_extends_cache):
      if dependend_uri in dependend_uris:
        _resolved_extends_cache.pop(dependend_uris, None)
    _clearExtendCache(dependend_uri, done)
  _extends_dependency_graph[uri].clear()


### buildout copied & modified functions ###

_isurl = re.compile('([a-zA-Z0-9+.-]+)://').match


async def parse(
    ls: LanguageServer,
    uri: URI,
    allow_errors: bool = True,
) -> BuildoutProfile:
  """
  Parse a sectioned setup file and return a non-resolved buildout.

  This is a wrapper over _parse which uses language server's workspace to access documents.
  Returned value changed to a BuildoutProfile instance.

  """
  try:
    return _parse_cache[uri].copy()
  except KeyError:
    pass

  parsed_uri = urllib.parse.urlparse(uri)
  if parsed_uri.scheme in (
      'http',
      'https',
  ):
    try:
      async with aiohttp_session.get_session().get(uri) as resp:
        resp.raise_for_status()
        fp = io.StringIO(await resp.text())
    except aiohttp.client_exceptions.ClientError:
      logger.warning('Error parsing from uri %s', uri, exc_info=True)
      fp = io.StringIO('')
  else:
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
  _parse_cache[uri] = parsed
  return parsed.copy()


async def _parse(
    fp: TextIO,
    uri: URI,
    allow_errors: bool,
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
    if isinstance(v, tuple):
      value = v[0]  # buildout < 2.9.3
    else:
      value = v.value
    sections['buildout'][k] = BuildoutOptionDefinition(
        value=value,
        location=Location(uri=uri,
                          range=Range(start=Position(line=0, character=0),
                                      end=Position(line=0, character=0))),
        default_value=True,
    )
  sections['buildout']['directory'] = BuildoutOptionDefinition(
      value='.',
      location=Location(uri=uri,
                        range=Range(start=Position(line=0, character=0),
                                    end=Position(line=0, character=0))),
      default_value=True,
  )
  sections.section_header_locations['buildout'] = Location(
      uri="",
      range=Range(
          start=Position(line=0, character=0),
          end=Position(line=0, character=0),
      ),
  )
  if slapos_instance_profile_filename_re.match(uri):
    # Add slapos instance generated sections.
    sections.section_header_locations.setdefault(
        'slap-connection',
        Location(uri='',
                 range=Range(start=Position(line=0, character=0),
                             end=Position(line=0, character=0))))
    slap_connection = BuildoutSection()
    for k in (
        'computer-id',
        'partition-id',
        'server-url',
        'key-file',
        'cert-file',
        'software-release-url',
    ):
      slap_connection[k] = BuildoutOptionDefinition(
          value='',
          location=Location(uri=uri,
                            range=Range(start=Position(line=0, character=0),
                                        end=Position(line=0, character=0))),
          default_value=True,
      )
    sections.setdefault('slap-connection', slap_connection)
    sections.section_header_locations.setdefault(
        'slap-network-information',
        Location(uri='',
                 range=Range(start=Position(line=0, character=0),
                             end=Position(line=0, character=0))))
    slap_network_information = BuildoutSection()
    for k in (
        'local-ipv4',
        'global-ipv6',
        'network-interface',
        'tap-ipv4',
        'tap-gateway',
        'tap-netmask',
        'tap-network',
        'global-ipv4-network',
    ):
      slap_network_information[k] = BuildoutOptionDefinition(
          value='',
          location=Location(uri=uri,
                            range=Range(start=Position(line=0, character=0),
                                        end=Position(line=0, character=0))),
          default_value=True,
      )
    sections.setdefault('slap-network-information', slap_network_information)

  jinja_parser = jinja.JinjaParser()
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

    jinja_parser.feed(line)
    if jinja_parser.is_in_jinja:
      sections.has_jinja = True
      continue
    line = jinja_parser.line

    if line[0] in '#;':
      continue  # comment

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
      # update current option in case of multi line option
      option_def.updateValue(
          value=("%s\n%s" % (option_def.value, line)),
          location=Location(
              uri=option_def.location.uri,
              range=Range(
                  start=option_def.location.range.start,
                  end=Position(line=lineno, character=len(_line) - 1),
              ),
          ),
      )
      cursect[optname] = option_def

    else:
      header = section_header(line)
      if header:
        sectname = header.group('name')
        sections.section_header_locations[sectname] = Location(
            uri=uri,
            range=Range(
                start=Position(line=lineno, character=0),
                end=Position(line=lineno + 1, character=0),
            ))
        if sectname in sections:
          cursect = sections[sectname]
        else:
          sections[sectname] = cursect = BuildoutSection()
          # initialize buildout default options
          cursect['_buildout_section_name_'] = BuildoutOptionDefinition(
              location=Location(uri=uri,
                                range=Range(start=Position(line=0,
                                                           character=0),
                                            end=Position(line=0,
                                                         character=0))),
              value=sectname,
              default_value=True,
          )
          # _profile_base_location_ is a slapos.buildout extension
          base_location = '.'
          if '/' in uri:
            base_location = uri[:uri.rfind('/')] + '/'
          cursect['_profile_base_location_'] = BuildoutOptionDefinition(
              location=Location(uri=uri,
                                range=Range(start=Position(line=0,
                                                           character=0),
                                            end=Position(line=0,
                                                         character=0))),
              value=base_location,
              default_value=True,
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
          optlocation = Location(
              uri=uri,
              range=Range(
                  start=Position(
                      line=lineno,
                      character=len(mo.groups()[0]) + 1,
                  ),
                  end=Position(
                      line=lineno,
                      character=len(line) - 1,
                  ),
              ),
          )
          if optname in cursect:
            option_def = cursect[optname]
            option_def.overrideValue(optval, optlocation)
          else:
            option_def = BuildoutOptionDefinition(value=optval,
                                                  location=optlocation)
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
        section[name].updateValue(
            leading_blank_lines.sub('', textwrap.dedent(value.rstrip())))

  return sections


async def getProfileForTemplate(
    ls: LanguageServer,
    document: Document,
) -> Optional[URI]:
  """Find the profile for template.

  For example when there's a buildout.cfg containing:
  
    [template]
    recipe = collective.recipe.template
    input = template.in
    output = template

  when called with `uri` template.in, this function would return `buildout.cfg`.

  """
  uri = document.uri

  def getCandidateBuildoutProfiles() -> Iterator[pathlib.Path]:
    path = pathlib.Path(document.path).parent
    for _ in range(3):  # look for buildouts up to 3 levels
      # we sort just to have stable behavior
      for profile in sorted(path.glob('*.cfg')):
        yield profile
      path = path.parent

  if slapos_instance_profile_filename_re.match(
      uri) or not uri.endswith('.cfg'):
    for buildout_path in getCandidateBuildoutProfiles():
      resolved_path = str(buildout_path.resolve())
      # For paths in workspace, we don't use buildout_path.resolve().as_uri(),
      # because we have fake uri -> path mapping in tests
      if resolved_path.startswith(ls.workspace.root_path):
        buildout_uri = resolved_path.replace(
            ls.workspace.root_path,
            ls.workspace.root_uri,
            1,
        )
      else:
        # but we still need to support the case where the path is outside the workspace
        buildout_uri = buildout_path.resolve().as_uri()
      logger.debug("Trying to find templates's buildout with %s -> %s",
                   buildout_path, buildout_uri)
      buildout = await _open(
          ls,
          '',
          buildout_uri,
          [],
          allow_errors=True,
      )
      assert isinstance(buildout, BuildoutProfile)
      template = await buildout.getTemplate(ls, uri)
      if template is not None:
        return buildout_uri
  return None


async def open(
    ls: LanguageServer,
    uri: URI,
    allow_errors: bool = True,
    force_open_as_buildout_profile: bool = False,
) -> Optional[Union[BuildoutTemplate, ResolvedBuildout]]:
  """Open an URI and returnes either a buildout or a profile connected to buildout.

  In the case of slapos buildout templates (instance.cfg.in), it is both. This is
  not true for slapos buildout templates as jinja templates, which have their own
  namespace as ${} and not as $${}.

  force_open_as_buildout_profile is used to force assuming that this file is a
  buildout profile (and not a buildout template).

  For buildout, it is a wrapper over _open which uses language server's workspace
  """
  document = ls.workspace.get_document(uri)
  logger.debug("open %s", uri)
  if not force_open_as_buildout_profile:
    # First, try to read as a template, because buildout profiles can be templates.
    buildout_uri = await getProfileForTemplate(ls, document)
    if buildout_uri is not None:
      buildout = await _open(
          ls,
          '',
          buildout_uri,
          [],
          allow_errors=allow_errors,
      )
      return await buildout.getTemplate(ls, uri)

  if BuildoutProfile.looksLikeBuildoutProfile(
      uri) or force_open_as_buildout_profile:
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
  try:
    return _resolved_buildout_cache[uri].copy()
  except KeyError:
    pass

  base = uri[:uri.rfind('/')] + '/'

  if uri in seen:
    if allow_errors:
      return ResolvedBuildout(uri, '')
    raise RecursiveIncludeError("Recursive file include", seen, uri)

  seen.append(uri)

  profile = await parse(ls, uri, allow_errors=allow_errors)
  extends_option = profile['buildout'].pop(
      'extends', None) if 'buildout' in profile else None

  result = profile
  has_dynamic_extends = False
  has_jinja = profile.has_jinja
  if extends_option:
    extends = extends_option.value.split()
    has_dynamic_extends = (jinja.JinjaParser.jinja_value in extends) or any(
        option_reference_re.match(extended_profile)
        for extended_profile in extends)
    if extends:
      # buildout:extends, as absolute URI that we can use as cache key
      absolute_extends: Tuple[URI, ...] = tuple(
          urllib.parse.urljoin(base, x) for x in extends)
      if absolute_extends in _resolved_extends_cache:
        logger.debug("_open %r was in cache", absolute_extends)
        eresult = _resolved_extends_cache[absolute_extends]
      else:
        eresult = await _open(ls, base, extends.pop(0), seen, allow_errors)
        for fname in extends:
          has_dynamic_extends = has_dynamic_extends or eresult.has_dynamic_extends
          has_jinja = has_jinja or eresult.has_jinja
          eresult = _update(eresult, await _open(ls, base, fname, seen,
                                                 allow_errors))
        for absolute_extend in absolute_extends:
          _extends_dependency_graph[absolute_extend].add(uri)

      if not has_dynamic_extends:
        _resolved_extends_cache[absolute_extends] = eresult
      result = _update(eresult, profile)

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

  result.has_dynamic_extends = has_dynamic_extends
  result.has_jinja = has_jinja
  resolved = cast(ResolvedBuildout, result)
  _resolved_buildout_cache[uri] = resolved
  return resolved.copy()


def _update_section(
    s1: BuildoutSection,
    s2: BuildoutSection,
) -> BuildoutSection:
  """Update s1 with values from s2.
  """
  s1 = s1.copy()
  for k, v in s2.items():
    if k == '_profile_base_location_':
      continue
    if k.endswith('-'):
      k = k.rstrip(' -')
      # Find v1 in s2 first; it may have been set by a += operation first
      option_def = s2.get(k, s1.get(k, v))
      new_option_def = option_def.copy()
      new_option_def.overrideValue(
          # same logic as as SectionKey.removeFromValue
          value='\n'.join(new_v for new_v in option_def.value.split('\n')
                          if new_v not in v.value.split('\n')),
          location=v.locations[-1])
      s1[k] = new_option_def
    elif k.endswith('+'):
      k = k.rstrip(' +')
      # Find v1 in s2 first; it may have been defined locally too.
      option_def = s2.get(k, s1.get(k, v))
      option_values = [] if option_def.default_value else option_def.value.split(
          '\n')
      new_option_def = option_def.copy()
      new_option_def.overrideValue(
          # same logic as as SectionKey.addToValue
          value='\n'.join(option_values + v.value.split('\n')),
          location=v.location)
      s1[k] = new_option_def
    else:
      if k in s1 and (v.location != s1[k].location):
        if not v.default_value:
          new_option_def = s1[k].copy()
          new_option_def.overrideValue(v.value, v.location)
          s1[k] = new_option_def
      else:
        s1[k] = v
  return s1


def _update(d1: BuildoutProfile, d2: BuildoutProfile) -> BuildoutProfile:
  """update d1 with values from d2
  """
  d1 = d1.copy()
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

    result = BuildoutSection()
    for iname in to_do.value.split('\n'):
      iname = iname.strip()
      if not iname:
        continue
      raw = buildout.get(iname)
      if raw is None:
        raise MissingExtendedSection("No section named %r" % iname)
      result.update({
          k: v.copy()
          for (k, v) in _do_extend_raw(iname, raw, buildout, doing).items()
      })
    result = _update_section(result, section)
    result.pop('<', None)
    return result
  finally:
    assert doing.pop() == name
