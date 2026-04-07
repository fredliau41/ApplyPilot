# Local development (fork + UV)

This repo is a normal Python package. PyPI installs register a console script; a **fork** uses the same mechanism—you install the package from your checkout in **editable** mode so `applypilot` runs your working tree.

## Setup

```bash
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
playwright install chromium
uv pip install --no-deps python-jobspy
uv pip install pydantic tls-client requests markdownify regex

## Run the CLI while developing


```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
rehash
which applypilot
```

```bash
# Init or check setup
applypilot init
applypilot doctor

# Pipeline stages (discover → enrich → score → tailor → cover → pdf)
applypilot run                              # all stages
applypilot run discover --workers 8
applypilot run score --workers 8
applypilot run tailor --limit 100 --workers 4
applypilot run tailor cover --limit 100 --workers 4

# Validation modes: strict, normal (default), lenient
applypilot run tailor --validation lenient --limit 100 --workers 4
applypilot run cover --validation lenient --limit 50

# Check progress
applypilot status

# Auto-apply 
applypilot apply --limit 10 --workers 3
applypilot apply --url "https://..." --dry-run

# Manage artifacts
applypilot reprint --target cover --workers 4
applypilot reprint --target resume
applypilot update_db
applypilot dashboard

#forever
applypilot apply --continuous --workers 3
applypilot apply -c --workers 3       # shorthand
```

**Without** activating the venv, you can still invoke the module if dependencies are on `PYTHONPATH` (not recommended); the reliable approach is the editable install above.

Equivalent to the `applypilot` command when debugging:

```bash
python -m applypilot --help
```


## pip equivalent (from CONTRIBUTING.md)

If you prefer pip instead of UV:

```bash
pip install -e ".[dev]"
playwright install chromium
pip install --no-deps python-jobspy && pip install pydantic tls-client requests markdownify regex
```

After that, `applypilot` on your PATH is your fork’s `src/applypilot` code.
