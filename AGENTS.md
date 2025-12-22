# Agent Instructions

## Running Tests

### Server Tests

To run all server tests, use `tox` from the server folder:

```bash
cd server
tox
```

This is slow and generate lots of output, to run a specific test file or test function with pytest directly:

```bash
cd server
uv run pytest src/buildoutls/tests/test_hover.py -v
uv run pytest src/buildoutls/tests/test_hover.py::test_hover_jinja_section_name -v
```

Note: Test requirements need to be installed first:

```bash
cd server
uv pip install -r test-requirements.txt
```

Also, make sure the linter is OK, using:

```bash
cd server
ruff check src
ruff format --diff src
mypy .
pylint --disable=all --enable=unused-variable,unreachable,duplicate-key,unused-import src
```
