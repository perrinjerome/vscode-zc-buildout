import sys
from typing import Any
from pygls.server import LanguageServer

import cProfile
import io
import pstats

_profiler: cProfile.Profile



def start_profiling(ls:LanguageServer, params: Any) -> None:
  global _profiler
  _profiler = cProfile.Profile()
  _profiler.enable()



def stop_profiling(ls:LanguageServer, params: Any) -> None:
  global _profiler
  _profiler.disable()
  
  s = io.StringIO()
  ps = pstats.Stats(_profiler, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
  ps.print_stats()
  print(s.getvalue(), file=sys.stderr)
  ls.show_message_log(s.getvalue())

