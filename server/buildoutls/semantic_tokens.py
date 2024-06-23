from typing import List, Optional
import logging
import itertools

from lsprotocol.types import SemanticTokens
import pygments.lexers
import pygments.token

from .buildout import BuildoutProfile
from .recipes import RecipeOptionKind
from .server import LanguageServer
from .types import SEMANTIC_TOKEN_TYPES


logger = logging.getLogger(__name__)


token_type_by_type = {t: SEMANTIC_TOKEN_TYPES.index(t) for t in SEMANTIC_TOKEN_TYPES}


def get_token_type(token_pygment_type: pygments.token._TokenType) -> Optional[int]:
  if token_pygment_type in pygments.token.Comment:
    return token_type_by_type["comment"]
  if token_pygment_type in pygments.token.String:
    return token_type_by_type["string"]
  if token_pygment_type in pygments.token.Number:
    return token_type_by_type["number"]
  if token_pygment_type in pygments.token.Name.Class:
    return token_type_by_type["class"]
  if token_pygment_type in pygments.token.Name.Function:
    return token_type_by_type["function"]
  if (
    token_pygment_type in pygments.token.Name.Builtin
    or token_pygment_type in pygments.token.Keyword.Constant
  ):
    return token_type_by_type["type"]
  if token_pygment_type in pygments.token.Name:
    return token_type_by_type["variable"]
  if token_pygment_type in pygments.token.Keyword:
    return token_type_by_type["keyword"]
  return None


def get_semantic_tokens(
  ls: LanguageServer,
  parsed: BuildoutProfile,
) -> SemanticTokens:
  data: List[int] = []

  delta_line = delta_start = last_block_end = 0
  for section_value in parsed.values():
    if recipe := section_value.getRecipe():
      for option_key, option_value in section_value.items():
        if (
          (option_definition := recipe.options.get(option_key))
          and option_value.value
          and option_definition.kind == RecipeOptionKind.PythonScript
        ):
          for option_value_location in option_value.locations:
            if parsed.uri != option_value_location.uri:
              continue
            lexer = pygments.lexers.get_lexer_by_name("python")

            doc = ls.workspace.get_text_document(option_value_location.uri)
            source_code = "".join(
              itertools.chain(
                (
                  doc.lines[option_value_location.range.start.line][
                    option_value_location.range.start.character :
                  ],
                ),
                doc.lines[
                  option_value_location.range.start.line
                  + 1 : option_value_location.range.end.line
                ],
                (doc.lines[option_value_location.range.end.line].rstrip(),),
              )
            )
            this_block_start = option_value.location.range.start.line
            delta_line += this_block_start - last_block_end
            last_block_end = option_value.location.range.end.line

            # skip empy lines at beginning
            for line in source_code.splitlines():
              if line.strip():
                break
              delta_line += 1

            for token_pygment_type, token_text in lexer.get_tokens(source_code):
              # A specific token i in the file consists of the following array indices:
              #
              # at index 5*i - deltaLine: token line number, relative to the previous token
              # at index 5*i+1 - deltaStart: token start character, relative to the previous
              #   token (relative to 0 or the previous token’s start if they are on the same
              #   line)
              # at index 5*i+2 - length: the length of the token.
              # at index 5*i+3 - tokenType: will be looked up in
              #   SemanticTokensLegend.tokenTypes. We currently ask that tokenType < 65536.
              # at index 5*i+4 - tokenModifiers: each set bit will be looked up in
              #   SemanticTokensLegend.tokenModifiers
              token_type = get_token_type(token_pygment_type)
              if token_type is not None:
                # explode token spawning on multiple lines into multiple tokens
                for token_text_line in token_text.splitlines(True):
                  tok = [
                    delta_line,
                    delta_start,
                    len(token_text_line),
                    token_type,
                    0,
                  ]
                  data.extend(tok)
                  delta_line = 1 if "\n" in token_text_line else 0
                  delta_start = len(token_text)
              else:
                if line_count := (token_text.replace("\r\n", "\n").count("\n")):
                  delta_line += line_count
                  delta_start = 0
                else:
                  delta_start += len(token_text)

            if not source_code.endswith("\n"):
              # pygments always output a final \n, but sometimes option does
              # not include one, so we adjust for this case.
              delta_line -= 1

  return SemanticTokens(data=data)
