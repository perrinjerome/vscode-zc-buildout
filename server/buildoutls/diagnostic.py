import logging
import re
import urllib.parse
from typing import AsyncIterable, Set

from pygls.lsp.types import (
    Diagnostic,
    DiagnosticRelatedInformation,
    DiagnosticSeverity,
    Position,
    Range,
)
from pygls.server import LanguageServer
from zc.buildout.configparser import MissingSectionHeaderError, ParsingError

from . import buildout, jinja, pypi, types

logger = logging.getLogger(__name__)
_profile_base_location_re = re.compile(
    r'\$\{([-a-zA-Z0-9 ._]*):_profile_base_location_\}')

# this is a function to be patched in unittest
from os.path import exists as os_path_exists

pypi_client = pypi.PyPIClient()


async def getDiagnostics(
    ls: LanguageServer,
    uri: str,
) -> AsyncIterable[Diagnostic]:

  parsed = None
  if buildout.BuildoutProfile.looksLikeBuildoutProfile(uri):
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
        yield Diagnostic(
            message=e.message,
            range=Range(
                start=Position(line=e.lineno, character=0),
                end=Position(line=e.lineno + 1, character=0),
            ),
            source="buildout",
            severity=DiagnosticSeverity.Error,
        )
      else:
        for (lineno, _), msg in zip(e.errors, e.message.splitlines()[1:]):
          msg = msg.split(":", 1)[1].strip()
          yield Diagnostic(
              message=f"ParseError: {msg}",
              range=Range(
                  start=Position(line=lineno, character=0),
                  end=Position(line=lineno + 1, character=0),
              ),
              source="buildout",
              severity=DiagnosticSeverity.Error,
          )

  resolved_buildout = await buildout.open(
      ls=ls,
      uri=uri,
  )
  assert resolved_buildout is not None

  # all these checks can not be performed on a buildout profile
  # with dynamic extends, we don't know what it's in the dynamic profile.
  has_dynamic_extends = (isinstance(resolved_buildout,
                                    buildout.BuildoutProfile)
                         and resolved_buildout.has_dynamic_extends)
  if not has_dynamic_extends:
    installed_parts: Set[str] = set([])
    if isinstance(resolved_buildout, buildout.BuildoutProfile):
      if "parts" in resolved_buildout["buildout"]:
        installed_parts = set(
            (v[0]
             for v in resolved_buildout.getOptionValues("buildout", "parts")))

    async for symbol in resolved_buildout.getAllOptionReferenceSymbols():
      if symbol.referenced_section is None:
        yield Diagnostic(
            message=
            f"Section `{symbol.referenced_section_name}` does not exist.",
            range=symbol.section_range,
            source="buildout",
            severity=DiagnosticSeverity.Error,
        )

      elif symbol.referenced_option is None:
        # if we have a recipe, either it's a known recipe where we know
        # all options that this recipe can generate, or it's an unknown
        # recipe and in this case we assume it's OK.
        if (symbol.referenced_section_recipe_name is not None
            and symbol.referenced_section_recipe is None) or (
                symbol.referenced_section_recipe is not None and
                (symbol.referenced_section_recipe.any_options
                 or symbol.referenced_option_name
                 in symbol.referenced_section_recipe.generated_options)):
          continue
        # if a section is a macro, it's OK to self reference ${:missing}
        if (symbol.is_same_section_reference
            and symbol.current_section_name not in installed_parts):
          continue
        yield Diagnostic(
            message=
            f"Option `{symbol.referenced_option_name}` does not exist in `{symbol.referenced_section_name}`.",
            range=symbol.option_range,
            source="buildout",
            severity=DiagnosticSeverity.Warning,
        )

    if isinstance(resolved_buildout, buildout.BuildoutProfile):
      for section_name, section in resolved_buildout.items():
        if (section_name in installed_parts
            and resolved_buildout.section_header_locations[section_name].uri
            == uri):
          # check for required options
          recipe = section.getRecipe()
          if recipe:
            missing_required_options = recipe.required_options.difference(
                section.keys())
            if missing_required_options:
              missing_required_options_text = ", ".join(
                  ["`{}`".format(o) for o in missing_required_options])
              yield Diagnostic(
                  message=
                  f"Missing required options for `{recipe.name}`: {missing_required_options_text}",
                  range=resolved_buildout.
                  section_header_locations[section_name].range,
                  source="buildout",
                  severity=DiagnosticSeverity.Error,
              )

        # check for options redefined to same values
        for option_name, option in section.items():
          if option.locations[-1].uri != uri:
            continue
          if jinja.JinjaParser.jinja_value in (option_name, option.value):
            continue
          # extend ${:_profile_base_location_}, because this option is dynamic
          # per profile, so redefining an option from another profile with the same
          # ${:_profile_base_location_} should not be considered as redefining to
          # same value.
          if len(option.locations) > 1 and (_profile_base_location_re.sub(
              option.locations[-1].uri,
              option.values[-1],
          ) == _profile_base_location_re.sub(
              option.locations[-2].uri,
              option.values[-2],
          )):
            related_information = []
            reported_related_location = set()
            for other_location, other_value, other_is_default_value in zip(
                option.locations,
                option.values,
                option.default_values,
            ):
              hashable_location = (
                  other_location.uri,
                  other_location.range.start.line,
              )
              if hashable_location in reported_related_location:
                continue
              reported_related_location.add(hashable_location)
              related_information.append(
                  DiagnosticRelatedInformation(
                      location=other_location,
                      message=f"default value: `{other_value}`"
                      if other_is_default_value else f"value: `{other_value}`",
                  ))

            yield Diagnostic(
                message=f"`{option_name}` already has value `{option.value}`.",
                range=option.locations[-1].range,
                source="buildout",
                severity=DiagnosticSeverity.Warning,
                related_information=related_information,
            )

      jinja_parser = jinja.JinjaParser()
      if parsed is not None and "extends" in parsed["buildout"]:
        for extend_filename, extend_range in parsed.getOptionValues(
            "buildout", "extends"):
          if extend_filename.startswith("${"):
            continue  # assume substitutions are OK
          jinja_parser.feed(extend_filename)
          if jinja_parser.is_in_jinja:
            continue  # ignore anything in jinja context
          if buildout._isurl(extend_filename):
            continue
          base = uri[:uri.rfind('/')] + '/'
          if not os_path_exists(
              urllib.parse.urlparse(urllib.parse.urljoin(
                  base, extend_filename)).path):
            yield Diagnostic(
                message=f"Extended profile `{extend_filename}` does not exist.",
                range=extend_range,
                source="buildout",
                severity=DiagnosticSeverity.Error,
            )

      if "parts" in resolved_buildout["buildout"]:
        for part_name, part_range in resolved_buildout.getOptionValues(
            "buildout", "parts"):
          if part_name:
            if part_name.startswith("${"):
              continue  # assume substitutions are OK
            jinja_parser.feed(part_name)
            if jinja_parser.is_in_jinja:
              continue  # ignore anything in jinja context

            if part_name not in resolved_buildout:
              if not resolved_buildout.has_dynamic_extends:
                yield Diagnostic(
                    message=f"Section `{part_name}` does not exist.",
                    range=part_range,
                    source="buildout",
                    severity=DiagnosticSeverity.Error,
                )
            elif "recipe" not in resolved_buildout[part_name]:
              yield Diagnostic(
                  message=f"Section `{part_name}` has no recipe.",
                  range=part_range,
                  source="buildout",
                  severity=DiagnosticSeverity.Error,
              )

      if resolved_buildout.get('versions'):
        for package_name, option in resolved_buildout['versions'].items():
          if option.location.uri != uri:
            continue
          if package_name in (
              '_buildout_section_name_',
              '_profile_base_location_',
          ):
            continue

          package_version = option.value

          # handle some slapos markers in versions
          if package_version.endswith(':whl'):
            package_version = package_version[:-4]
          if "+slapos" in package_version.lower():
            continue

          logger.debug(
              'Found package %s at version %s @ %s',
              package_name,
              package_version,
              option.location,
          )

          known_vulnerabilities = tuple(
              pypi_client.get_known_vulnerabilities(
                  package_name,
                  package_version,
              ))
          newer_version = pypi_client.get_latest_version(
              package_name, package_version)
          if newer_version:
            severity = DiagnosticSeverity.Hint
            message = f"Newer version available ({newer_version})"
            if known_vulnerabilities:
              message = f'{package_name} {package_version} has some known vunerabilities:\n' + '\n\n'.join(
                  f"{v.id}\n{v.details}\n{v.link}"
                  for v in known_vulnerabilities)
              severity = DiagnosticSeverity.Warning

            yield Diagnostic(
                message=message,
                range=option.location.range,
                source="buildout",
                severity=severity,
                data=types.PyPIPackageInfo(
                    latest_version=str(newer_version),
                    url=pypi_client.get_home_page_url(
                        package_name,
                        package_version,
                    ),
                    known_vulnerabilities=known_vulnerabilities,
                ),
            )
