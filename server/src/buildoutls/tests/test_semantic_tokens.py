from lsprotocol.types import (
  TextDocumentIdentifier,
  SemanticTokensParams,
)
from pygls.lsp.server import LanguageServer

from ..server import lsp_semantic_tokens_full


async def test_semantic_tokens_full(server: LanguageServer):
  # on option from a known recipe, show the option documentation
  tokens = await lsp_semantic_tokens_full(
    server,
    SemanticTokensParams(
      text_document=TextDocumentIdentifier(
        uri="file:///semantic_tokens/slapos_recipe_build.cfg"
      ),
    ),
  )
  assert tokens is not None
  assert tokens.data == (
    # fmt:off
    []
    # ${ok:init}
    + [3, 2, 6, 3, 0]  # import
    + [0, 7, 2, 6, 0]  # os
    + [1, 2, 9, 0, 0]  # # comment
    + [1, 2, 3, 3, 0]  # def
    + [0, 4, 1, 5, 0]  # f
    + [0, 2, 5, 6, 0]  # param
    + [1, 4, 1, 1, 0]  # "
    + [0, 1, 9, 1, 0]  # docstring
    + [0, 9, 1, 1, 0]  # "
    + [1, 4, 6, 3, 0]  # return
    + [0, 7, 1, 6, 0]  # g
    + [0, 2, 1, 1, 0]  # "
    + [0, 1, 6, 1, 0]  # string
    + [0, 6, 1, 1, 0]  # "
    + [0, 5, 1, 2, 0]  # 1
    + [2, 2, 17, 6, 0]  # multi_line_string
    + [0, 20, 3, 1, 0]  # """
    + [0, 3, 1, 1, 0]  # \n
    + [1, 1, 8, 1, 0]  #   line 1
    + [0, 8, 1, 1, 0]  # \n
    + [1, 1, 8, 1, 0]  #   line 2
    + [0, 8, 1, 1, 0]  # \n
    + [1, 1, 2, 1, 0]  # \n
    + [0, 2, 3, 1, 0]  # """
    + [2, 2, 5, 3, 0]  # class
    + [0, 6, 5, 4, 0]  # Class
    + [1, 4, 9, 6, 0]  # @property
    + [1, 4, 3, 3, 0]  # def
    + [0, 4, 1, 5, 0]  # p
    + [0, 2, 4, 7, 0]  # self
    + [1, 6, 6, 3, 0]  # return
    + [0, 7, 1, 2, 0]  # 1
    # ${ok:install}
    + [3, 2, 3, 3, 0]  # def
    + [0, 4, 2, 5, 0]  # f2
    + [0, 3, 1, 6, 0]  # a
    + [0, 2, 3, 7, 0]  # int
    + [0, 8, 3, 7, 0]  # str
    + [1, 4, 2, 6, 0]  # f2
    + [0, 3, 1, 6, 0]  # a
    + [0, 4, 1, 2, 0]  # 1
    + [1, 2, 4, 3, 0]  # pass
    # ${another:init}
    + [8, 2, 6, 3, 0]  # import
    + [0, 7, 12, 6, 0]  # another_init
    # ${another:install}
    + [3, 2, 6, 3, 0]  # import
    + [0, 7, 15, 6, 0]  # another_install
    # ${again-another:init}
    + [7, 2, 6, 3, 0]  # import
    + [0, 7, 18, 6, 0]  # again_another_init
    # ${again-another:install}
    + [2, 2, 6, 3, 0]  # import
    + [0, 7, 21, 6, 0]  # again_another_install
  )
  # fmt: on
