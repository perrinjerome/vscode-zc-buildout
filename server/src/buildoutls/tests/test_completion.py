import textwrap

from lsprotocol.types import (
  CompletionContext,
  CompletionParams,
  CompletionTriggerKind,
  CompletionItemTag,
  MarkupContent,
  MarkupKind,
  Position,
  Range,
  TextDocumentIdentifier,
  TextEdit,
)
from pygls.lsp.server import LanguageServer

from ..server import lsp_completion


async def test_complete_section_reference(server: LanguageServer):
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )
  # complete section names in ${se|}
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/sections.cfg"),
    position=Position(line=13, character=13),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted(
    [
      (c.text_edit.range, c.text_edit.new_text)
      for c in completions
      if isinstance(c.text_edit, TextEdit)
    ]
  ) == [
    (
      Range(start=Position(line=13, character=10), end=Position(line=13, character=13)),
      "${buildout",
    ),
    (
      Range(start=Position(line=13, character=10), end=Position(line=13, character=13)),
      "${section1",
    ),
    (
      Range(start=Position(line=13, character=10), end=Position(line=13, character=13)),
      "${section2",
    ),
    (
      Range(start=Position(line=13, character=10), end=Position(line=13, character=13)),
      "${section3",
    ),
    (
      Range(start=Position(line=13, character=10), end=Position(line=13, character=13)),
      "${xsection4",
    ),
  ]

  # edge cases: complete section names on a line with a ${section:ref}
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/sections.cfg"),
    position=Position(line=4, character=32),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted(
    [
      (c.text_edit.range, c.text_edit.new_text)
      for c in completions
      if isinstance(c.text_edit, TextEdit)
    ]
  ) == [
    (
      Range(start=Position(line=4, character=30), end=Position(line=4, character=32)),
      "${buildout",
    ),
    (
      Range(start=Position(line=4, character=30), end=Position(line=4, character=32)),
      "${section1",
    ),
    (
      Range(start=Position(line=4, character=30), end=Position(line=4, character=32)),
      "${section2",
    ),
    (
      Range(start=Position(line=4, character=30), end=Position(line=4, character=32)),
      "${section3",
    ),
    (
      Range(start=Position(line=4, character=30), end=Position(line=4, character=32)),
      "${xsection4",
    ),
  ]

  # in documentation we show the section content
  (documentation,) = [c.documentation for c in completions if c.label == "section1"]
  assert isinstance(documentation, MarkupContent)
  assert documentation.kind == MarkupKind.Markdown
  assert documentation.value == textwrap.dedent("""\
      ```ini
      option1 = value1
      ```""")

  # section names of known recipes also have description in markdown for documentation
  (documentation,) = [c.documentation for c in completions if c.label == "section3"]
  assert isinstance(documentation, MarkupContent)
  assert documentation.value == textwrap.dedent("""\
      ## `plone.recipe.command`

      ---
      The `plone.recipe.command` buildout recipe allows you to run a command when a buildout part is installed or updated.

      ---
      ```ini
      recipe = plone.recipe.command
      option4 = value4
      ```""")

  # complete section names in [se|]
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/sections.cfg"),
    position=Position(line=15, character=1),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted(
    [
      (c.text_edit.range, c.text_edit.new_text)
      for c in completions
      if isinstance(c.text_edit, TextEdit)
    ]
  ) == [
    (
      Range(start=Position(line=15, character=1), end=Position(line=15, character=1)),
      "buildout",
    ),
    (
      Range(start=Position(line=15, character=1), end=Position(line=15, character=1)),
      "section1",
    ),
    (
      Range(start=Position(line=15, character=1), end=Position(line=15, character=1)),
      "section2",
    ),
    (
      Range(start=Position(line=15, character=1), end=Position(line=15, character=1)),
      "section3",
    ),
    (
      Range(start=Position(line=15, character=1), end=Position(line=15, character=1)),
      "xsection4",
    ),
  ]

  # test completions from various positions where all sections are suggested
  for completion_position, textEditRange in (
    (
      Position(line=5, character=10),
      Range(start=Position(line=5, character=10), end=Position(line=5, character=20)),
    ),
    (
      Position(line=5, character=17),
      Range(start=Position(line=5, character=10), end=Position(line=5, character=20)),
    ),
    (
      Position(line=5, character=32),
      Range(start=Position(line=5, character=30), end=Position(line=5, character=40)),
    ),
    (
      Position(line=5, character=34),
      Range(start=Position(line=5, character=30), end=Position(line=5, character=40)),
    ),
    (
      Position(line=5, character=40),
      Range(start=Position(line=5, character=30), end=Position(line=5, character=40)),
    ),
    (
      Position(line=5, character=52),
      Range(start=Position(line=5, character=50), end=Position(line=5, character=60)),
    ),
    (
      Position(line=5, character=56),
      Range(start=Position(line=5, character=50), end=Position(line=5, character=60)),
    ),
  ):
    params = CompletionParams(
      text_document=TextDocumentIdentifier(uri="file:///completions/sections.cfg"),
      position=completion_position,
      context=context,
    )
    completions = await lsp_completion(server, params)
    assert completions is not None
    assert sorted(
      [
        (c.text_edit.range, c.text_edit.new_text, c.filter_text, c.label)
        for c in completions
        if isinstance(c.text_edit, TextEdit)
      ]
    ) == [
      (textEditRange, "${buildout", "${buildout", "buildout"),
      (textEditRange, "${section1", "${section1", "section1"),
      (textEditRange, "${section2", "${section2", "section2"),
      (textEditRange, "${section3", "${section3", "section3"),
      (textEditRange, "${xsection4", "${xsection4", "xsection4"),
    ]


async def test_complete_option_reference(server: LanguageServer):
  context = CompletionContext(trigger_kind=CompletionTriggerKind.Invoked)

  # complete referenced options
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/options.cfg"),
    position=Position(line=1, character=21),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
    "_buildout_section_name_",
    "_profile_base_location_",
    "option2",
    "recipe",
  ]

  # complete referenced options, including recipe generated options
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/recipe.cfg"),
    position=Position(line=8, character=41),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
    "_buildout_section_name_",
    "_profile_base_location_",
    "location",
    "recipe",
    "repository",
  ]

  # complete referenced options from current section
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/options.cfg"),
    position=Position(line=2, character=13),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  # options of section1
  assert sorted([c.label for c in completions]) == [
    "_buildout_section_name_",
    "_profile_base_location_",
    "option1",
    "option2",
    "option3",
  ]

  assert sorted(
    [
      (c.text_edit.range, c.text_edit.new_text)
      for c in completions
      if isinstance(c.text_edit, TextEdit)
    ]
  ) == [
    (
      Range(start=Position(line=2, character=13), end=Position(line=2, character=13)),
      "_buildout_section_name_}",
    ),
    (
      Range(start=Position(line=2, character=13), end=Position(line=2, character=13)),
      "_profile_base_location_}",
    ),
    (
      Range(start=Position(line=2, character=13), end=Position(line=2, character=13)),
      "option1}",
    ),
    (
      Range(start=Position(line=2, character=13), end=Position(line=2, character=13)),
      "option2}",
    ),
    (
      Range(start=Position(line=2, character=13), end=Position(line=2, character=13)),
      "option3}",
    ),
  ]

  # options has values for docstrings
  (documentation,) = [c.documentation for c in completions if c.label == "option3"]
  assert isinstance(documentation, MarkupContent)
  assert documentation.kind == MarkupKind.Markdown
  assert documentation.value == "```\nvalue3```"

  # more complex replace text scenarios
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/options.cfg"),
    position=Position(line=13, character=53),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted(
    [
      (c.text_edit.range, c.text_edit.new_text)
      for c in completions
      if isinstance(c.text_edit, TextEdit)
    ]
  ) == [
    (
      Range(start=Position(line=13, character=51), end=Position(line=13, character=59)),
      "_buildout_section_name_}",
    ),
    (
      Range(start=Position(line=13, character=51), end=Position(line=13, character=59)),
      "_profile_base_location_}",
    ),
    (
      Range(start=Position(line=13, character=51), end=Position(line=13, character=59)),
      "option1}",
    ),
    (
      Range(start=Position(line=13, character=51), end=Position(line=13, character=59)),
      "option2}",
    ),
    (
      Range(start=Position(line=13, character=51), end=Position(line=13, character=59)),
      "option3}",
    ),
  ]

  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/options.cfg"),
    position=Position(line=14, character=53),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted(
    [
      (c.text_edit.range, c.text_edit.new_text)
      for c in completions
      if isinstance(c.text_edit, TextEdit)
    ]
  ) == [
    (
      Range(start=Position(line=14, character=51), end=Position(line=14, character=58)),
      "_buildout_section_name_}",
    ),
    (
      Range(start=Position(line=14, character=51), end=Position(line=14, character=58)),
      "_profile_base_location_}",
    ),
    (
      Range(start=Position(line=14, character=51), end=Position(line=14, character=58)),
      "option1}",
    ),
    (
      Range(start=Position(line=14, character=51), end=Position(line=14, character=58)),
      "option2}",
    ),
    (
      Range(start=Position(line=14, character=51), end=Position(line=14, character=58)),
      "option3}",
    ),
  ]


async def test_complete_options_with_space(server: LanguageServer):
  # bug reproduction test
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )
  params = CompletionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///completions/options_with_space.cfg"
    ),
    position=Position(line=2, character=22),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
    "_buildout_section_name_",
    "_profile_base_location_",
    "option",
  ]


async def test_complete_option_name(server: LanguageServer):
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )
  # complete options of a section
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/options.cfg"),
    position=Position(line=8, character=0),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  # completion includes known options of the recipe and already defined
  # options, for cases where user wants to override an already defined
  # option
  assert sorted([c.label for c in completions]) == [
    "command",
    "location",
    "option2",
    "recipe",
    "stop-on-error",
    "update-command",
  ]

  # we insert with the = like: option =
  (textEdit,) = [c.text_edit for c in completions if c.label == "command"]
  assert isinstance(textEdit, TextEdit)
  assert textEdit.range == Range(
    start=Position(line=8, character=0), end=Position(line=8, character=0)
  )
  assert textEdit.new_text == "command = "
  assert [
    c.documentation.value
    for c in completions
    if c.label == "command" and isinstance(c.documentation, MarkupContent)
  ] == ["Command to run when the buildout part is installed."]

  # when there's no recipe we offer completion for "recipe"
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/options.cfg"),
    position=Position(line=10, character=1),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == ["recipe"]
  assert sorted(
    [c.text_edit.new_text for c in completions if isinstance(c.text_edit, TextEdit)]
  ) == ["recipe = "]

  # Also works when document has invalid syntax
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///diagnostics/syntax_error.cfg"),
    position=Position(line=3, character=0),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == ["option1", "recipe"]
  assert sorted(
    [c.text_edit.new_text for c in completions if isinstance(c.text_edit, TextEdit)]
  ) == ["option1 = ", "recipe = "]


async def test_complete_referenced_option_recipe_valid_values(server: LanguageServer):
  # complete option values with recipe valid values
  params = CompletionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///completions/option_definitions.cfg"
    ),
    position=Position(line=2, character=16),
    context=CompletionContext(
      trigger_kind=CompletionTriggerKind.Invoked,
    ),
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == ["true", "yes"]
  assert sorted(
    [c.text_edit.new_text for c in completions if isinstance(c.text_edit, TextEdit)]
  ) == ["true", "yes"]


async def test_complete_deprecated_options(server: LanguageServer):
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/recipe.cfg"),
    position=Position(line=12, character=1),
    context=CompletionContext(trigger_kind=CompletionTriggerKind.Invoked),
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert "rendered" in [c.label for c in completions]
  (rendered_completion,) = [c for c in completions if c.label == "rendered"]
  assert rendered_completion.tags == [CompletionItemTag.Deprecated]
  assert rendered_completion.documentation == MarkupContent(
    kind=MarkupKind.Markdown,
    value=textwrap.dedent("""\
          **Deprecated**
          Use `output` option instead

          ----
          Where rendered template should be stored."""),
  )
  (output_completion,) = [c for c in completions if c.label == "output"]
  assert not output_completion.tags
  assert output_completion.documentation == MarkupContent(
    kind=MarkupKind.Markdown, value="Path of the output"
  )


async def test_complete_recipe_option_value(server: LanguageServer):
  # complete recipe= with known recipes
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/recipe.cfg"),
    position=Position(line=1, character=18),
    context=CompletionContext(trigger_kind=CompletionTriggerKind.Invoked),
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert "plone.recipe.command" in [c.label for c in completions]
  assert [
    c.text_edit.new_text
    for c in completions
    if isinstance(c.text_edit, TextEdit) and c.label == "plone.recipe.command"
  ] == ["plone.recipe.command"]
  assert [
    c.text_edit.range
    for c in completions
    if isinstance(c.text_edit, TextEdit) and c.label == "plone.recipe.command"
  ] == [Range(start=Position(line=1, character=9), end=Position(line=1, character=18))]


async def test_complete_macro_option_value(server: LanguageServer):
  # complete <= with parts
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/buildout.cfg"),
    position=Position(line=18, character=3),
    context=CompletionContext(trigger_kind=CompletionTriggerKind.Invoked),
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert [c.label for c in completions] == [
    "section1",
    "section2",
    "section3",
  ]


async def test_complete_insert_text(server: LanguageServer):
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )
  # Only insert the text after the latest -
  params = CompletionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///completions/partial_completions.cfg"
    ),
    position=Position(line=1, character=24),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  (completion,) = [c for c in completions if c.label == "sec-tion-one"]
  assert isinstance(completion.text_edit, TextEdit)
  assert completion.text_edit.range == Range(
    start=Position(line=1, character=18), end=Position(line=1, character=24)
  )
  assert completion.text_edit.new_text == "${sec-tion-one"
  # we set a filter text, because the inserted text is different from the label
  assert completion.filter_text == "${sec-tion-one"

  # Only insert the text after the latest .
  params = CompletionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///completions/partial_completions.cfg"
    ),
    position=Position(line=2, character=24),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  (completion,) = [c for c in completions if c.label == "sect.ion.three"]
  assert isinstance(completion.text_edit, TextEdit)
  assert completion.text_edit.range == Range(
    start=Position(line=2, character=17), end=Position(line=2, character=24)
  )
  assert completion.text_edit.new_text == "${sect.ion.three"


async def test_complete_buildout_options(server: LanguageServer):
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )
  # complete known buildout options
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/empty_buildout.cfg"),
    position=Position(line=1, character=0),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert "extends" in [c.label for c in completions]
  assert "parts" in [c.label for c in completions]
  assert "allow-hosts" in [c.label for c in completions]
  assert "allow-picked-versions" in [c.label for c in completions]


async def test_complete_buildout_parts(server: LanguageServer):
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )
  # complete buildout:parts with existing parts
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/buildout.cfg"),
    position=Position(line=1, character=8),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == [
    "section1",
    "section2",
    "section3",
  ]


async def test_complete_buildout_extends(server: LanguageServer):
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )
  # complete buildout:extends with local files
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/buildout.cfg"),
    position=Position(line=2, character=12),
    context=context,
  )

  completions = await lsp_completion(server, params)
  assert completions is not None
  assert "buildout.cfg" in [c.label for c in completions]
  assert "not_buildout.txt" not in [c.label for c in completions]
  assert "../buildout.cfg" in [c.label for c in completions]
  assert "../symbol/buildout.cfg" in [c.label for c in completions]

  # multi lines
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/buildout.cfg"),
    position=Position(line=7, character=7),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert "buildout.cfg" in [c.label for c in completions]
  assert "not_buildout.txt" not in [c.label for c in completions]
  assert "../buildout.cfg" in [c.label for c in completions]
  assert "../symbol/buildout.cfg" in [c.label for c in completions]

  # multi line on empty line
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/buildout.cfg"),
    position=Position(line=8, character=4),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert "buildout.cfg" in [c.label for c in completions]
  assert "not_buildout.txt" not in [c.label for c in completions]
  assert "../buildout.cfg" in [c.label for c in completions]
  assert "../symbol/buildout.cfg" in [c.label for c in completions]

  # multi line with existing text
  params = CompletionParams(
    text_document=TextDocumentIdentifier(uri="file:///completions/buildout.cfg"),
    position=Position(line=10, character=10),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert "buildout.cfg" in [c.label for c in completions]
  assert "not_buildout.txt" not in [c.label for c in completions]
  assert "../buildout.cfg" in [c.label for c in completions]
  assert "../symbol/buildout.cfg" in [c.label for c in completions]
  (completion,) = [c for c in completions if c.label == "../symbol/buildout.cfg"]
  assert isinstance(completion.text_edit, TextEdit)
  assert completion.text_edit.new_text == "../symbol/buildout.cfg"
  assert completion.text_edit.range == Range(
    start=Position(line=10, character=4),
    end=Position(line=10, character=10),
  )


async def test_complete_comments(server: LanguageServer):
  # no completions happens in comments
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )
  for position in (
    Position(line=3, character=6),
    Position(line=4, character=2),
    Position(line=5, character=1),
    Position(line=6, character=7),
    Position(line=7, character=8),
  ):
    params = CompletionParams(
      text_document=TextDocumentIdentifier(uri="file:///completions/comments.cfg"),
      position=position,
      context=context,
    )

    completions = await lsp_completion(server, params)
    assert completions is None

  # but completions should happen normally if there's a comment after the cursor
  for position in (Position(line=10, character=28),):
    params = CompletionParams(
      text_document=TextDocumentIdentifier(uri="file:///completions/comments.cfg"),
      position=position,
      context=context,
    )
    completions = await lsp_completion(server, params)
    assert completions is not None


async def test_complete_in_empty_substitution(server: LanguageServer):
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )
  params = CompletionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///completions/empty_substitution.cfg"
    ),
    position=Position(line=1, character=11),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == ["buildout", "section"]


async def test_complete_after_empty_substitution(server: LanguageServer):
  context = CompletionContext(
    trigger_kind=CompletionTriggerKind.Invoked,
  )
  params = CompletionParams(
    text_document=TextDocumentIdentifier(
      uri="file:///completions/empty_substitution.cfg"
    ),
    position=Position(line=1, character=18),
    context=context,
  )
  completions = await lsp_completion(server, params)
  assert completions is not None
  assert sorted([c.label for c in completions]) == []
