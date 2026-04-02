# Local development (fork + UV)

This repo is a normal Python package. PyPI installs register a console script; a **fork** uses the same mechanism—you install the package from your checkout in **editable** mode so `applypilot` runs your working tree.

## Where the CLI is wired up

| What | Where |
|------|--------|
| **Console script name** | `applypilot` (declared in `pyproject.toml`) |
| **Entry target** | `applypilot.cli:app` — the Typer application in `src/applypilot/cli.py` |
| **Module entry** | `python -m applypilot` → `src/applypilot/__main__.py`, which calls `applypilot.cli.app()` |

The “launcher” for subcommands (`init`, `doctor`, `run`, `apply`, etc.) is **`src/applypilot/cli.py`**. Pipeline orchestration lives in `src/applypilot/pipeline.py`; browser auto-apply is under `src/applypilot/apply/`.

## UV environment and editable install

From the repository root (Python **3.11+**):

```bash
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

Install Playwright’s browser (needed for discovery/enrichment pieces that use it):

```bash
playwright install chromium
```

### `python-jobspy` (same resolver quirk as PyPI)

JobSpy’s metadata pins conflict with a plain resolver; mirror the README’s two-step install with `uv pip`:

```bash
uv pip install --no-deps python-jobspy
uv pip install pydantic tls-client requests markdownify regex
```

## Run the CLI while developing

With the venv activated and the editable install in place, use the same commands as end users:

```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
rehash
which applypilot
applypilot --version
applypilot init
applypilot doctor
applypilot run
applypilot run --help
applypilot run discovery --workers 8 
applypilot run score --workers 8 
applypilot run tailor --workers 4
applypilot run tailor --tailor-limit 100 --validation lenient
applypilot run tailor cover -w 4 --limit 100 --validation lenient
applypilot run  cover -w 4 --limit 4 --validation lenient
applypilot run  cover  --limit 1 --validation lenient


applypilot reprint --target cover --workers 4
applypilot reprint --target resume
applypilot reprint --target all

applypilot apply --workers 3 --dry-run  --limit 12
applypilot apply --workers 1 --dry-run  --limit 1

# …etc.
```

**Without** activating the venv, you can still invoke the module if dependencies are on `PYTHONPATH` (not recommended); the reliable approach is the editable install above.

Equivalent to the `applypilot` command when debugging:

```bash
python -m applypilot --help
```

## Quick checks

```bash
pytest tests/ -v
ruff check src/
```

## pip equivalent (from CONTRIBUTING.md)

If you prefer pip instead of UV:

```bash
pip install -e ".[dev]"
playwright install chromium
pip install --no-deps python-jobspy && pip install pydantic tls-client requests markdownify regex
```

After that, `applypilot` on your PATH is your fork’s `src/applypilot` code.
