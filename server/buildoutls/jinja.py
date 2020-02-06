"""Support of jinja context
"""

import re
import enum

from typing import List, Dict


# https://jinja.palletsprojects.com/en/2.11.x/templates/#list-of-control-structures
# we ignore block assignments for simplicity
class JinjaStatement(str, enum.Enum):
  For = 'for'
  If = 'if'
  Macro = 'macro'
  Call = 'call'
  Filter = 'filter'


jinja_statements = set(JinjaStatement)

end_block_statement = {
    'endfor': JinjaStatement.For,
    'endif': JinjaStatement.If,
    'endmacro': JinjaStatement.Macro,
    'endcall': JinjaStatement.Call,
    'endfilter': JinjaStatement.Filter,
}

statement_re = re.compile(r'.*\{%[\-\+\s]*(?P<statement>[\w]+).*%\}')
expression_re = re.compile(r'.*\{\{.*\}\}')


class JinjaParser:
  """A very simple jinja parser which allow skipping lines containing jinja blocks.
  """
  def __init__(self) -> None:
    self.is_in_expression = False
    self.is_in_comment = False
    self.is_error = False
    self._stack: List[JinjaStatement] = []
    self._current_line_was_in_jinja = False
    self._in_comment = False

  def feed(self, line: str) -> None:
    """Feeds a line and update the state.
    """
    self._current_line_was_in_jinja = False
    self.is_in_expression = bool(expression_re.match(line))
    self.is_error = False

    if '{#' in line or self._in_comment:
      self._current_line_was_in_jinja = True
      self._in_comment = '#}' not in line

    statement_match = statement_re.match(line)
    if statement_match:
      self._current_line_was_in_jinja = True
      statement = statement_match.group('statement')
      if statement in jinja_statements:
        self._stack.append(JinjaStatement(statement))
      elif statement in end_block_statement:
        self.is_error = True
        if self._stack:
          popped = self._stack.pop()
          self.is_error = end_block_statement[statement] != popped

  @property
  def is_in_jinja(self) -> bool:
    return (bool(self._stack) or self.is_in_expression or
            self._current_line_was_in_jinja)
