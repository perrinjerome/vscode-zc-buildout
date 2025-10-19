import cProfile
import io
import logging
import pstats
from typing import Any

from lsprotocol.types import LogMessageParams, MessageType
from pygls.lsp.server import LanguageServer

_profiler: cProfile.Profile
logger = logging.getLogger(__name__)


def start_profiling(ls: LanguageServer, params: Any) -> None:
  global _profiler
  _profiler = cProfile.Profile()
  _profiler.enable()


def stop_profiling(ls: LanguageServer, params: Any) -> None:
  global _profiler
  _profiler.disable()

  s = io.StringIO()
  ps = pstats.Stats(_profiler, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
  ps.print_stats()
  logger.warn(s.getvalue())
  ls.window_log_message(LogMessageParams(message=s.getvalue(), type=MessageType.Info))
