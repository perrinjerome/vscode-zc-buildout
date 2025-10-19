import asyncio
import pathlib
import subprocess
from typing import Any, List, no_type_check
from unittest import mock

import pytest
from lsprotocol.types import Diagnostic
from pygls.lsp.server import LanguageServer
from pygls.workspace import Workspace

from ..buildout import (
  _extends_dependency_graph,
  _parse_cache,
  _resolved_buildout_cache,
  _resolved_extends_cache,
  open,
)
from ..diagnostic import getDiagnostics


@pytest.fixture
def slapos_working_copy() -> pathlib.Path:
  working_copy_path = pathlib.Path(".") / "slapos"
  if not working_copy_path.exists():
    subprocess.check_call(
      (
        "git",
        "clone",
        "--depth=1",
        "--branch=1.0.238",
        "https://github.com/slapos/slapos",
      )
    )
  return working_copy_path.absolute()


def clear_caches() -> None:
  _resolved_buildout_cache.clear()
  _resolved_extends_cache.clear()
  _parse_cache.clear()
  _extends_dependency_graph.clear()


@pytest.fixture
def no_pypi_diagnostics() -> Any:
  with (
    mock.patch(
      "buildoutls.diagnostic.pypi.PyPIClient.get_known_vulnerabilities",
      return_value=(),
    ),
    mock.patch(
      "buildoutls.diagnostic.pypi.PyPIClient.get_latest_version", return_value=None
    ),
  ):
    yield


# https://github.com/ionelmc/pytest-benchmark/issues/66#issuecomment-575853801
@no_type_check
@pytest.fixture(scope="function")
def aio_benchmark(benchmark):
  import threading

  class Sync2Async:
    def __init__(self, coro, *args, **kwargs):
      self.coro = coro
      self.args = args
      self.kwargs = kwargs
      self.custom_loop = None
      self.thread = None

    def start_background_loop(self) -> None:
      asyncio.set_event_loop(self.custom_loop)
      self.custom_loop.run_forever()

    def __call__(self):
      evloop = None
      awaitable = self.coro(*self.args, **self.kwargs)
      try:
        evloop = asyncio.get_running_loop()
      except Exception:
        pass
      if evloop is None:
        return asyncio.run(awaitable)
      else:
        if not self.custom_loop or not self.thread or not self.thread.is_alive():
          self.custom_loop = asyncio.new_event_loop()
          self.thread = threading.Thread(target=self.start_background_loop, daemon=True)
          self.thread.start()

        return asyncio.run_coroutine_threadsafe(awaitable, self.custom_loop).result()

  def _wrapper(func, *args, **kwargs):
    if asyncio.iscoroutinefunction(func):
      benchmark(Sync2Async(func, *args, **kwargs))
    else:
      benchmark(func, *args, **kwargs)

  return _wrapper


@pytest.mark.parametrize("cache", ("with_cache", "without_cache"))
@pytest.mark.parametrize(
  "profile_relative_path",
  (
    "stack/slapos.cfg",
    "stack/erp5/buildout.cfg",
    "stack/erp5/rsyslogd.cfg.in",
    "stack/erp5/instance.cfg.in",
    "stack/erp5/instance-erp5.cfg.in",
  ),
)
async def test_open_and_diagnostic(
  no_pypi_diagnostics: Any,
  slapos_working_copy: pathlib.Path,
  aio_benchmark: Any,
  profile_relative_path: pathlib.Path,
  cache: Any,
) -> None:
  doc_uri = (slapos_working_copy / profile_relative_path).as_uri()
  workspace = Workspace(slapos_working_copy.as_uri())
  ls = LanguageServer(name="zc.buildout.languageserver", version="dev")
  ls.protocol._workspace = workspace

  async def open_and_get_diagnostics() -> List[Diagnostic]:
    diags: List[Diagnostic] = []
    await open(ls, doc_uri)
    async for diag in getDiagnostics(ls, doc_uri):
      diags.append(diag)
    return diags

  # warmup
  await open_and_get_diagnostics()

  @aio_benchmark
  async def open_and_get_diagnostics_bench() -> None:
    if cache == "without_cache":
      clear_caches()
    await open_and_get_diagnostics()
