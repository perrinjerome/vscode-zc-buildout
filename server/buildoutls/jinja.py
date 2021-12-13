"""Support of jinja context
"""

import enum
import re
from typing import List


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
expression_re = re.compile(r'\{\{.*?\}\}')
multiline_expression_start_re = re.compile(r'^\s*\{\{')
multiline_expression_end_re = re.compile(r'\}\}')
multiline_statement_start_re = re.compile(r'^\s*\{%')
multiline_statement_end_re = re.compile(r'%\}')


class JinjaParser:
  """A very simple jinja parser which allow skipping lines containing jinja blocks.
  """
  # a replacement for jinja expressions, so that we
  # can still parse them as buildout
  jinja_value = "JINJA_EXPRESSION"

  def __init__(self) -> None:
    self.has_expression = False
    self.is_in_comment = False
    self.is_error = False
    self._stack: List[JinjaStatement] = []
    self._current_line_was_in_jinja = False
    self._in_comment = False
    self._in_multiline_expression = False
    self._in_multiline_statement = False
    self.line = ""

  def feed(self, line: str) -> None:
    """Feeds a line and update the state.
    """
    self._current_line_was_in_jinja = False
    self.has_expression = bool(expression_re.search(line))
    expression_re_match = expression_re.search(line)
    if expression_re_match:
      if expression_re_match.start() == 0 \
         and expression_re_match.end() == len(line.strip()):
        line = f'{self.jinja_value} = {self.jinja_value}'
      else:
        line = expression_re.sub(self.jinja_value, line)
    self.line = line
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

    if multiline_expression_start_re.match(
        line) or self._in_multiline_expression:
      self._current_line_was_in_jinja = True
      self._in_multiline_expression = multiline_expression_end_re.search(
          line) is None
    if multiline_statement_start_re.match(
        line) or self._in_multiline_statement:
      self._current_line_was_in_jinja = True
      self._in_multiline_statement = multiline_statement_end_re.search(
          line) is None

  @property
  def is_in_jinja(self) -> bool:
    return (bool(self._stack) or self._current_line_was_in_jinja)
